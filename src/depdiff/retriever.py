from typing import Optional, Set
import pathlib
import subprocess
import tempfile
import tarfile
import zipfile
import shutil
import requests
from depdiff.models import DependencyChange
from depdiff.comparator import SourceComparator
from depdiff.pypi.metadata import MetadataClient, PackageMetadata


class HybridRetriever:
    """
    Orchestrates the retrieval of source code diffs using a hybrid strategy.
    Prioritizes Git native diffs, falls back to downloading and comparing artifacts.
    """

    def __init__(self, comparator: SourceComparator):
        self.comparator = comparator
        self._temp_dirs: Set[pathlib.Path] = set()

    def get_diff(self, change: DependencyChange) -> str:
        """
        Obtains the unified diff for a dependency change.

        Uses hybrid strategy: tries Git first, falls back to artifact comparison.

        Args:
            change: The dependency change object.

        Returns:
            The unified diff string.

        Raises:
            Exception: If both Git and artifact strategies fail.
        """
        # Try Git strategy first
        git_diff = self._try_git_strategy(change)
        if git_diff is not None:
            return git_diff

        # Fall back to artifact comparison
        return self._artifact_fallback(change)

    def _try_git_strategy(self, change: DependencyChange) -> Optional[str]:
        """
        Attempts to fetch the diff using Git.

        1. Fetch PyPI metadata to find Git URL.
        2. Clone repo.
        3. Resolve tags.
        4. Run git diff.

        Returns:
            The diff string if successful, None otherwise.
        """
        # Can only use git strategy for version updates (not additions/removals)
        if not change.is_update:
            return None

        # These assertions are safe because is_update guarantees both are not None
        assert change.old_version is not None
        assert change.new_version is not None

        try:
            # Fetch metadata for the new version to get the Git URL
            metadata = self._fetch_pypi_metadata(change.name, change.new_version)

            # Extract Git URL from metadata
            git_url = self._extract_git_url(metadata)
            if not git_url:
                return None

            # Clone the repository
            repo_path = self._clone_repo(git_url)

            # Resolve tags for both versions
            old_tag = self._resolve_tag(repo_path, change.old_version)
            if not old_tag:
                return None

            new_tag = self._resolve_tag(repo_path, change.new_version)
            if not new_tag:
                return None

            # Generate and return the diff
            diff = self._git_diff(repo_path, old_tag, new_tag)
            return diff

        except Exception:
            # Any error means we fall back to artifact strategy
            return None

    def _fetch_pypi_metadata(self, package_name: str, version: str) -> PackageMetadata:
        """Fetches package metadata from PyPI."""
        client = MetadataClient()
        return client.get(package_name, version)

    def _extract_git_url(self, metadata: PackageMetadata) -> Optional[str]:
        """
        Extracts a valid Git URL from PyPI metadata.

        Checks for common Git hosting platforms (GitHub, GitLab, Bitbucket).

        Args:
            metadata: The package metadata from PyPI.

        Returns:
            A valid Git URL if found, None otherwise.
        """
        url = metadata.info.url

        if not url:
            return None

        # Check if the URL is from a known Git hosting platform
        git_platforms = [
            "https://github.com/",
            "https://gitlab.com/",
            "https://bitbucket.org/",
        ]

        for platform in git_platforms:
            if url.startswith(platform):
                # Ensure it ends with .git for consistency
                if not url.endswith(".git"):
                    url = url.rstrip("/") + ".git"
                return url

        return None

    def _clone_repo(self, git_url: str) -> pathlib.Path:
        """
        Clones a git repository to a temporary location.

        Uses --filter=blob:none for performance (blobless clone).

        Args:
            git_url: The URL of the Git repository to clone.

        Returns:
            Path to the cloned repository.

        Raises:
            subprocess.CalledProcessError: If git clone fails.
        """
        # Create a temporary directory for the clone
        temp_dir = tempfile.mkdtemp(prefix="depdiff_git_")
        repo_path = pathlib.Path(temp_dir)

        # Track for cleanup
        self._temp_dirs.add(repo_path)

        # Clone with blob filtering for performance
        # --filter=blob:none fetches commits and trees but not blobs initially
        subprocess.run(
            ["git", "clone", "--filter=blob:none", git_url, str(repo_path)],
            check=True,
            capture_output=True,
            text=True,
        )

        return repo_path

    def _resolve_tag(self, repo_path: pathlib.Path, version: str) -> Optional[str]:
        """
        Resolves a version string to a Git tag.

        Tries exact match first (e.g., "1.0.0"), then with "v" prefix ("v1.0.0").

        Args:
            repo_path: Path to the Git repository.
            version: Version string to resolve (e.g., "1.0.0").

        Returns:
            The resolved tag name if found, None otherwise.
        """
        # Get all tags from the repository
        try:
            result = subprocess.run(
                ["git", "tag", "--list"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            tags = set(result.stdout.strip().split("\n"))

            # Try exact match first
            if version in tags:
                return version

            # Try with "v" prefix
            v_version = f"v{version}"
            if v_version in tags:
                return v_version

            return None

        except subprocess.CalledProcessError:
            return None

    def _git_diff(self, repo_path: pathlib.Path, old_tag: str, new_tag: str) -> str:
        """
        Runs git diff between two tags.

        Args:
            repo_path: Path to the Git repository.
            old_tag: The old tag/commit reference.
            new_tag: The new tag/commit reference.

        Returns:
            The unified diff output as a string.

        Raises:
            subprocess.CalledProcessError: If git diff fails.
        """
        result = subprocess.run(
            ["git", "diff", old_tag, new_tag],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout

    def _artifact_fallback(self, change: DependencyChange) -> str:
        """
        Fallback strategy: downloads artifacts and compares them.

        1. Download .tar.gz or .whl for both versions.
        2. Extract.
        3. Compare directories using SourceComparator.

        Args:
            change: The dependency change object.

        Returns:
            The unified diff string.

        Raises:
            Exception: If download or comparison fails.
        """
        # Can only compare updates (not additions/removals)
        if not change.is_update:
            raise ValueError("Artifact fallback only supports version updates")

        # These assertions are safe because is_update guarantees both are not None
        assert change.old_version is not None
        assert change.new_version is not None

        # Download and extract both versions
        old_dir = self._download_artifact(change.name, change.old_version)
        new_dir = self._download_artifact(change.name, change.new_version)

        # Compare the directories
        diff = self.comparator.compare_directories(old_dir, new_dir)

        return diff

    def _download_artifact(self, package_name: str, version: str) -> pathlib.Path:
        """
        Downloads and extracts the package artifact to a temporary directory.

        Prefers sdist (.tar.gz) over wheels (.whl).

        Args:
            package_name: Name of the package.
            version: Version string.

        Returns:
            Path to the extracted package directory.

        Raises:
            ValueError: If no suitable artifact is found.
            Exception: If download or extraction fails.
        """
        # Fetch metadata to get download URLs
        metadata = self._fetch_pypi_metadata(package_name, version)

        # Find sdist (.tar.gz) or wheel (.whl) URL
        sdist_url: Optional[str] = None
        wheel_url: Optional[str] = None

        for url in metadata.urls:
            if url.endswith(".tar.gz"):
                sdist_url = url
                break
            elif url.endswith(".whl") and wheel_url is None:
                wheel_url = url

        # Prefer sdist over wheel
        download_url = sdist_url or wheel_url

        if not download_url:
            raise ValueError(f"No suitable artifact found for {package_name} {version}")

        # Create temporary directory for extraction
        temp_dir = tempfile.mkdtemp(prefix="depdiff_artifact_")
        extract_path = pathlib.Path(temp_dir)

        # Track for cleanup
        self._temp_dirs.add(extract_path)

        # Download the artifact
        response = requests.get(download_url, timeout=30)
        response.raise_for_status()

        # Save to temporary file
        artifact_file = extract_path / "artifact"
        artifact_file.write_bytes(response.content)

        # Extract based on file type
        if download_url.endswith(".tar.gz"):
            with tarfile.open(artifact_file, "r:gz") as tar:
                tar.extractall(path=extract_path, filter="fully_trusted")
        elif download_url.endswith(".whl"):
            with zipfile.ZipFile(artifact_file, "r") as zip_ref:
                zip_ref.extractall(extract_path)

        # Remove the downloaded artifact file
        artifact_file.unlink()

        # Find the extracted package directory
        # For sdist, it's typically <package>-<version>/
        # For wheel, files are extracted directly
        extracted_dirs = [d for d in extract_path.iterdir() if d.is_dir()]

        if len(extracted_dirs) == 1:
            # Return the single extracted directory
            return extracted_dirs[0]
        else:
            # Return the extraction path itself (for wheels)
            return extract_path

    def cleanup(self) -> None:
        """
        Clean up all temporary directories created during retrieval operations.

        This should be called when the retriever is no longer needed.
        """
        for temp_dir in self._temp_dirs:
            if temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    # Ignore cleanup errors
                    pass

        self._temp_dirs.clear()

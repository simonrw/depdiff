from typing import Optional
import pathlib
import subprocess
import tempfile
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

    def get_diff(self, change: DependencyChange) -> str:
        """
        Obtains the unified diff for a dependency change.

        Args:
            change: The dependency change object.

        Returns:
            The unified diff string.
        """
        raise NotImplementedError

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
        ...

    def _fetch_pypi_metadata(self, package_name: str, version: str) -> PackageMetadata:
        """Fetches package metadata from PyPI."""
        client = MetadataClient()
        return client.get(package_name, version)

    def _extract_git_url(self, metadata: dict) -> Optional[str]:
        """Extracts a valid Git URL from PyPI metadata."""
        ...

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
        """
        raise NotImplementedError

    def _download_artifact(self, package_name: str, version: str) -> pathlib.Path:
        """Downloads and extracts the package artifact to a temporary directory."""
        raise NotImplementedError

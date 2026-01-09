from typing import Optional
import pathlib
from depdiff.models import DependencyChange
from depdiff.comparator import SourceComparator


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

    def _fetch_pypi_metadata(self, package_name: str) -> dict:
        """Fetches package metadata from PyPI."""
        raise NotImplementedError

    def _extract_git_url(self, metadata: dict) -> Optional[str]:
        """Extracts a valid Git URL from PyPI metadata."""
        ...

    def _clone_repo(self, git_url: str) -> pathlib.Path:
        """Clones a git repository to a temporary location."""
        raise NotImplementedError

    def _resolve_tag(self, repo_path: pathlib.Path, version: str) -> Optional[str]:
        """Resolves a version string to a Git tag."""
        ...

    def _git_diff(self, repo_path: pathlib.Path, old_tag: str, new_tag: str) -> str:
        """Runs git diff between two tags."""
        raise NotImplementedError

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

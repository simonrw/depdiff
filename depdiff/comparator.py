import pathlib
from typing import Optional
from depdiff.models import DependencyChange

class SourceComparator:
    """
    Compares two source directories to generate a unified diff.
    Acts as a fallback engine when Git native diff is not available.
    """

    def compare_directories(self, old_dir: pathlib.Path, new_dir: pathlib.Path) -> str:
        """
        Recursively compares two directories and generates a unified diff.

        Args:
            old_dir: Path to the directory containing the old version.
            new_dir: Path to the directory containing the new version.

        Returns:
            A string containing the unified diff of the directory contents.
        """
        ...
        raise NotImplementedError

    def _is_binary(self, file_path: pathlib.Path) -> bool:
        """Determines if a file is binary."""
        ...
        raise NotImplementedError

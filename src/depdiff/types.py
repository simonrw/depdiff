import pathlib
import shutil
from typing import Protocol, Set


class TempDirTracker(Protocol):
    """Protocol for objects that track temporary directories."""

    def track_temp_dir(self, path: pathlib.Path) -> None:
        """Register a temporary directory for cleanup."""
        ...


def cleanup_temp_dirs(temp_dirs: Set[pathlib.Path]) -> None:
    """
    Clean up all temporary directories in the provided set.

    Args:
        temp_dirs: Set of paths to clean up. The set is cleared after cleanup.
    """
    for temp_dir in temp_dirs:
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
            except OSError:
                # Ignore cleanup errors
                pass

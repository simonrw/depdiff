import os
import sys
import pathlib
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, List, Optional, Set
from depdiff.models import DependencyChange
from depdiff.comparator import SourceComparator
from depdiff.retriever import HybridRetriever
from depdiff.types import cleanup_temp_dirs


class ParallelRetriever:
    """
    Manages parallel processing of dependency changes using ThreadPoolExecutor.

    Provides thread-safe temp directory tracking and progress reporting while
    processing multiple packages concurrently.
    """

    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize the parallel retriever.

        Args:
            max_workers: Maximum number of worker threads. If None, uses
                        min(20, cpu_count * 2) for optimal I/O-bound performance.
        """
        cpu_count = os.cpu_count() or 4
        workers = max_workers or min(20, cpu_count * 2)
        self._executor = ThreadPoolExecutor(max_workers=workers)
        self._temp_dirs: Set[pathlib.Path] = set()
        self._temp_dirs_lock = threading.Lock()
        self._progress_lock = threading.Lock()
        self._comparator = SourceComparator()

    def process_changes_parallel(
        self, changes: List[DependencyChange]
    ) -> Dict[str, str]:
        """
        Process multiple dependency changes in parallel.

        Args:
            changes: List of dependency changes to process.

        Returns:
            Dictionary mapping package names to their diff strings.
        """
        total = len(changes)
        completed = 0

        # Submit all packages to thread pool
        futures: Dict[str, Future[str]] = {}
        for change in changes:
            future = self._executor.submit(self._process_single_package, change)
            futures[change.name] = future

        # Collect results with error handling
        diffs: Dict[str, str] = {}

        for package_name, future in futures.items():
            try:
                # Wait for result with 5-minute timeout
                diff = future.result(timeout=300)
                diffs[package_name] = diff

                # Update progress
                completed += 1
                with self._progress_lock:
                    print(
                        f"[{completed}/{total}] Completed {package_name}",
                        file=sys.stderr,
                    )

            except Exception as e:
                # Log error but continue with other packages
                completed += 1
                error_msg = f"Error: {e}"
                diffs[package_name] = error_msg

                with self._progress_lock:
                    print(
                        f"[{completed}/{total}] Failed {package_name}: {e}",
                        file=sys.stderr,
                    )

        return diffs

    def _process_single_package(self, change: DependencyChange) -> str:
        """
        Process a single package (executed in thread pool).

        Args:
            change: The dependency change to process.

        Returns:
            The unified diff string for this package.
        """
        # Create HybridRetriever for this thread
        retriever = HybridRetriever(comparator=self._comparator, temp_dir_tracker=self)
        return retriever.get_diff(change)

    def track_temp_dir(self, path: pathlib.Path) -> None:
        """
        Thread-safe temp directory registration.

        Args:
            path: Path to temporary directory to track for cleanup.
        """
        with self._temp_dirs_lock:
            self._temp_dirs.add(path)

    def cleanup(self) -> None:
        """
        Clean up all tracked temp directories and shutdown thread pool.

        This should be called when the retriever is no longer needed.
        """
        self._executor.shutdown(wait=True)
        cleanup_temp_dirs(self._temp_dirs)
        self._temp_dirs.clear()

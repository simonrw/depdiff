import sys
import atexit
import pathlib
from typing import Optional

from depdiff.parser import DiffParser
from depdiff.reporter import ReportGenerator
from depdiff.parallel import ParallelRetriever


class DependencyDiffOrchestrator:
    """
    Orchestrates the complete dependency diff workflow.

    Manages the lifecycle of parsing input, fetching diffs, formatting output,
    and cleaning up temporary resources.
    """

    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize the orchestrator with necessary components.

        Args:
            max_workers: Maximum number of worker threads for parallel processing.
                        If None, uses min(20, cpu_count * 2).
        """
        self.parser = DiffParser()
        self.parallel_retriever = ParallelRetriever(max_workers=max_workers)
        self.reporter = ReportGenerator()

        # Register cleanup on exit
        atexit.register(self._cleanup)

    def process_requirements_diff(
        self, diff_input: str, input_source: Optional[str] = None
    ) -> str:
        """
        Process a requirements.txt diff and generate a report of source code changes.

        Args:
            diff_input: The unified diff content of requirements.txt changes.
            input_source: Optional description of the input source (for logging).

        Returns:
            A formatted report showing source code diffs for all changed dependencies.
        """
        # Parse the input to extract dependency changes
        changes = self.parser.parse(diff_input)

        if not changes:
            return "No dependency changes detected."

        # Filter to only version updates (skip additions/removals for now)
        updates = [c for c in changes if c.is_update]

        if not updates:
            return "No dependency changes detected."

        # Process in parallel
        print(f"Processing {len(updates)} packages in parallel...", file=sys.stderr)
        diffs = self.parallel_retriever.process_changes_parallel(updates)

        # Generate the final report
        report = self.reporter.generate_report(diffs)

        # Return appropriate message if no diffs were collected
        if not report:
            return "No dependency changes detected."

        return report

    def process_from_file(self, filepath: pathlib.Path) -> str:
        """
        Process a requirements.txt diff from a file.

        Args:
            filepath: Path to the file containing the diff.

        Returns:
            A formatted report showing source code diffs.
        """
        content = filepath.read_text()
        return self.process_requirements_diff(content, input_source=str(filepath))

    def process_from_stdin(self) -> str:
        """
        Process a requirements.txt diff from stdin.

        Returns:
            A formatted report showing source code diffs.
        """
        content = sys.stdin.read()
        return self.process_requirements_diff(content, input_source="stdin")

    def _cleanup(self) -> None:
        """Clean up temporary directories created during processing."""
        self.parallel_retriever.cleanup()

    def cleanup(self) -> None:
        """Manually trigger cleanup of temporary resources."""
        self._cleanup()

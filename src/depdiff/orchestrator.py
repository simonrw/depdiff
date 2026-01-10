import sys
import atexit
import pathlib
from typing import Optional

from depdiff.comparator import SourceComparator
from depdiff.models import DependencyChange
from depdiff.parser import DiffParser
from depdiff.reporter import ReportGenerator
from depdiff.retriever import HybridRetriever


class DependencyDiffOrchestrator:
    """
    Orchestrates the complete dependency diff workflow.

    Manages the lifecycle of parsing input, fetching diffs, formatting output,
    and cleaning up temporary resources.
    """

    def __init__(self):
        """Initialize the orchestrator with necessary components."""
        self.parser = DiffParser()
        self.comparator = SourceComparator()
        self.retriever = HybridRetriever(self.comparator)
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

        # Collect diffs for each change
        diffs: dict[str, str] = {}

        for change in changes:
            # Only process version updates (skip additions/removals for now)
            if not change.is_update:
                continue

            try:
                # Get the diff for this dependency change
                diff = self.retriever.get_diff(change)
                diffs[change.name] = diff

            except Exception as e:
                # Log error but continue processing other packages
                error_msg = f"Error processing {change.name}: {str(e)}"
                print(error_msg, file=sys.stderr)
                continue

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
        self.retriever.cleanup()

    def cleanup(self) -> None:
        """Manually trigger cleanup of temporary resources."""
        self._cleanup()

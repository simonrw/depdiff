from typing import Dict


class ReportGenerator:
    """Generates the final report from the aggregated diffs."""

    def generate_report(self, diffs: Dict[str, str]) -> str:
        """
        Formats the collected diffs into a human-readable report.

        Args:
            diffs: A dictionary mapping package names to their diff strings.

        Returns:
            The formatted report string.
        """
        raise NotImplementedError

    def _format_header(self, package_name: str) -> str:
        """Creates a visual separator header for a package."""
        raise NotImplementedError

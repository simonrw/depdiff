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
        if not diffs:
            return ""

        report_sections: list[str] = []

        for package_name in sorted(diffs.keys()):
            diff_content = diffs[package_name]

            # Add header for this package
            header = self._format_header(package_name)
            report_sections.append(header)

            # Add the diff content (strip trailing newlines to avoid double spacing)
            report_sections.append(diff_content.rstrip("\n"))

            # Add blank line between packages
            report_sections.append("")

        # Remove the trailing blank line at the end
        if report_sections and report_sections[-1] == "":
            report_sections.pop()

        return "\n".join(report_sections)

    def _format_header(self, package_name: str) -> str:
        """
        Creates a visual separator header for a package.

        Args:
            package_name: The name of the package.

        Returns:
            A formatted header string.
        """
        separator = "=" * 80
        title = f" DIFF FOR PACKAGE: {package_name.upper()} "
        # Center the title in the separator
        padding = (80 - len(title)) // 2
        header_line = "=" * padding + title + "=" * (80 - padding - len(title))

        return f"{separator}\n{header_line}\n{separator}"

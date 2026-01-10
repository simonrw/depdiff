import pytest

from depdiff.reporter import ReportGenerator


@pytest.fixture
def reporter() -> ReportGenerator:
    """Create a ReportGenerator instance for testing."""
    return ReportGenerator()


class TestReportGenerator:
    """Tests for the ReportGenerator class."""

    def test_empty_diffs(self, reporter: ReportGenerator) -> None:
        """Test generating report with no diffs."""
        # Arrange
        diffs = {}

        # Act
        result = reporter.generate_report(diffs)

        # Assert
        assert result == ""

    def test_single_package_diff(self, reporter: ReportGenerator) -> None:
        """Test generating report for a single package."""
        # Arrange
        diffs = {
            "requests": "diff --git a/requests/api.py b/requests/api.py\n"
            "--- a/requests/api.py\n"
            "+++ b/requests/api.py\n"
            "@@ -1,3 +1,4 @@\n"
            "+# New comment\n"
            " def get(url):\n"
            "     pass\n"
        }

        # Act
        result = reporter.generate_report(diffs)

        # Assert
        assert "DIFF FOR PACKAGE: REQUESTS" in result
        assert "diff --git a/requests/api.py" in result
        assert "===" in result

    def test_multiple_packages(self, reporter: ReportGenerator) -> None:
        """Test generating report for multiple packages."""
        # Arrange
        diffs = {
            "requests": "diff for requests",
            "flask": "diff for flask",
            "django": "diff for django",
        }

        # Act
        result = reporter.generate_report(diffs)

        # Assert
        assert "DIFF FOR PACKAGE: REQUESTS" in result
        assert "DIFF FOR PACKAGE: FLASK" in result
        assert "DIFF FOR PACKAGE: DJANGO" in result
        assert "diff for requests" in result
        assert "diff for flask" in result
        assert "diff for django" in result

    def test_packages_sorted_alphabetically(self, reporter: ReportGenerator) -> None:
        """Test that packages are sorted alphabetically in the report."""
        # Arrange
        diffs = {
            "zebra": "diff for zebra",
            "apple": "diff for apple",
            "middle": "diff for middle",
        }

        # Act
        result = reporter.generate_report(diffs)

        # Assert
        # Check that apple appears before middle, and middle before zebra
        apple_pos = result.index("APPLE")
        middle_pos = result.index("MIDDLE")
        zebra_pos = result.index("ZEBRA")

        assert apple_pos < middle_pos < zebra_pos

    def test_format_header(self, reporter: ReportGenerator) -> None:
        """Test the header formatting."""
        # Act
        header = reporter._format_header("test-package")

        # Assert
        assert "DIFF FOR PACKAGE: TEST-PACKAGE" in header
        assert "===" in header
        # Check that header has 3 lines (separator, title, separator)
        assert len(header.split("\n")) == 3
        # Check all lines are 80 characters
        for line in header.split("\n"):
            assert len(line) == 80

    def test_packages_separated_by_blank_line(self, reporter: ReportGenerator) -> None:
        """Test that packages are separated by blank lines."""
        # Arrange
        diffs = {
            "package1": "diff1",
            "package2": "diff2",
        }

        # Act
        result = reporter.generate_report(diffs)

        # Assert
        # After the first package's diff, there should be a blank line
        assert "diff1\n\n" in result

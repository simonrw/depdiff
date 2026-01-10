import pathlib
from unittest.mock import patch

import pytest

from depdiff.orchestrator import DependencyDiffOrchestrator


@pytest.fixture
def orchestrator() -> DependencyDiffOrchestrator:
    """Create a DependencyDiffOrchestrator instance for testing."""
    return DependencyDiffOrchestrator()


class TestDependencyDiffOrchestrator:
    """Tests for the DependencyDiffOrchestrator class."""

    def test_no_changes(self, orchestrator: DependencyDiffOrchestrator) -> None:
        """Test processing diff with no dependency changes."""
        # Arrange
        diff_input = """
--- a/README.md
+++ b/README.md
@@ -1,1 +1,1 @@
-Old readme
+New readme
"""

        # Act
        result = orchestrator.process_requirements_diff(diff_input)

        # Assert
        assert result == "No dependency changes detected."

    def test_single_package_update(
        self, orchestrator: DependencyDiffOrchestrator
    ) -> None:
        """Test processing diff with a single package update."""
        # Arrange
        diff_input = """
--- a/requirements.txt
+++ b/requirements.txt
@@ -1,1 +1,1 @@
-requests==2.25.1
+requests==2.26.0
"""

        # Mock the retriever to return a simple diff
        with patch.object(
            orchestrator.retriever,
            "get_diff",
            return_value="mock diff content for requests",
        ):
            # Act
            result = orchestrator.process_requirements_diff(diff_input)

        # Assert
        assert "DIFF FOR PACKAGE: REQUESTS" in result
        assert "mock diff content for requests" in result

    def test_multiple_package_updates(
        self, orchestrator: DependencyDiffOrchestrator
    ) -> None:
        """Test processing diff with multiple package updates."""
        # Arrange
        diff_input = """
--- a/requirements.txt
+++ b/requirements.txt
@@ -1,3 +1,3 @@
-requests==2.25.1
+requests==2.26.0
 flask==1.1.2
-django==3.1.0
+django==3.2.0
"""

        def mock_get_diff(change):
            return f"mock diff for {change.name}"

        with patch.object(
            orchestrator.retriever, "get_diff", side_effect=mock_get_diff
        ):
            # Act
            result = orchestrator.process_requirements_diff(diff_input)

        # Assert
        assert "DIFF FOR PACKAGE: REQUESTS" in result
        assert "DIFF FOR PACKAGE: DJANGO" in result
        assert "mock diff for requests" in result
        assert "mock diff for django" in result

    def test_skips_package_additions(
        self, orchestrator: DependencyDiffOrchestrator
    ) -> None:
        """Test that package additions are skipped."""
        # Arrange
        diff_input = """
--- a/requirements.txt
+++ b/requirements.txt
@@ -1,1 +1,2 @@
 requests==2.25.1
+flask==1.1.2
"""

        # Act
        result = orchestrator.process_requirements_diff(diff_input)

        # Assert
        # Should not process additions, so result should indicate no changes
        assert result == "No dependency changes detected."

    def test_skips_package_removals(
        self, orchestrator: DependencyDiffOrchestrator
    ) -> None:
        """Test that package removals are skipped."""
        # Arrange
        diff_input = """
--- a/requirements.txt
+++ b/requirements.txt
@@ -1,2 +1,1 @@
-flask==1.1.2
 requests==2.25.1
"""

        # Act
        result = orchestrator.process_requirements_diff(diff_input)

        # Assert
        # Should not process removals, so result should indicate no changes
        assert result == "No dependency changes detected."

    def test_handles_retriever_errors(
        self, orchestrator: DependencyDiffOrchestrator
    ) -> None:
        """Test that errors from retriever are handled gracefully."""
        # Arrange
        diff_input = """
--- a/requirements.txt
+++ b/requirements.txt
@@ -1,2 +1,2 @@
-requests==2.25.1
+requests==2.26.0
-flask==1.1.2
+flask==2.0.0
"""

        def mock_get_diff_with_error(change):
            if change.name == "requests":
                raise ValueError("Mock error for requests")
            return f"diff for {change.name}"

        with patch.object(
            orchestrator.retriever, "get_diff", side_effect=mock_get_diff_with_error
        ):
            # Act
            result = orchestrator.process_requirements_diff(diff_input)

        # Assert
        # Flask should still be in the result
        assert "DIFF FOR PACKAGE: FLASK" in result
        assert "diff for flask" in result
        # Requests should be skipped due to error
        assert "requests" not in result.lower() or "REQUESTS" not in result

    def test_process_from_file(
        self, orchestrator: DependencyDiffOrchestrator, tmp_path: pathlib.Path
    ) -> None:
        """Test processing diff from a file."""
        # Arrange
        diff_file = tmp_path / "requirements.diff"
        diff_content = """
--- a/requirements.txt
+++ b/requirements.txt
@@ -1,1 +1,1 @@
-requests==2.25.1
+requests==2.26.0
"""
        diff_file.write_text(diff_content)

        with patch.object(
            orchestrator.retriever,
            "get_diff",
            return_value="mock diff",
        ):
            # Act
            result = orchestrator.process_from_file(diff_file)

        # Assert
        assert "DIFF FOR PACKAGE: REQUESTS" in result

    def test_cleanup_called_on_exit(
        self, orchestrator: DependencyDiffOrchestrator
    ) -> None:
        """Test that cleanup is registered to run on exit."""
        # Arrange & Act
        with patch.object(orchestrator.retriever, "cleanup") as mock_cleanup:
            orchestrator.cleanup()

        # Assert
        mock_cleanup.assert_called_once()

    @pytest.mark.vcr
    def test_integration_real_package(
        self, orchestrator: DependencyDiffOrchestrator
    ) -> None:
        """Integration test with a real package diff."""
        # Arrange
        diff_input = """
--- a/requirements.txt
+++ b/requirements.txt
@@ -1,1 +1,1 @@
-six==1.15.0
+six==1.16.0
"""

        # Mock Git strategy to fail, forcing artifact fallback
        with patch.object(
            orchestrator.retriever, "_try_git_strategy", return_value=None
        ):
            # Act
            result = orchestrator.process_requirements_diff(diff_input)

        # Assert
        assert "DIFF FOR PACKAGE: SIX" in result
        assert len(result) > 0

        # Cleanup
        orchestrator.cleanup()

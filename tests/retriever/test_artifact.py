from unittest.mock import patch

import pytest

from depdiff.comparator import SourceComparator
from depdiff.models import DependencyChange
from depdiff.retriever import HybridRetriever


@pytest.fixture
def retriever() -> HybridRetriever:
    """Create a HybridRetriever instance for testing."""
    comparator = SourceComparator()
    # Disable parallel downloads for VCR compatibility
    return HybridRetriever(comparator, parallel_downloads=False)


class TestDownloadArtifact:
    """Tests for the _download_artifact method."""

    @pytest.mark.vcr
    def test_download_sdist(self, retriever: HybridRetriever) -> None:
        """Test downloading and extracting an sdist package."""
        # Act
        result = retriever._download_artifact("six", "1.16.0")

        # Assert
        assert result.exists()
        assert result.is_dir()
        # Check that package files exist
        assert (result / "six.py").exists() or any(result.rglob("six.py"))

    @pytest.mark.vcr
    def test_download_nonexistent_version(self, retriever: HybridRetriever) -> None:
        """Test downloading a nonexistent package version raises error."""
        # Act & Assert
        with pytest.raises(Exception):
            retriever._download_artifact("nonexistent-package-12345", "0.0.1")


class TestArtifactFallback:
    """Tests for the _artifact_fallback method."""

    @pytest.mark.vcr
    def test_artifact_fallback_real_package(self, retriever: HybridRetriever) -> None:
        """Test artifact fallback with a real package from PyPI."""
        # Arrange
        change = DependencyChange(
            name="six",
            old_version="1.15.0",
            new_version="1.16.0",
        )

        # Act
        result = retriever._artifact_fallback(change)

        # Assert
        assert isinstance(result, str)
        # The diff should contain changes
        assert len(result) > 0

    def test_artifact_fallback_with_addition(self, retriever: HybridRetriever) -> None:
        """Test that artifact fallback raises error for package additions."""
        # Arrange
        change = DependencyChange(
            name="test-package",
            old_version=None,
            new_version="1.0.0",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="only supports version updates"):
            retriever._artifact_fallback(change)

    def test_artifact_fallback_with_removal(self, retriever: HybridRetriever) -> None:
        """Test that artifact fallback raises error for package removals."""
        # Arrange
        change = DependencyChange(
            name="test-package",
            old_version="1.0.0",
            new_version=None,
        )

        # Act & Assert
        with pytest.raises(ValueError, match="only supports version updates"):
            retriever._artifact_fallback(change)


class TestGetDiff:
    """Tests for the get_diff method (hybrid strategy)."""

    def test_get_diff_uses_git_when_available(self, retriever: HybridRetriever) -> None:
        """Test that get_diff uses Git strategy when successful."""
        # Arrange
        change = DependencyChange(
            name="test-package",
            old_version="1.0.0",
            new_version="2.0.0",
        )

        expected_diff = "git diff output"

        with patch.object(retriever, "_try_git_strategy", return_value=expected_diff):
            with patch.object(retriever, "_artifact_fallback") as mock_fallback:
                # Act
                result = retriever.get_diff(change)

        # Assert
        assert result == expected_diff
        mock_fallback.assert_not_called()

    def test_get_diff_falls_back_to_artifact(self, retriever: HybridRetriever) -> None:
        """Test that get_diff falls back to artifact when Git fails."""
        # Arrange
        change = DependencyChange(
            name="test-package",
            old_version="1.0.0",
            new_version="2.0.0",
        )

        expected_diff = "artifact diff output"

        with patch.object(retriever, "_try_git_strategy", return_value=None):
            with patch.object(
                retriever, "_artifact_fallback", return_value=expected_diff
            ):
                # Act
                result = retriever.get_diff(change)

        # Assert
        assert result == expected_diff

    @pytest.mark.vcr
    def test_get_diff_integration(self, retriever: HybridRetriever) -> None:
        """Integration test for get_diff using real packages."""
        # Arrange
        change = DependencyChange(
            name="six",
            old_version="1.15.0",
            new_version="1.16.0",
        )

        # Mock Git strategy to fail, forcing artifact fallback
        with patch.object(retriever, "_try_git_strategy", return_value=None):
            # Act
            result = retriever.get_diff(change)

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0

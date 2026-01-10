import pathlib
import subprocess
import tempfile
from typing import Generator
from unittest.mock import patch

import pytest

from depdiff.comparator import SourceComparator
from depdiff.models import DependencyChange
from depdiff.pypi.metadata import Info, PackageMetadata
from depdiff.retriever import HybridRetriever


@pytest.fixture
def retriever() -> HybridRetriever:
    """Create a HybridRetriever instance for testing."""
    comparator = SourceComparator()
    return HybridRetriever(comparator)


@pytest.fixture
def temp_git_repo() -> Generator[pathlib.Path, None, None]:
    """
    Create a temporary Git repository for testing.

    Sets up a repository with:
    - Initial commit with a requirements.txt file
    - Tags for version 1.0.0 and v2.0.0
    """
    with tempfile.TemporaryDirectory(prefix="test_git_repo_") as tmpdir:
        repo_path = pathlib.Path(tmpdir)

        # Initialize git repository
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Configure git user for commits
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create initial requirements.txt
        requirements_file = repo_path / "requirements.txt"
        requirements_file.write_text("requests==2.25.1\n")

        # Create initial commit
        subprocess.run(
            ["git", "add", "requirements.txt"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Tag as version 1.0.0 (without v prefix)
        subprocess.run(
            ["git", "tag", "1.0.0"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Update requirements.txt
        requirements_file.write_text("requests==2.26.0\n")

        # Create second commit
        subprocess.run(
            ["git", "add", "requirements.txt"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Update requests version"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Tag as version v2.0.0 (with v prefix)
        subprocess.run(
            ["git", "tag", "v2.0.0"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        yield repo_path


@pytest.fixture
def cloneable_git_repo(temp_git_repo: pathlib.Path) -> str:
    """
    Convert temp_git_repo to a file:// URL that can be cloned.
    """
    return f"file://{temp_git_repo}"


class TestCloneRepo:
    """Tests for the _clone_repo method."""

    def test_successful_clone(
        self, retriever: HybridRetriever, cloneable_git_repo: str
    ) -> None:
        """Test successful git clone operation with a real repository."""
        # Act
        result = retriever._clone_repo(cloneable_git_repo)

        # Assert
        assert result.exists()
        assert result.is_dir()
        assert (result / ".git").exists()
        assert (result / "requirements.txt").exists()

    @pytest.mark.skip(reason="GitHub asks for the user password instead of directly failing")
    def test_clone_failure(self, retriever: HybridRetriever) -> None:
        """Test git clone failure with an invalid URL."""
        # Arrange
        invalid_url = "https://github.com/nonexistent/repo-that-does-not-exist-12345.git"

        # Act & Assert
        with pytest.raises(subprocess.CalledProcessError):
            retriever._clone_repo(invalid_url)


class TestResolveTag:
    """Tests for the _resolve_tag method."""

    def test_exact_version_match(
        self, retriever: HybridRetriever, temp_git_repo: pathlib.Path
    ) -> None:
        """Test resolving a tag with exact version match."""
        # Act
        result = retriever._resolve_tag(temp_git_repo, "1.0.0")

        # Assert
        assert result == "1.0.0"

    def test_v_prefix_match(
        self, retriever: HybridRetriever, temp_git_repo: pathlib.Path
    ) -> None:
        """Test resolving a tag with v-prefix when exact match not found."""
        # Act - requesting 2.0.0 should find v2.0.0
        result = retriever._resolve_tag(temp_git_repo, "2.0.0")

        # Assert
        assert result == "v2.0.0"

    def test_no_match(
        self, retriever: HybridRetriever, temp_git_repo: pathlib.Path
    ) -> None:
        """Test resolving a tag that doesn't exist."""
        # Act
        result = retriever._resolve_tag(temp_git_repo, "99.99.99")

        # Assert
        assert result is None

    def test_prefer_exact_over_v_prefix(
        self, retriever: HybridRetriever, temp_git_repo: pathlib.Path
    ) -> None:
        """Test that exact match is preferred over v-prefix match."""
        # Arrange - add a tag that exists both with and without v prefix
        subprocess.run(
            ["git", "tag", "3.0.0"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "tag", "v3.0.0"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        # Act
        result = retriever._resolve_tag(temp_git_repo, "3.0.0")

        # Assert
        assert result == "3.0.0"  # Should prefer exact match


class TestGitDiff:
    """Tests for the _git_diff method."""

    def test_successful_diff(
        self, retriever: HybridRetriever, temp_git_repo: pathlib.Path
    ) -> None:
        """Test successful git diff operation between two tags."""
        # Act
        result = retriever._git_diff(temp_git_repo, "1.0.0", "v2.0.0")

        # Assert
        assert "requirements.txt" in result
        assert "-requests==2.25.1" in result
        assert "+requests==2.26.0" in result

    def test_empty_diff(
        self, retriever: HybridRetriever, temp_git_repo: pathlib.Path
    ) -> None:
        """Test git diff with no changes between same tags."""
        # Act
        result = retriever._git_diff(temp_git_repo, "1.0.0", "1.0.0")

        # Assert
        assert result == ""

    def test_diff_command_failure(
        self, retriever: HybridRetriever, temp_git_repo: pathlib.Path
    ) -> None:
        """Test git diff failure with nonexistent tags."""
        # Act & Assert
        with pytest.raises(subprocess.CalledProcessError):
            retriever._git_diff(temp_git_repo, "nonexistent1", "nonexistent2")

    def test_diff_shows_file_additions(
        self, retriever: HybridRetriever, temp_git_repo: pathlib.Path
    ) -> None:
        """Test that diff captures new file additions."""
        # Arrange - create a new file and commit
        new_file = temp_git_repo / "setup.py"
        new_file.write_text("from setuptools import setup\nsetup(name='test')\n")

        subprocess.run(
            ["git", "add", "setup.py"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add setup.py"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "tag", "3.0.0"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        # Act
        result = retriever._git_diff(temp_git_repo, "v2.0.0", "3.0.0")

        # Assert
        assert "setup.py" in result
        assert "+from setuptools import setup" in result


class TestExtractGitUrl:
    """Tests for the _extract_git_url method."""

    def test_github_url(self, retriever: HybridRetriever) -> None:
        """Test extracting GitHub URL."""
        # Arrange
        metadata = PackageMetadata(
            info=Info(url="https://github.com/user/repo"),
            urls=[],
        )

        # Act
        result = retriever._extract_git_url(metadata)

        # Assert
        assert result == "https://github.com/user/repo.git"

    def test_github_url_already_with_git(self, retriever: HybridRetriever) -> None:
        """Test extracting GitHub URL that already ends with .git."""
        # Arrange
        metadata = PackageMetadata(
            info=Info(url="https://github.com/user/repo.git"),
            urls=[],
        )

        # Act
        result = retriever._extract_git_url(metadata)

        # Assert
        assert result == "https://github.com/user/repo.git"

    def test_gitlab_url(self, retriever: HybridRetriever) -> None:
        """Test extracting GitLab URL."""
        # Arrange
        metadata = PackageMetadata(
            info=Info(url="https://gitlab.com/user/project"),
            urls=[],
        )

        # Act
        result = retriever._extract_git_url(metadata)

        # Assert
        assert result == "https://gitlab.com/user/project.git"

    def test_bitbucket_url(self, retriever: HybridRetriever) -> None:
        """Test extracting Bitbucket URL."""
        # Arrange
        metadata = PackageMetadata(
            info=Info(url="https://bitbucket.org/user/repo"),
            urls=[],
        )

        # Act
        result = retriever._extract_git_url(metadata)

        # Assert
        assert result == "https://bitbucket.org/user/repo.git"

    def test_non_git_url(self, retriever: HybridRetriever) -> None:
        """Test that non-Git URLs return None."""
        # Arrange
        metadata = PackageMetadata(
            info=Info(url="https://example.com/project"),
            urls=[],
        )

        # Act
        result = retriever._extract_git_url(metadata)

        # Assert
        assert result is None

    def test_empty_url(self, retriever: HybridRetriever) -> None:
        """Test that empty URL returns None."""
        # Arrange
        metadata = PackageMetadata(
            info=Info(url=""),
            urls=[],
        )

        # Act
        result = retriever._extract_git_url(metadata)

        # Assert
        assert result is None


class TestTryGitStrategy:
    """Tests for the _try_git_strategy method."""

    def test_successful_git_strategy(
        self, retriever: HybridRetriever, cloneable_git_repo: str
    ) -> None:
        """Test successful Git strategy workflow."""
        # Arrange
        change = DependencyChange(
            name="test-package",
            old_version="1.0.0",
            new_version="2.0.0",
        )

        # Mock the metadata fetch to return our local git repo
        mock_metadata = PackageMetadata(
            info=Info(url=cloneable_git_repo.replace("file://", "https://github.com/")),
            urls=[],
        )

        with patch.object(retriever, "_fetch_pypi_metadata", return_value=mock_metadata):
            with patch.object(retriever, "_clone_repo", return_value=pathlib.Path(cloneable_git_repo.replace("file://", ""))):
                # Act
                result = retriever._try_git_strategy(change)

        # Assert
        assert result is not None
        assert "requirements.txt" in result
        assert "-requests==2.25.1" in result
        assert "+requests==2.26.0" in result

    def test_git_strategy_with_addition(self, retriever: HybridRetriever) -> None:
        """Test that Git strategy returns None for package additions."""
        # Arrange
        change = DependencyChange(
            name="test-package",
            old_version=None,
            new_version="1.0.0",
        )

        # Act
        result = retriever._try_git_strategy(change)

        # Assert
        assert result is None

    def test_git_strategy_with_removal(self, retriever: HybridRetriever) -> None:
        """Test that Git strategy returns None for package removals."""
        # Arrange
        change = DependencyChange(
            name="test-package",
            old_version="1.0.0",
            new_version=None,
        )

        # Act
        result = retriever._try_git_strategy(change)

        # Assert
        assert result is None

    def test_git_strategy_no_git_url(self, retriever: HybridRetriever) -> None:
        """Test that Git strategy returns None when no Git URL is found."""
        # Arrange
        change = DependencyChange(
            name="test-package",
            old_version="1.0.0",
            new_version="2.0.0",
        )

        # Mock metadata with non-Git URL
        mock_metadata = PackageMetadata(
            info=Info(url="https://example.com/project"),
            urls=[],
        )

        with patch.object(retriever, "_fetch_pypi_metadata", return_value=mock_metadata):
            # Act
            result = retriever._try_git_strategy(change)

        # Assert
        assert result is None

    def test_git_strategy_missing_old_tag(
        self, retriever: HybridRetriever, cloneable_git_repo: str
    ) -> None:
        """Test that Git strategy returns None when old tag is missing."""
        # Arrange
        change = DependencyChange(
            name="test-package",
            old_version="0.5.0",  # This tag doesn't exist
            new_version="2.0.0",
        )

        mock_metadata = PackageMetadata(
            info=Info(url=cloneable_git_repo.replace("file://", "https://github.com/")),
            urls=[],
        )

        with patch.object(retriever, "_fetch_pypi_metadata", return_value=mock_metadata):
            with patch.object(retriever, "_clone_repo", return_value=pathlib.Path(cloneable_git_repo.replace("file://", ""))):
                # Act
                result = retriever._try_git_strategy(change)

        # Assert
        assert result is None

    def test_git_strategy_missing_new_tag(
        self, retriever: HybridRetriever, cloneable_git_repo: str
    ) -> None:
        """Test that Git strategy returns None when new tag is missing."""
        # Arrange
        change = DependencyChange(
            name="test-package",
            old_version="1.0.0",
            new_version="99.0.0",  # This tag doesn't exist
        )

        mock_metadata = PackageMetadata(
            info=Info(url=cloneable_git_repo.replace("file://", "https://github.com/")),
            urls=[],
        )

        with patch.object(retriever, "_fetch_pypi_metadata", return_value=mock_metadata):
            with patch.object(retriever, "_clone_repo", return_value=pathlib.Path(cloneable_git_repo.replace("file://", ""))):
                # Act
                result = retriever._try_git_strategy(change)

        # Assert
        assert result is None

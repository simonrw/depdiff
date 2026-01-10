import pathlib
import subprocess
import tempfile
from typing import Generator

import pytest

from depdiff.comparator import SourceComparator
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

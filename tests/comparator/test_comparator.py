import pathlib
import tempfile
from typing import Generator

import pytest

from depdiff.comparator import SourceComparator


@pytest.fixture
def comparator() -> SourceComparator:
    """Create a SourceComparator instance for testing."""
    return SourceComparator()


@pytest.fixture
def temp_dirs() -> Generator[tuple[pathlib.Path, pathlib.Path], None, None]:
    """Create two temporary directories for testing comparisons."""
    with tempfile.TemporaryDirectory(prefix="old_") as old_dir:
        with tempfile.TemporaryDirectory(prefix="new_") as new_dir:
            yield pathlib.Path(old_dir), pathlib.Path(new_dir)


class TestIsBinary:
    """Tests for the _is_binary method."""

    def test_text_file(self, comparator: SourceComparator, tmp_path: pathlib.Path) -> None:
        """Test that text files are identified as non-binary."""
        # Arrange
        text_file = tmp_path / "test.txt"
        text_file.write_text("Hello, world!\nThis is a text file.")

        # Act
        result = comparator._is_binary(text_file)

        # Assert
        assert result is False

    def test_binary_file(self, comparator: SourceComparator, tmp_path: pathlib.Path) -> None:
        """Test that binary files are identified correctly."""
        # Arrange
        binary_file = tmp_path / "test.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe")

        # Act
        result = comparator._is_binary(binary_file)

        # Assert
        assert result is True

    def test_python_file(self, comparator: SourceComparator, tmp_path: pathlib.Path) -> None:
        """Test that Python files are identified as non-binary."""
        # Arrange
        py_file = tmp_path / "test.py"
        py_file.write_text("def hello():\n    print('Hello, world!')\n")

        # Act
        result = comparator._is_binary(py_file)

        # Assert
        assert result is False


class TestCompareDirectories:
    """Tests for the compare_directories method."""

    def test_identical_directories(
        self, comparator: SourceComparator, temp_dirs: tuple[pathlib.Path, pathlib.Path]
    ) -> None:
        """Test comparison of identical directories."""
        # Arrange
        old_dir, new_dir = temp_dirs
        (old_dir / "file.txt").write_text("Hello")
        (new_dir / "file.txt").write_text("Hello")

        # Act
        result = comparator.compare_directories(old_dir, new_dir)

        # Assert
        assert result == ""

    def test_file_modification(
        self, comparator: SourceComparator, temp_dirs: tuple[pathlib.Path, pathlib.Path]
    ) -> None:
        """Test comparison with a modified file."""
        # Arrange
        old_dir, new_dir = temp_dirs
        (old_dir / "file.txt").write_text("Hello\n")
        (new_dir / "file.txt").write_text("Hello, World\n")

        # Act
        result = comparator.compare_directories(old_dir, new_dir)

        # Assert
        assert "file.txt" in result
        assert "-Hello" in result
        assert "+Hello, World" in result

    def test_file_addition(
        self, comparator: SourceComparator, temp_dirs: tuple[pathlib.Path, pathlib.Path]
    ) -> None:
        """Test comparison with a new file added."""
        # Arrange
        old_dir, new_dir = temp_dirs
        (new_dir / "newfile.txt").write_text("New content\n")

        # Act
        result = comparator.compare_directories(old_dir, new_dir)

        # Assert
        assert "newfile.txt" in result
        assert "+New content" in result
        assert "/dev/null" in result

    def test_file_deletion(
        self, comparator: SourceComparator, temp_dirs: tuple[pathlib.Path, pathlib.Path]
    ) -> None:
        """Test comparison with a file deleted."""
        # Arrange
        old_dir, new_dir = temp_dirs
        (old_dir / "oldfile.txt").write_text("Old content\n")

        # Act
        result = comparator.compare_directories(old_dir, new_dir)

        # Assert
        assert "oldfile.txt" in result
        assert "-Old content" in result
        assert "/dev/null" in result

    def test_nested_directories(
        self, comparator: SourceComparator, temp_dirs: tuple[pathlib.Path, pathlib.Path]
    ) -> None:
        """Test comparison with nested directory structures."""
        # Arrange
        old_dir, new_dir = temp_dirs

        # Create nested structure
        (old_dir / "src").mkdir()
        (old_dir / "src" / "main.py").write_text("print('v1')\n")

        (new_dir / "src").mkdir()
        (new_dir / "src" / "main.py").write_text("print('v2')\n")

        # Act
        result = comparator.compare_directories(old_dir, new_dir)

        # Assert
        assert "src/main.py" in result or "src\\main.py" in result  # Handle Windows paths
        assert "-print('v1')" in result
        assert "+print('v2')" in result

    def test_binary_files_ignored(
        self, comparator: SourceComparator, temp_dirs: tuple[pathlib.Path, pathlib.Path]
    ) -> None:
        """Test that binary files are skipped in comparison."""
        # Arrange
        old_dir, new_dir = temp_dirs
        (old_dir / "data.bin").write_bytes(b"\x00\x01\x02")
        (new_dir / "data.bin").write_bytes(b"\x00\x01\x03")

        # Act
        result = comparator.compare_directories(old_dir, new_dir)

        # Assert
        # Binary files should not appear in diff
        assert result == ""

    def test_multiple_file_changes(
        self, comparator: SourceComparator, temp_dirs: tuple[pathlib.Path, pathlib.Path]
    ) -> None:
        """Test comparison with multiple types of changes."""
        # Arrange
        old_dir, new_dir = temp_dirs

        # Modified file
        (old_dir / "modified.txt").write_text("Old\n")
        (new_dir / "modified.txt").write_text("New\n")

        # Deleted file
        (old_dir / "deleted.txt").write_text("Gone\n")

        # Added file
        (new_dir / "added.txt").write_text("Fresh\n")

        # Act
        result = comparator.compare_directories(old_dir, new_dir)

        # Assert
        assert "modified.txt" in result
        assert "deleted.txt" in result
        assert "added.txt" in result
        assert "-Old" in result
        assert "+New" in result
        assert "-Gone" in result
        assert "+Fresh" in result

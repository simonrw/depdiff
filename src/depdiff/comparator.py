import pathlib
import difflib
from typing import Set


class SourceComparator:
    """
    Compares two source directories to generate a unified diff.
    Acts as a fallback engine when Git native diff is not available.
    """

    def compare_directories(self, old_dir: pathlib.Path, new_dir: pathlib.Path) -> str:
        """
        Recursively compares two directories and generates a unified diff.

        Args:
            old_dir: Path to the directory containing the old version.
            new_dir: Path to the directory containing the new version.

        Returns:
            A string containing the unified diff of the directory contents.
        """
        # Collect all files from both directories
        old_files = self._collect_files(old_dir)
        new_files = self._collect_files(new_dir)

        # Get relative paths for comparison
        old_rel_files = {f.relative_to(old_dir) for f in old_files}
        new_rel_files = {f.relative_to(new_dir) for f in new_files}

        # Determine file changes
        deleted_files = old_rel_files - new_rel_files
        added_files = new_rel_files - old_rel_files
        common_files = old_rel_files & new_rel_files

        diff_lines: list[str] = []

        # Process deleted files
        for rel_path in sorted(deleted_files):
            old_file = old_dir / rel_path
            if not self._is_binary(old_file):
                diff_lines.extend(self._generate_deletion_diff(rel_path, old_file))

        # Process added files
        for rel_path in sorted(added_files):
            new_file = new_dir / rel_path
            if not self._is_binary(new_file):
                diff_lines.extend(self._generate_addition_diff(rel_path, new_file))

        # Process modified files
        for rel_path in sorted(common_files):
            old_file = old_dir / rel_path
            new_file = new_dir / rel_path

            # Skip if either is binary
            if self._is_binary(old_file) or self._is_binary(new_file):
                continue

            # Compare file contents
            diff = self._generate_file_diff(rel_path, old_file, new_file)
            if diff:
                diff_lines.extend(diff)

        return "\n".join(diff_lines)

    def _is_binary(self, file_path: pathlib.Path) -> bool:
        """
        Determines if a file is binary by checking for null bytes.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if the file appears to be binary, False otherwise.
        """
        try:
            # Read first 8KB to check for null bytes
            with open(file_path, "rb") as f:
                chunk = f.read(8192)
                return b"\x00" in chunk
        except Exception:
            # If we can't read it, treat it as binary
            return True

    def _collect_files(self, directory: pathlib.Path) -> Set[pathlib.Path]:
        """
        Recursively collects all files in a directory.

        Args:
            directory: The directory to scan.

        Returns:
            Set of absolute paths to all files in the directory.
        """
        files: Set[pathlib.Path] = set()
        for item in directory.rglob("*"):
            if item.is_file():
                files.add(item)
        return files

    def _generate_deletion_diff(
        self, rel_path: pathlib.Path, old_file: pathlib.Path
    ) -> list[str]:
        """
        Generates a unified diff for a deleted file.

        Args:
            rel_path: Relative path of the file.
            old_file: Absolute path to the old file.

        Returns:
            List of diff lines.
        """
        lines: list[str] = []
        lines.append(f"--- a/{rel_path}")
        lines.append("+++ /dev/null")

        try:
            with open(old_file, "r", encoding="utf-8", errors="replace") as f:
                old_content = f.readlines()

            for i, line in enumerate(old_content, start=1):
                lines.append(f"-{line.rstrip()}")

        except Exception:
            pass

        return lines

    def _generate_addition_diff(
        self, rel_path: pathlib.Path, new_file: pathlib.Path
    ) -> list[str]:
        """
        Generates a unified diff for an added file.

        Args:
            rel_path: Relative path of the file.
            new_file: Absolute path to the new file.

        Returns:
            List of diff lines.
        """
        lines: list[str] = []
        lines.append("--- /dev/null")
        lines.append(f"+++ b/{rel_path}")

        try:
            with open(new_file, "r", encoding="utf-8", errors="replace") as f:
                new_content = f.readlines()

            for i, line in enumerate(new_content, start=1):
                lines.append(f"+{line.rstrip()}")

        except Exception:
            pass

        return lines

    def _generate_file_diff(
        self, rel_path: pathlib.Path, old_file: pathlib.Path, new_file: pathlib.Path
    ) -> list[str]:
        """
        Generates a unified diff for a modified file.

        Args:
            rel_path: Relative path of the file.
            old_file: Absolute path to the old version.
            new_file: Absolute path to the new version.

        Returns:
            List of diff lines, or empty list if files are identical.
        """
        try:
            with open(old_file, "r", encoding="utf-8", errors="replace") as f:
                old_content = f.readlines()

            with open(new_file, "r", encoding="utf-8", errors="replace") as f:
                new_content = f.readlines()

            # Generate unified diff
            diff = difflib.unified_diff(
                old_content,
                new_content,
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
                lineterm="",
            )

            # Strip newlines from each line since readlines() includes them
            # and we'll be joining with newlines later
            diff_lines = [line.rstrip("\n") for line in diff]

            # Only return if there are actual changes (more than just headers)
            if len(diff_lines) > 2:
                return diff_lines

            return []

        except Exception:
            return []

from typing import List

from packaging.requirements import Requirement

from depdiff.models import DependencyChange


class DiffParser:
    """Parses unified diff input to identify dependency changes."""

    _dependency_changes: dict[str, DependencyChange]

    def __init__(self):
        self._dependency_changes = {}

    def parse(self, diff_content: str) -> List[DependencyChange]:
        """
        Parses a unified diff string and returns a list of dependency changes.

        Args:
            diff_content: The content of the unified diff.

        Returns:
            A list of DependencyChange objects representing version bumps, additions, or removals.
        """
        for line in diff_content.splitlines():
            if line.startswith("+") and line[1] != "+":
                req = Requirement(line[1:].strip())
                version = list(req.specifier)[0].version

                if req.name in self._dependency_changes:
                    self._dependency_changes[req.name].new_version = version
                else:
                    self._dependency_changes[req.name] = DependencyChange(
                        req.name, old_version=None, new_version=version
                    )

            elif line.startswith("-") and line[1] != "-":
                req = Requirement(line[1:].strip())
                version = list(req.specifier)[0].version

                if req.name in self._dependency_changes:
                    self._dependency_changes[req.name].old_version = version
                else:
                    self._dependency_changes[req.name] = DependencyChange(
                        req.name, old_version=version, new_version=None
                    )
            else:
                continue

        return list(self._dependency_changes.values())

    def _split_dependency_specification(self, line: str) -> tuple[str, str]:
        for i, c in enumerate(line):
            if not c.isalnum():
                return (line[:i], line[i:])

        raise RuntimeError(f"Could not parse specification: {line}")

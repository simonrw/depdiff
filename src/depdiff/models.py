from dataclasses import dataclass
from typing import Optional


@dataclass
class DependencyChange:
    """Represents a change in a dependency version."""

    name: str
    old_version: Optional[str]
    new_version: Optional[str]

    @property
    def is_addition(self) -> bool:
        return self.old_version is None and self.new_version is not None

    @property
    def is_removal(self) -> bool:
        return self.old_version is not None and self.new_version is None

    @property
    def is_update(self) -> bool:
        return self.old_version is not None and self.new_version is not None

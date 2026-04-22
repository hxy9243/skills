from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class CategoryPath:
    """Normalized category lineage such as `Computer Science > AI Systems`."""

    parts: tuple[str, ...]

    @classmethod
    def parse(cls, value: str) -> "CategoryPath":
        """Parse a `>`-delimited category string into canonical path parts."""
        parts = tuple(part.strip() for part in value.split(">") if part.strip())
        if not parts:
            raise ValueError("category must not be empty")
        return cls(parts)

    def display(self) -> str:
        """Render the path in packet/frontmatter display form."""
        return " > ".join(self.parts)

    def layer_labels(self) -> tuple[str, ...]:
        """Render prompt-friendly labels such as `layer1: Computer Science`."""
        return tuple(
            f"layer{index}: {part}" for index, part in enumerate(self.parts, start=1)
        )

    def slug_parts(self) -> tuple[str, ...]:
        """Render filesystem-safe path parts for generated category pages."""
        return tuple(_slugify(part) for part in self.parts)

    def to_json(self) -> str:
        """Serialize category paths as their display string."""
        return self.display()


def _slugify(value: str) -> str:
    """Make a stable lowercase slug for category page paths."""
    chars: list[str] = []
    previous_dash = False
    for char in value.lower():
        if char.isalnum():
            chars.append(char)
            previous_dash = False
        elif not previous_dash:
            chars.append("-")
            previous_dash = True
    return "".join(chars).strip("-")

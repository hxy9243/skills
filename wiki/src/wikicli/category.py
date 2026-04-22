from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class CategoryPath:
    parts: tuple[str, ...]

    @classmethod
    def parse(cls, value: str) -> "CategoryPath":
        parts = tuple(part.strip() for part in value.split(">") if part.strip())
        if not parts:
            raise ValueError("category must not be empty")
        return cls(parts)

    def display(self) -> str:
        return " > ".join(self.parts)

    def layer_labels(self) -> tuple[str, ...]:
        return tuple(f"layer{index}: {part}" for index, part in enumerate(self.parts, start=1))

    def slug_parts(self) -> tuple[str, ...]:
        return tuple(_slugify(part) for part in self.parts)

    def to_json(self) -> str:
        return self.display()


def _slugify(value: str) -> str:
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

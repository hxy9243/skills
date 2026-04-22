from __future__ import annotations

from collections.abc import Iterable

from .app import Issue
from .config import WikiConfig


def lint_workspace(config: WikiConfig) -> Iterable[Issue]:
    """Yield read-only integrity issues for the resolved wiki workspace."""
    if not config.notebook_root.exists():
        yield Issue(
            "notebook_root_missing",
            "notebook root does not exist",
            path=str(config.notebook_root),
        )
    if not config.generated_root.exists():
        yield Issue(
            "generated_root_missing",
            "generated root does not exist",
            severity="warning",
            path=str(config.generated_root),
        )

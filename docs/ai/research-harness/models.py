"""Shared data structures passed between the query, physics, and rendering layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Investigation:
    """The complete result of running one research query.

    The harness hands this to the report builder; nothing in here is
    HTML-specific, so the same object could feed a PDF or notebook later.
    """

    slug: str
    title: str
    question: str
    params: dict[str, Any]
    summary: str                       # one-paragraph plain-language answer
    findings: list[str]                # bullet takeaways
    equations: list[tuple[str, str]]   # (rendered_equation, description)
    assumptions: list[str]
    table_text: str                    # monospace results table
    ascii_blocks: list[tuple[str, str]] = field(default_factory=list)  # (title, body)
    figures: list[dict] = field(default_factory=list)  # {name, path, caption}
    references: list[str] = field(default_factory=list)

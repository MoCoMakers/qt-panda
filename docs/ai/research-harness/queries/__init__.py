"""Query registry.

A *query* is a self-contained research question. Each module exposes:
    SLUG: str
    def run(out_dir: Path, **overrides) -> Investigation

Register new questions in REGISTRY below and they become runnable from the CLI.
"""

from __future__ import annotations

from . import tip_displacement_length
from . import thermal_displacement_gold

REGISTRY = {
    tip_displacement_length.SLUG: tip_displacement_length,
    thermal_displacement_gold.SLUG: thermal_displacement_gold,
}

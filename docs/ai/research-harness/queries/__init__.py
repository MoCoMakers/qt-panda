"""Query registry.

A *query* is a self-contained research question. Each module exposes:
    SLUG: str
    def run(out_dir: Path, **overrides) -> Investigation

Register new questions in REGISTRY below and they become runnable from the CLI.
"""

from __future__ import annotations

from . import tip_displacement_length
from . import thermal_displacement_gold
from . import wedge_lever_gearing
from . import wedge_piezo_position
from . import wedge_geared_stage
from . import scan_dwell_fidelity

REGISTRY = {
    tip_displacement_length.SLUG: tip_displacement_length,
    thermal_displacement_gold.SLUG: thermal_displacement_gold,
    wedge_lever_gearing.SLUG: wedge_lever_gearing,
    wedge_piezo_position.SLUG: wedge_piezo_position,
    wedge_geared_stage.SLUG: wedge_geared_stage,
    scan_dwell_fidelity.SLUG: scan_dwell_fidelity,
}

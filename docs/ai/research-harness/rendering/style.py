"""Shared matplotlib styling so every figure in a report looks consistent.

Centralising style here is what lets the agent-review loop converge: when a
review flags "labels too small" or "palette clashes", the fix lives in one
place and propagates to every figure.
"""

from __future__ import annotations

import matplotlib as mpl

# Colour-blind-safe palette (Okabe-Ito), assigned to semantic roles.
PALETTE = {
    "short": "#0072B2",   # blue   -> short tip (1 mm)
    "long": "#D55E00",    # orange -> long tip (10 mm)
    "accent": "#009E73",  # green  -> highlighted/exact
    "muted": "#7F7F7F",   # grey   -> approximations / guides
    "ideal": "#444444",   # near-black -> nominal/ideal geometry
}

FIG_DPI = 150


def apply_house_style() -> None:
    """Apply a clean, publication-leaning rcParams profile."""
    mpl.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "savefig.dpi": FIG_DPI,
            "figure.dpi": FIG_DPI,
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.labelsize": 11,
            "axes.grid": True,
            "grid.color": "#E6E6E6",
            "grid.linewidth": 0.8,
            "axes.axisbelow": True,
            "axes.edgecolor": "#666666",
            "axes.linewidth": 1.0,
            "xtick.color": "#333333",
            "ytick.color": "#333333",
            "legend.frameon": True,
            "legend.framealpha": 0.9,
            "legend.edgecolor": "#CCCCCC",
            "lines.linewidth": 2.0,
        }
    )

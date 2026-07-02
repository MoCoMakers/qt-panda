"""Matplotlib figures for the tip-displacement investigation.

Every function takes an explicit output path and returns it, so the harness
can collect a manifest of generated artifacts for the agent-review loop.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from physics.piezo_tip import tip_displacement, tip_displacement_mm_deg
from rendering.style import PALETTE, apply_house_style


def _annotate_value(ax, x, y, text, color, dy=8):
    ax.annotate(
        text,
        xy=(x, y),
        xytext=(0, dy),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=9,
        color=color,
        fontweight="bold",
    )


def _draw_tip_panel(ax, L, theta_deg, color, draw_deg):
    """One schematic panel: a single tip of length L, tilt drawn exaggerated.

    Geometry within the panel is normalised to L (the tip is one unit long),
    so a 1 mm and a 10 mm tip look the same size; only the *labels* differ.
    The lateral offset is drawn at ``draw_deg`` (exaggerated) for legibility,
    while the printed Delta x / Delta z are the exact values at ``theta_deg``.
    """
    d = tip_displacement_mm_deg(L, theta_deg)
    draw = math.radians(draw_deg)

    # Mounting face.
    ax.add_patch(plt.Rectangle((-0.45, -0.16), 0.9, 0.16, facecolor="#D9D9D9",
                               edgecolor="#666666", hatch="////", zorder=1))
    ax.text(0, -0.085, "piezo face", ha="center", va="center",
            fontsize=8, color="#333333")

    # Ideal (vertical) axis. Label placed mid-height to the left so it never
    # collides with the apex callouts at the top.
    ax.plot([0, 0], [0, 1.0], color=PALETTE["ideal"], lw=1.2,
            ls=(0, (5, 4)), alpha=0.6, zorder=2)
    ax.text(-0.06, 0.62, "ideal axis", color=PALETTE["ideal"], fontsize=8,
            alpha=0.85, ha="right", va="center", rotation=90)

    # Tilted tip (exaggerated angle, unit length).
    tx, ty = math.sin(draw), math.cos(draw)
    ax.plot([0, tx], [0, ty], color=color, lw=3.0, solid_capstyle="round", zorder=3)
    ax.plot([tx], [ty], "o", color=color, ms=9, zorder=4)
    ax.plot([0], [1.0], "o", color=PALETTE["ideal"], ms=6, alpha=0.5, zorder=3)

    # Angle arc + label.
    arc = np.linspace(math.pi / 2, math.pi / 2 - draw, 40)
    ax.plot(0.32 * np.cos(arc), 0.32 * np.sin(arc), color=PALETTE["accent"], lw=1.6)
    ax.text(0.20, 0.40, f"$\\theta$ = {theta_deg:g}$\\degree$",
            color=PALETTE["accent"], fontsize=11, fontweight="bold")

    # Lateral-offset arrow between ideal apex and tilted apex.
    ax.annotate("", xy=(tx, ty), xytext=(0, ty),
                arrowprops=dict(arrowstyle="<->", color=color, lw=1.6))
    ax.text(tx / 2, ty + 0.05, f"$\\Delta x$ = {d.lateral_um:.1f} $\\mu$m",
            ha="center", va="bottom", color=color, fontsize=10, fontweight="bold")
    ax.text(tx + 0.05, ty - 0.08, f"$\\Delta z$ = {d.vertical_um:.2f} $\\mu$m",
            ha="left", va="top", color=color, fontsize=9.5)

    ax.set_title(f"L = {L:g} mm", color=color, fontsize=13)
    ax.set_xlim(-0.55, 0.9)
    ax.set_ylim(-0.25, 1.2)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)


def fig_geometry_schematic(out: Path, theta_deg: float, lengths_mm) -> Path:
    """Side-view schematic: one panel per tip length.

    The tilt is drawn deliberately exaggerated (a true 2 deg tilt is invisible
    at this scale); a figure note states this and the printed displacement
    values are exact. Each tip is normalised to unit length so both panels are
    legible regardless of the 10x length difference.
    """
    apply_house_style()
    draw_deg = 18.0  # exaggerated tilt purely for visualisation
    colors = [PALETTE["short"], PALETTE["long"], PALETTE["accent"], PALETTE["muted"]]
    n = len(lengths_mm)
    fig, axes = plt.subplots(1, n, figsize=(3.4 * n, 4.8))
    if n == 1:
        axes = [axes]
    for ax, L, c in zip(axes, lengths_mm, colors):
        _draw_tip_panel(ax, L, theta_deg, c, draw_deg)

    fig.suptitle(f"Tip tilt geometry at a {theta_deg:g}° offset",
                 fontsize=15, fontweight="bold", y=0.99)
    fig.text(0.5, 0.02,
             f"Schematic — tilt exaggerated to {draw_deg:g}° (true {theta_deg:g}°); "
             f"tips normalised to equal length. Δx, Δz values are exact.",
             ha="center", fontsize=8, color="#666666", style="italic", wrap=True)
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    fig.savefig(out)
    plt.close(fig)
    return out


def fig_bar_comparison(out: Path, theta_deg: float, lengths_mm) -> Path:
    """Grouped bars: lateral vs vertical apex error for each tip length."""
    apply_house_style()
    fig, ax = plt.subplots(figsize=(7.2, 4.6))

    metrics = ["lateral  $\\Delta x$", "vertical  $\\Delta z$"]
    x = np.arange(len(metrics))
    width = 0.36
    colors = [PALETTE["short"], PALETTE["long"]]

    for i, (L, c) in enumerate(zip(lengths_mm, colors)):
        d = tip_displacement_mm_deg(L, theta_deg)
        vals = [d.lateral_um, d.vertical_um]
        bars = ax.bar(x + (i - 0.5) * width, vals, width,
                      color=c, edgecolor="white", label=f"L = {L:g} mm")
        for rect, v in zip(bars, vals):
            ax.annotate(f"{v:.2f}", xy=(rect.get_x() + rect.get_width() / 2,
                        rect.get_height()),
                        xytext=(0, 4), textcoords="offset points",
                        ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.set_ylabel("apex displacement ($\\mu$m)")
    ax.set_title(f"Apex error components at $\\theta$ = {theta_deg:g}°")
    ax.legend()
    ax.margins(y=0.18)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def fig_length_sweep(out: Path, theta_deg: float, lengths_mm) -> Path:
    """Continuous sweep of apex error vs tip length, with markers at L of interest."""
    apply_house_style()
    fig, ax = plt.subplots(figsize=(7.2, 4.6))

    Ls = np.linspace(0, max(lengths_mm) * 1.2, 400)
    lat = np.array([tip_displacement_mm_deg(L, theta_deg).lateral_um for L in Ls])
    ver = np.array([tip_displacement_mm_deg(L, theta_deg).vertical_um for L in Ls])

    ax.plot(Ls, lat, color=PALETTE["short"], label="lateral $\\Delta x = L\\sin\\theta$")
    ax.plot(Ls, ver, color=PALETTE["long"], label="vertical $\\Delta z = L(1-\\cos\\theta)$")

    colors = [PALETTE["accent"], PALETTE["ideal"]]
    for L, c in zip(lengths_mm, colors):
        d = tip_displacement_mm_deg(L, theta_deg)
        ax.axvline(L, color=c, ls=":", lw=1.2, alpha=0.7)
        ax.plot([L], [d.lateral_um], "o", color=PALETTE["short"], ms=7)
        ax.plot([L], [d.vertical_um], "s", color=PALETTE["long"], ms=6)
        ax.annotate(f"L={L:g} mm\n{d.lateral_um:.1f} $\\mu$m",
                    xy=(L, d.lateral_um), xytext=(6, -2),
                    textcoords="offset points", fontsize=8.5,
                    color=PALETTE["short"], fontweight="bold")

    ax.set_xlabel("tip length L (mm)")
    ax.set_ylabel("apex displacement ($\\mu$m)")
    ax.set_title(f"Displacement scales linearly with tip length ($\\theta$ = {theta_deg:g}°)")
    ax.legend(loc="upper left")
    ax.set_xlim(0, max(Ls))
    ax.set_ylim(0, lat.max() * 1.12)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def fig_angle_sweep(out: Path, theta_deg: float, lengths_mm) -> Path:
    """Lateral error vs offset angle for each tip length (log y)."""
    apply_house_style()
    fig, ax = plt.subplots(figsize=(7.2, 4.6))

    thetas = np.linspace(0.05, 5.0, 300)
    colors = [PALETTE["short"], PALETTE["long"]]
    for L, c in zip(lengths_mm, colors):
        lat = np.array([tip_displacement_mm_deg(L, t).lateral_um for t in thetas])
        ax.plot(thetas, lat, color=c, label=f"L = {L:g} mm")
        d = tip_displacement_mm_deg(L, theta_deg)
        ax.plot([theta_deg], [d.lateral_um], "o", color=c, ms=7)

    ax.axvline(theta_deg, color=PALETTE["muted"], ls="--", lw=1.2)
    ax.text(theta_deg + 0.08, ax.get_ylim()[1] * 0.5,
            f"operating point\n$\\theta$ = {theta_deg:g}°",
            fontsize=8.5, color=PALETTE["muted"])
    ax.set_yscale("log")
    ax.set_xlabel("angular offset $\\theta$ (degrees)")
    ax.set_ylabel("lateral apex displacement ($\\mu$m, log)")
    ax.set_title("Lateral error vs angular offset")
    ax.legend(loc="lower right")
    ax.set_xlim(0, 5)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def generate_all(out_dir: Path, theta_deg: float, lengths_mm) -> list[dict]:
    """Generate every figure and return a manifest for the report + review loop."""
    out_dir.mkdir(parents=True, exist_ok=True)
    specs = [
        ("geometry", fig_geometry_schematic,
         "Side-view geometry of the tilted tips, drawn to scale."),
        ("bars", fig_bar_comparison,
         "Lateral vs vertical apex error for each tip length."),
        ("length_sweep", fig_length_sweep,
         "Apex displacement as a continuous function of tip length."),
        ("angle_sweep", fig_angle_sweep,
         "Lateral error vs angular offset, log scale."),
    ]
    manifest = []
    for name, fn, caption in specs:
        path = out_dir / f"{name}.png"
        fn(path, theta_deg, lengths_mm)
        manifest.append({"name": name, "path": path, "caption": caption})
    return manifest

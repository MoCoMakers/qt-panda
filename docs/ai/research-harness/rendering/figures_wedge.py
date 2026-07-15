"""Matplotlib figures for the wedge-lever gearing investigation.

Same contract as ``figures.py``: every function takes an output path,
returns it, and ``generate_all`` builds the review manifest.

Figure order tells the story of the AS-BUILT rig (WedgeDesign v37):
  1. chain      — one motor step walked through the four stages (log scale)
  2. geometry   — the as-built lever geometry, to scale
  3. budget     — full-stroke and piezo-handoff step budgets
  4. wedge_sizes, length_sweep — design-space APPENDIX (scenario rules)
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from physics import wedge_lever as wl
from rendering.style import PALETTE, apply_house_style

# Semantic colors for the three example plate lengths (Okabe-Ito).
LENGTH_COLORS = [PALETTE["short"], PALETTE["accent"], PALETTE["long"]]


def fig_chain(path: Path, plate_lengths_mm, wedge_size: str) -> Path:
    """One motor step through the reduction chain — horizontal log-scale bars."""
    apply_house_style()
    g = wl.as_built_gearing()

    stages = [
        ("Stage 2 — stick slide s\n(m=1 z=10 pinion, 31.416 mm/rev / 4096)",
         g.travel_per_step_nm, PALETTE["muted"]),
        ("Stage 3 — lift under the lid lip\ns × tan 7.2527° (= 3.5/27.5)",
         g.dz_wedge_nm, PALETTE["long"]),
        ("Stage 4 — TIP Z PER STEP\n× lever 76.26/120.15",
         g.dz_tip_nm, PALETTE["short"]),
        ("Stage 4b — lateral Abbe walk\n× collet 8/120.15",
         g.dx_tip_nm, PALETTE["accent"]),
    ]
    factors = ["× 0.12727", "× 0.63470", "(same Δφ, × 8 mm)"]

    fig, ax = plt.subplots(figsize=(9.4, 5.0))
    y = np.arange(len(stages))[::-1]
    for yi, (label, v, color) in zip(y, stages):
        ax.barh(yi, v, height=0.5, color=color, alpha=0.9)
        ax.text(v, yi + 0.33, f"{v:,.1f} nm", va="bottom", ha="right", fontsize=11,
                fontweight="bold", color=color)
        ax.text(0.985, yi, label, va="center", ha="right", fontsize=9.5,
                transform=ax.get_yaxis_transform())
    # factor arrows between consecutive bars
    for i, f in enumerate(factors):
        y0, y1 = y[i], y[i + 1]
        v1 = stages[i + 1][1]
        ax.annotate("", xy=(v1, y1 + 0.42), xytext=(v1, y0 - 0.42),
                    arrowprops=dict(arrowstyle="->", color="#555", lw=1.3))
        ax.text(v1 * 1.15, (y0 + y1) / 2, f, fontsize=9, color="#555",
                va="center", style="italic")

    ax.axvline(wl.TUNNELING_WINDOW_NM, color=PALETTE["ideal"], ls=":", lw=1.4)
    ax.text(wl.TUNNELING_WINDOW_NM * 1.1, y[0] + 0.55, "~1 nm tunneling window",
            fontsize=8.5, color=PALETTE["ideal"], rotation=0, va="bottom")
    ax.axvspan(wl.PIEZO_REACH_UM[0] * 1e3, wl.PIEZO_REACH_UM[1] * 1e3,
               color=PALETTE["ideal"], alpha=0.10, lw=0)
    ax.text(math.sqrt(wl.PIEZO_REACH_UM[0] * wl.PIEZO_REACH_UM[1]) * 1e3, y[0] + 0.55,
            "piezo Z reach\n15–50 µm", fontsize=8.5, color=PALETTE["ideal"],
            ha="center", va="bottom")

    ax.set_xscale("log")
    ax.set_xlim(0.5, 1.2e5)
    ax.set_ylim(-0.7, len(stages) - 0.1 + 0.8)
    ax.set_yticks([])
    ax.set_xlabel("motion per motor half-step (nm, log scale)")
    ax.set_title("One motor step through the as-built chain "
                 f"→ tip Z = {g.dz_tip_nm:.1f} nm/step")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def fig_geometry(path: Path, plate_lengths_mm, wedge_size: str) -> Path:
    """Side view of the AS-BUILT lever geometry (pin frame, fully to scale).

    Drawn at the TRUE contact pose (1.669°): the lip corner rests exactly
    on the wedge crest, 3.5 mm above the parting plane.
    """
    apply_house_style()
    r_p = wl.ASBUILT_LEVER_MM
    d_w = wl.LIP_ARM_MM
    c = wl.COLLET_STANDOFF_MM
    rise = wl.WEDGE_RISE_MM
    run = wl.WEDGE_RUN_ASBUILT_MM
    phi = math.asin(rise / d_w)   # 1.669° — the real contact pose

    fig, ax = plt.subplots(figsize=(10.2, 5.2))

    # Sample (bottom) plate: static, top surface at y = 0 (the parting plane).
    ax.add_patch(plt.Rectangle((-147.65, -12), 145.0, 12, facecolor="#D9D9D9",
                               edgecolor="#666666", zorder=1))
    ax.text(-30, -9.5, "sample plate (static)", ha="center", fontsize=9, color="#333")

    # Lid: rotated OPEN by phi about the pin (lip end lifts): rotate by -phi.
    rot = np.array([[math.cos(-phi), -math.sin(-phi)],
                    [math.sin(-phi), math.cos(-phi)]])
    corners = np.array([[0, 0], [-d_w, 0], [-d_w, 9], [0, 9]], dtype=float)
    top = corners @ rot.T
    ax.add_patch(plt.Polygon(top, closed=True, facecolor="#EFEFEF",
                             edgecolor="#666666", zorder=2))
    ax.text(-62, 9.6, "lid (117.5 mm, lip corner at 120.15)", fontsize=9, color="#333")

    # Hinge pin.
    ax.plot(0, 0, "o", ms=11, color=PALETTE["ideal"], zorder=6)
    ax.annotate("hinge pin (pivot)\nON the parting plane", xy=(0, 0), xytext=(8, 12),
                textcoords="offset points", fontsize=9, color=PALETTE["ideal"])

    # Wedge under the lip: crest (3.5 tall) at the lip contact, thin edge toward pin.
    wedge_pts = np.array([[-d_w, 0], [-d_w + run, 0], [-d_w, rise]])
    ax.add_patch(plt.Polygon(wedge_pts, closed=True, facecolor=PALETTE["long"],
                             edgecolor="#8a3d00", alpha=0.9, zorder=3))
    ax.annotate("M12 wedge — slope 3.5/27.5 (7.25°)\npulled LEFT by the glued stick",
                xy=(-d_w + run * 0.35, rise * 0.55), xytext=(-d_w - 38, 17),
                fontsize=9, color=PALETTE["long"], fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=PALETTE["long"], lw=1.4))

    # Push stick (rides the channel, body 83.2..88.0 -> -2.5..+2.3 here).
    ax.add_patch(plt.Rectangle((-162, -2.5), 162 - d_w - 0.05, 4.8,
                               facecolor="#F5F2E8", edgecolor="#999", zorder=2))
    ax.annotate("push stick → to the m=1 z=10 pinion + 28BYJ-48 (off-frame left)",
                xy=(-160, -9.0), fontsize=8.5, color="#666", ha="left")

    # Piezo + collet + tip on the rotated lid.
    bore = np.array([-r_p, 0.0]) @ rot.T
    tip = bore + np.array([0.0, -c])   # collet hangs down from the lid
    ax.plot([bore[0]], [bore[1]], "s", ms=9, color=PALETTE["short"], zorder=5)
    ax.plot([bore[0], tip[0]], [bore[1], tip[1]], color=PALETTE["short"], lw=2.5, zorder=4)
    ax.plot([tip[0]], [tip[1]], "v", ms=8, color=PALETTE["short"], zorder=5)
    ax.annotate("piezo center", xy=(bore[0], bore[1]), xytext=(-4, 12),
                textcoords="offset points", ha="center", fontsize=9,
                color=PALETTE["short"], fontweight="bold")
    ax.annotate(f"collet + tip  c = {c:g} mm", xy=(tip[0], tip[1]), xytext=(-96, -4),
                textcoords="offset points", fontsize=9, color=PALETTE["short"])

    # Dimension lines.
    for dist, y, label, color in (
            (r_p, -18.5, f"lever  $r_p$ = {r_p:.2f} mm (pin → piezo)", PALETTE["short"]),
            (d_w, -25.5, f"lip arm  $d_w$ = {d_w:.2f} mm (pin → wedge contact)", PALETTE["long"])):
        ax.annotate("", xy=(-dist, y), xytext=(0, y),
                    arrowprops=dict(arrowstyle="<->", color=color, lw=1.4))
        ax.text(-dist / 2, y - 1.3, label, ha="center", va="top", fontsize=10,
                color=color, fontweight="bold")

    ax.set_title("As-built lever geometry, TO SCALE at the real contact pose "
                 "(lid open 1.669°)", fontsize=11)
    ax.set_xlim(-168, 30)
    ax.set_ylim(-33, 26)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("mm (pin at 0, stage extends left; parting plane at y = 0)")
    ax.grid(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def fig_budget(path: Path, plate_lengths_mm, wedge_size: str) -> Path:
    """As-built budgets: cumulative tip travel vs steps + handoff-zone steps."""
    apply_house_style()
    g = wl.as_built_gearing()
    g_lead = wl.leadscrew_gearing()
    full_steps = wl.asbuilt_full_stroke_steps()
    full_mm = wl.asbuilt_full_range_mm()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.0, 4.6))

    # Panel A: tip Z travelled vs motor steps (the whole approach is a line).
    steps = np.linspace(0, full_steps, 200)
    ax1.plot(steps, steps * g.dz_tip_nm * 1e-6, color=PALETTE["short"], lw=2)
    ax1.annotate(f"slope = {g.dz_tip_nm:.1f} nm/step",
                 xy=(full_steps * 0.5, full_mm * 0.5), xytext=(-10, 22),
                 textcoords="offset points", fontsize=10, color=PALETTE["short"],
                 fontweight="bold")
    ax1.axhline(full_mm, color=PALETTE["muted"], ls=":", lw=1.2)
    ax1.text(80, full_mm + 0.03, f"full 27.5 mm wedge run = {full_steps:,.0f} steps "
             f"→ {full_mm:.2f} mm of tip Z", fontsize=8.5, color=PALETTE["muted"])
    # handoff zone: the last 15–50 µm before contact
    z_lo = full_mm - wl.PIEZO_REACH_UM[1] * 1e-3
    z_hi = full_mm - wl.PIEZO_REACH_UM[0] * 1e-3
    ax1.axhspan(z_lo, full_mm, color=PALETTE["ideal"], alpha=0.15, lw=0)
    ax1.annotate(f"piezo handoff zone (last 15–50 µm)\n= final "
                 f"{g.steps_across_reach_um(wl.PIEZO_REACH_UM[0]):,.0f}–"
                 f"{g.steps_across_reach_um(wl.PIEZO_REACH_UM[1]):,.0f} steps",
                 xy=(full_steps * 0.72, full_mm), xytext=(-30, -42),
                 textcoords="offset points", fontsize=8.5, color=PALETTE["ideal"],
                 arrowprops=dict(arrowstyle="->", color=PALETTE["ideal"], lw=1.1))
    ax1.set_xlabel("motor half-steps")
    ax1.set_ylabel("tip Z travelled (mm)")
    ax1.set_title("The full approach is one line:\n"
                  f"{g.dz_tip_nm:.1f} nm per step, {full_steps:,.0f} steps end to end")
    ax1.set_xlim(0, full_steps * 1.02)
    ax1.set_ylim(0, full_mm * 1.12)

    # Panel B: steps to cross the piezo reach — as-built vs leadscrew upgrade.
    labels = [f"{wl.PIEZO_REACH_UM[0]:g} µm reach", f"{wl.PIEZO_REACH_UM[1]:g} µm reach"]
    x = np.arange(2)
    rack = [g.steps_across_reach_um(u) for u in wl.PIEZO_REACH_UM]
    lead = [g_lead.steps_across_reach_um(u) for u in wl.PIEZO_REACH_UM]
    b1 = ax2.bar(x - 0.18, rack, 0.34, color=PALETTE["short"],
                 label=f"as built ({g.dz_tip_nm:.0f} nm/step)")
    b2 = ax2.bar(x + 0.18, lead, 0.34, color=PALETTE["accent"],
                 label=f"M3 leadscrew ({g_lead.dz_tip_nm:.1f} nm/step)")
    for bars in (b1, b2):
        for b in bars:
            ax2.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.12,
                     f"{b.get_height():,.0f}", ha="center", fontsize=9, fontweight="bold")
    ax2.set_yscale("log")
    ax2.set_ylim(8, 3e4)
    ax2.set_xticks(x); ax2.set_xticklabels(labels)
    ax2.set_ylabel("motor steps (log)")
    ax2.set_title("Steps to cross the piezo handoff zone:\nas built vs round-2 leadscrew")
    ax2.legend(fontsize=8.5)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def fig_wedge_sizes(path: Path, plate_lengths_mm, wedge_size: str) -> Path:
    """APPENDIX: per-step tip Z for every washer in the kit (leadscrew baseline)."""
    apply_house_style()
    sizes = list(wl.WEDGE_ANGLES_DEG)
    x = np.arange(len(sizes))
    width = 0.26

    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    for i, (Lx, color) in enumerate(zip(plate_lengths_mm, LENGTH_COLORS)):
        vals = [wl.step_gearing(Lx, wl.WEDGE_ANGLES_DEG[s]).dz_tip_nm for s in sizes]
        bars = ax.bar(x + (i - 1) * width, vals, width, color=color,
                      label=f"{Lx:g} mm plates ($r_p$={wl.lever_from_plate_length(Lx):.1f} mm)")
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.2, f"{v:.1f}",
                    ha="center", va="bottom", fontsize=8, color=color)
    ax.axhspan(0, wl.TUNNELING_WINDOW_NM, color=PALETTE["accent"], alpha=0.18, lw=0)
    ax.text(-0.55, wl.TUNNELING_WINDOW_NM + 0.25, "~1 nm tunneling window",
            ha="left", fontsize=8.5, color=PALETTE["accent"],
            bbox=dict(facecolor="white", alpha=0.85, edgecolor="none", pad=1.5))
    ax.set_xticks(x)
    ax.set_xticklabels([f"{s}\n{wl.WEDGE_ANGLES_DEG[s]:g}°" for s in sizes])
    ax.set_xlabel("beveled washer (wedge angle)")
    ax.set_ylabel("tip Z motion per motor step (nm)")
    ax.set_title("APPENDIX (design space) — wedge choice dominates; plate length only "
                 f"trims the lever ratio\n(evaluated at the {wl.BASELINE_TRAVEL_PER_STEP_NM:.1f} "
                 "nm/step M3-leadscrew drive)")
    ax.set_ylim(0, 22)
    ax.legend(loc="upper center", ncol=3, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def fig_length_sweep(path: Path, plate_lengths_mm, wedge_size: str) -> Path:
    """APPENDIX: tip Z per step vs plate length (scenario layout rules)."""
    apply_house_style()
    theta = wl.WEDGE_ANGLES_DEG[wedge_size]
    L = np.linspace(55, 130, 300)
    follow = [wl.step_gearing(x, theta).dz_tip_nm for x in L]
    fixed_arm = wl.wedge_arm_from_plate_length(70.0)  # old front rail at 72.65 mm
    fixed = [wl.step_gearing(x, theta, wedge_arm_mm=fixed_arm).dz_tip_nm
             for x in L if wl.lever_from_plate_length(x) <= fixed_arm]
    Lfix = L[: len(fixed)]

    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    ax.plot(L, follow, color=PALETTE["short"], label="wedge at plate front edge ($d_w$ grows with plate)")
    ax.plot(Lfix, fixed, color=PALETTE["long"], ls="--",
            label=f"wedge on fixed rail at {fixed_arm:.1f} mm (bore stays inboard)")
    ax.axhline(wl.BEST_LONGBOARD_NM_PER_STEP, color=PALETTE["ideal"], lw=1.2, ls=":")
    ax.text(L[-1], wl.BEST_LONGBOARD_NM_PER_STEP - 0.35,
            f"best documented longboard ({wl.BEST_LONGBOARD_NM_PER_STEP:g} nm/step)",
            ha="right", va="top", fontsize=8.5, color=PALETTE["ideal"])

    for Lx, color in zip(plate_lengths_mm, LENGTH_COLORS):
        g = wl.step_gearing(Lx, theta)
        ax.plot([Lx], [g.dz_tip_nm], "o", ms=9, color=color, zorder=5)
        ax.annotate(f"{Lx:g} mm plates\n{g.dz_tip_nm:.2f} nm/step",
                    xy=(Lx, g.dz_tip_nm), xytext=(6, -26), textcoords="offset points",
                    fontsize=9, color=color, fontweight="bold")

    # As-built lever/arm at the leadscrew drive — off both scenario curves.
    ab = wl.leadscrew_gearing()
    ax.plot([wl.PLATE_LENGTH_NOW_MM], [ab.dz_tip_nm], "*", ms=16,
            color=PALETTE["accent"], zorder=6, markeredgecolor="white")
    ax.annotate(f"AS-BUILT geometry (lip rides wedge,\n$d_w$={ab.wedge_arm_mm:.1f} mm): "
                f"{ab.dz_tip_nm:.2f} nm/step",
                xy=(wl.PLATE_LENGTH_NOW_MM, ab.dz_tip_nm), xytext=(10, -34),
                textcoords="offset points", fontsize=9, color=PALETTE["accent"],
                fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=PALETTE["accent"], lw=1.2))

    ax.set_xlabel("plate length (mm)")
    ax.set_ylabel("tip Z motion per motor step (nm)")
    ax.set_title(f"APPENDIX (design space) — fineness vs plate length, {wedge_size} wedge "
                 f"({theta:g}°)\n(evaluated at the {wl.BASELINE_TRAVEL_PER_STEP_NM:.1f} "
                 "nm/step M3-leadscrew drive)")
    ax.set_ylim(0, 30)
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def generate_all(out_dir: Path, plate_lengths_mm, wedge_size: str) -> list[dict]:
    """Generate every figure and return the manifest for report + review loop."""
    out_dir.mkdir(parents=True, exist_ok=True)
    specs = [
        ("chain", fig_chain,
         "One motor step walked through the as-built reduction chain (log scale): "
         "stick 7.67 µm → lip lift 976 nm → tip Z 620 nm (+65 nm lateral)."),
        ("geometry", fig_geometry,
         "As-built lever geometry (WedgeDesign v37), pin frame, to scale in x; "
         "opening exaggerated for legibility."),
        ("budget", fig_budget,
         "As-built budgets: cumulative tip travel vs steps (full stroke), and steps "
         "to cross the piezo handoff zone vs the round-2 leadscrew."),
        ("wedge_sizes", fig_wedge_sizes,
         "APPENDIX — per-step tip Z for every washer size in the kit at three plate "
         "lengths (design-space scenario, leadscrew baseline)."),
        ("length_sweep", fig_length_sweep,
         "APPENDIX — tip Z per step vs plate length under the old layout rules "
         "(design-space scenario, leadscrew baseline)."),
    ]
    manifest = []
    for name, fn, caption in specs:
        p = out_dir / f"{name}.png"
        fn(p, plate_lengths_mm, wedge_size)
        manifest.append({"name": name, "path": p, "caption": caption})
    return manifest

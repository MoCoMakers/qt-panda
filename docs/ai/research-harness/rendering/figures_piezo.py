"""Figures for the piezo-position (lever-arm relocation) investigation.

Same contract as figures_wedge.py: each function takes an output path,
returns it, and generate_all builds the manifest.

The question: the drive (wedge + rack-pinion at the far lip, d_w = 120.15 mm)
stays put; we only slide the piezo/sample junction along the lid toward the
hinge, shrinking the lever r_p.  Because dz_tip = dz_wedge * (r_p / d_w), that
is a pure, free lever reduction — finer steps, at the cost of Z range.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from physics import wedge_lever as wl
from rendering.style import PALETTE, apply_house_style

# Tie-down "roman arch" rails live at x = -16 .. +24 mm (RESUME v33); with the
# pin at x = 35, that is the r_p band the piezo could be reseated into.
ARCH_RP_LO = wl.PIVOT_X_MM - 24.0   # 11 mm  (back rail, very close to the pin)
ARCH_RP_HI = wl.PIVOT_X_MM + 16.0   # 51 mm  (front rail)


def _dztip(r_p: float) -> float:
    return wl.as_built_gearing(lever_mm=r_p).dz_tip_nm


def _zrange_mm(r_p: float) -> float:
    return wl.WEDGE_RISE_MM * (r_p / wl.LIP_ARM_MM)


def fig_precision(path: Path, positions) -> Path:
    """Tip Z per step vs piezo lever r_p — the free-lever precision curve."""
    apply_house_style()
    rp = np.linspace(20, 82, 300)
    dz = np.array([_dztip(r) for r in rp])

    fig, ax = plt.subplots(figsize=(9.4, 5.3))
    # relocation band (over the tie-down arches)
    ax.axvspan(max(20, ARCH_RP_LO), ARCH_RP_HI, color=PALETTE["ideal"], alpha=0.10, lw=0)
    ax.text((max(20, ARCH_RP_LO) + ARCH_RP_HI) / 2, dz.max() * 0.96,
            "reseat band\n(over the arch rails)", ha="center", va="top",
            fontsize=8.5, color=PALETTE["ideal"])

    ax.plot(rp, dz, color=PALETTE["short"], lw=2.4, zorder=3)

    for label, x_mm in positions:
        r = wl.PIVOT_X_MM - x_mm
        y = _dztip(r)
        ab = abs(r - wl.ASBUILT_LEVER_MM) < 1e-6
        ax.plot([r], [y], "o", ms=11 if ab else 8,
                color=PALETTE["accent"] if ab else PALETTE["short"],
                markeredgecolor="white", zorder=5)
        ax.annotate(f"{label}\n$r_p$={r:.0f} mm → {y:.0f} nm",
                    xy=(r, y), xytext=(6, 16 if ab else -30),
                    textcoords="offset points", fontsize=9,
                    color=PALETTE["accent"] if ab else PALETTE["short"],
                    fontweight="bold")

    ax.axhline(wl.BEST_LONGBOARD_NM_PER_STEP, color=PALETTE["muted"], ls=":", lw=1.2)
    ax.text(81, wl.BEST_LONGBOARD_NM_PER_STEP + 6,
            f"best documented longboard ({wl.BEST_LONGBOARD_NM_PER_STEP:g} nm/step)",
            ha="right", va="bottom", fontsize=8, color=PALETTE["muted"])

    ax.annotate("← move piezo toward the hinge (finer steps)",
                xy=(0.30, 0.06), xycoords="axes fraction", fontsize=9.5,
                color=PALETTE["short"], fontweight="bold")
    ax.set_xlabel("piezo lever  $r_p$  (mm, pin → piezo center)")
    ax.set_ylabel("tip Z per motor step (nm) — smaller = finer")
    ax.set_title("Precision is LINEAR in the lever: $Δz_{tip}$ = 976.2 nm × "
                 "$r_p$ / 120.15\n(the existing rack-pinion drive; only the piezo moves)")
    ax.set_xlim(20, 82)
    ax.set_ylim(0, dz.max() * 1.08)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def fig_tradeoff(path: Path, positions) -> Path:
    """Two panels: (A) precision vs range trade; (B) the Abbe cost."""
    apply_house_style()
    rp = np.linspace(20, 82, 300)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.4, 4.7))

    # Panel A — dz_tip (left) and Z range (right), both vs r_p.
    dz = np.array([_dztip(r) for r in rp])
    rng = np.array([_zrange_mm(r) for r in rp])
    l1, = ax1.plot(rp, dz, color=PALETTE["short"], lw=2.2, label="tip Z / step (nm)")
    ax1.set_xlabel("piezo lever  $r_p$  (mm)")
    ax1.set_ylabel("tip Z per step (nm)", color=PALETTE["short"])
    ax1.tick_params(axis="y", labelcolor=PALETTE["short"])
    axr = ax1.twinx()
    l2, = axr.plot(rp, rng, color=PALETTE["long"], lw=2.2, ls="--",
                   label="full Z range (mm)")
    axr.set_ylabel("full tip Z range over the 27.5 mm stroke (mm)", color=PALETTE["long"])
    axr.tick_params(axis="y", labelcolor=PALETTE["long"])
    # as-built marker
    r0 = wl.ASBUILT_LEVER_MM
    ax1.plot([r0], [_dztip(r0)], "o", ms=9, color=PALETTE["accent"],
             markeredgecolor="white", zorder=6)
    ax1.legend(handles=[l1, l2], loc="upper left", fontsize=8.5)
    ax1.set_title("Finer steps cost Z range —\nboth scale linearly with $r_p$")
    ax1.set_xlim(20, 82)

    # Panel B — Abbe: absolute lateral is FIXED; lateral/Z ratio grows.
    ratio = 100.0 * wl.COLLET_STANDOFF_MM / rp
    ax2.plot(rp, ratio, color=PALETTE["accent"], lw=2.2)
    ax2.axhline(100.0 * wl.COLLET_STANDOFF_MM / r0, color=PALETTE["muted"], ls=":", lw=1)
    for label, x_mm in positions:
        r = wl.PIVOT_X_MM - x_mm
        ax2.plot([r], [100 * wl.COLLET_STANDOFF_MM / r], "o", ms=7,
                 color=PALETTE["accent"], markeredgecolor="white", zorder=5)
    ax2.text(81, 100 * wl.COLLET_STANDOFF_MM / r0 + 0.6,
             f"as-built {100*wl.COLLET_STANDOFF_MM/r0:.1f}%", ha="right",
             fontsize=8.5, color=PALETTE["muted"])
    ax2.set_xlabel("piezo lever  $r_p$  (mm)")
    ax2.set_ylabel("lateral walk per unit Z  ($c/r_p$, %)")
    ax2.set_title("The cost: Abbe ratio worsens as 1/$r_p$\n"
                  f"(absolute lateral stays {_dxconst():.0f} nm/step)")
    ax2.set_xlim(20, 82)
    ax2.set_ylim(0, 100 * wl.COLLET_STANDOFF_MM / 20 * 1.05)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def _dxconst() -> float:
    return wl.as_built_gearing().dx_tip_nm


def generate_all(out_dir: Path, positions) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    specs = [
        ("precision", fig_precision,
         "Tip Z per motor step vs the piezo lever r_p: shortening the arm (moving "
         "the piezo toward the hinge) makes every step linearly finer, for free."),
        ("tradeoff", fig_tradeoff,
         "The trade: finer steps cost proportional Z range (both linear in r_p), and "
         "the Abbe lateral/Z ratio grows as 1/r_p while the absolute lateral is fixed."),
    ]
    manifest = []
    for name, fn, caption in specs:
        p = out_dir / f"{name}.png"
        fn(p, positions)
        manifest.append({"name": name, "path": p, "caption": caption})
    return manifest

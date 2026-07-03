"""Matplotlib figures for the gold thermal-vibration investigation."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

import physics.thermal_vibration as tv
from rendering.style import PALETTE, apply_house_style

GOLD = "#C9A227"  # gold fill for the atom schematic


def fig_distribution(out: Path, T: float) -> Path:
    """Position distribution: 1-D component (Gaussian) + 3-D magnitude (Maxwell)."""
    apply_house_style()
    d = tv.gold_at(T)
    s = d.sigma_pm
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(10.4, 4.4))

    # --- 1-D Cartesian component ----------------------------------------
    x = np.linspace(-4 * s, 4 * s, 500)
    p1 = np.exp(-x**2 / (2 * s**2)) / (s * math.sqrt(2 * math.pi))
    axL.plot(x, p1, color=PALETTE["short"])
    axL.fill_between(x, p1, color=PALETTE["short"], alpha=0.15)
    for sign in (-1, 1):
        axL.axvline(sign * s, color=PALETTE["short"], ls=":", lw=1.2, alpha=0.8)
    axL.text(s, p1.max() * 0.5, f"  $\\pm\\sigma$ = {s:.1f} pm",
             color=PALETTE["short"], fontsize=9.5, fontweight="bold", va="center")
    axL.set_title("One axis: Gaussian about the site")
    axL.set_xlabel("displacement along one axis (pm)")
    axL.set_ylabel("probability density")
    axL.set_ylim(0, p1.max() * 1.18)

    # --- 3-D magnitude (Maxwell) ----------------------------------------
    r = np.linspace(0, 4.2 * s, 500)
    p3 = math.sqrt(2 / math.pi) * r**2 / s**3 * np.exp(-r**2 / (2 * s**2))
    axR.plot(r, p3, color=PALETTE["long"])
    axR.fill_between(r, p3, color=PALETTE["long"], alpha=0.15)

    marks = [
        (d.most_probable_pm, PALETTE["muted"], "most probable", "$\\sqrt{2}\\,\\sigma$"),
        (d.mean_mag_pm, PALETTE["accent"], "mean  $\\langle|u|\\rangle$", "$\\sqrt{8/\\pi}\\,\\sigma$"),
        (d.rms_pm, PALETTE["long"], "rms", "$\\sqrt{3}\\,\\sigma$"),
    ]
    ymax = p3.max()
    # Vertical markers on the curve; labels collected in a clean stacked block
    # in the upper-right corner so nothing overlaps the peak.
    for val, col, lbl, form in marks:
        axR.axvline(val, color=col, ls="--", lw=1.4)
    for i, (val, col, lbl, form) in enumerate(marks):
        axR.text(0.97, 0.93 - 0.13 * i, f"{lbl} = {val:.1f} pm  ({form})",
                 transform=axR.transAxes, ha="right", va="top",
                 fontsize=9.5, color=col, fontweight="bold")
    axR.set_title("3-D displacement magnitude $|u|$")
    axR.set_xlabel("distance from lattice site (pm)")
    axR.set_ylabel("probability density")
    axR.set_ylim(0, ymax * 1.18)

    fig.suptitle(f"Where a gold atom sits relative to its lattice site (T = {T:.0f} K)",
                 fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out)
    plt.close(fig)
    return out


def fig_temperature(out: Path, T0: float) -> Path:
    """RMS displacement vs temperature: full Debye vs classical, 0 K to melt."""
    apply_house_style()
    Ts = np.linspace(0, tv.T_MELT_AU * 1.02, 400)
    rms_d = np.array([tv.gold_at(T).rms_pm for T in Ts])
    rms_c = np.array([math.sqrt(tv.msd_classical(T)) * 1e12 for T in Ts])
    zpf = tv.gold_at(0).rms_pm

    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    ax.plot(Ts, rms_d, color=PALETTE["long"], label="full Debye (quantum + zero-point)")
    ax.plot(Ts, rms_c, color=PALETTE["short"], ls="--",
            label="classical equipartition  $\\propto\\sqrt{T}$")
    ax.axhline(zpf, color=PALETTE["muted"], ls=":", lw=1.3)
    ax.text(tv.T_MELT_AU * 0.5, zpf + 0.6,
            f"zero-point floor {zpf:.1f} pm", color=PALETTE["muted"], fontsize=9)

    d0 = tv.gold_at(T0)
    ax.axvline(T0, color=PALETTE["accent"], ls="-.", lw=1.3)
    ax.plot([T0], [d0.rms_pm], "o", color=PALETTE["accent"], ms=8, zorder=5)
    ax.annotate(f"room T = {T0:.0f} K\nrms = {d0.rms_pm:.1f} pm",
                xy=(T0, d0.rms_pm), xytext=(14, -6), textcoords="offset points",
                fontsize=9.5, color=PALETTE["accent"], fontweight="bold")

    dm = tv.gold_at(tv.T_MELT_AU)
    ax.axvline(tv.T_MELT_AU, color=PALETTE["ideal"], ls=":", lw=1.2, alpha=0.7)
    ax.annotate(f"melting point\n{tv.T_MELT_AU:.0f} K · {dm.rms_pm:.0f} pm",
                xy=(tv.T_MELT_AU, dm.rms_pm), xytext=(-118, -2),
                textcoords="offset points", fontsize=8.5, color=PALETTE["ideal"])

    ax.set_xlabel("temperature (K)")
    ax.set_ylabel("3-D RMS displacement (pm)")
    ax.set_title("Thermal amplitude grows as $\\sqrt{T}$ above the Debye temperature")
    ax.set_xlim(0, Ts.max())
    ax.set_ylim(0, rms_d.max() * 1.12)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def fig_scale(out: Path, T: float) -> Path:
    """Atomic-scale schematic: thermal jitter envelope vs lattice spacing."""
    apply_house_style()
    d = tv.gold_at(T)
    a_nn = tv.A_NN_AU * 1e12       # pm
    r_atom = tv.R_ATOM_AU * 1e12   # pm
    rms = d.rms_pm

    fig, ax = plt.subplots(figsize=(7.6, 5.0))

    # Central atom + one neighbour, drawn to scale in pm.
    for cx, alpha, lbl in [(0, 1.0, "atom"), (a_nn, 0.35, "neighbour")]:
        ax.add_patch(plt.Circle((cx, 0), r_atom, facecolor=GOLD, alpha=alpha,
                                 edgecolor="#7A6310", lw=1.5, zorder=2))
    ax.plot([0], [0], "+", color="#333333", ms=10, mew=1.5, zorder=4)

    # Thermal RMS envelope around the central atom (to scale).
    ax.add_patch(plt.Circle((0, 0), rms, facecolor="none", edgecolor=PALETTE["long"],
                            lw=2.0, ls="--", zorder=5))
    ax.annotate(f"thermal RMS\nenvelope\n{rms:.1f} pm",
                xy=(rms * 0.71, rms * 0.71), xytext=(70, 60),
                textcoords="offset points", fontsize=9.5, color=PALETTE["long"],
                fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=PALETTE["long"], lw=1.4))

    # Nearest-neighbour dimension line (derived from density).
    y_dim = -r_atom - 70
    ax.annotate("", xy=(a_nn, y_dim), xytext=(0, y_dim),
                arrowprops=dict(arrowstyle="<->", color="#333333", lw=1.4))
    ax.text(a_nn / 2, y_dim - 18,
            f"nearest-neighbour spacing = {a_nn:.0f} pm\n(from density 19.30 g/cm³)",
            ha="center", va="top", fontsize=9.5)
    for cx in (0, a_nn):
        ax.plot([cx, cx], [-r_atom, y_dim], color="#999999", lw=0.8, ls=":")

    ax.text(0, r_atom + 95,
            f"RMS jitter is {d.lindemann_ratio*100:.1f}% of the spacing\n"
            f"(Lindemann melting criterion: ~10–15%)",
            ha="center", va="bottom", fontsize=10, color=PALETTE["accent"],
            fontweight="bold")

    ax.set_xlim(-r_atom - 60, a_nn + r_atom + 60)
    ax.set_ylim(y_dim - 70, r_atom + 175)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("position (pm)")
    ax.set_yticks([])
    ax.grid(False)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.set_title("A gold atom's thermal jitter vs. its lattice spacing")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def fig_lindemann(out: Path, T0: float) -> Path:
    """Lindemann ratio (rms / nn-spacing) vs temperature, with melt band."""
    apply_house_style()
    Ts = np.linspace(0, tv.T_MELT_AU * 1.02, 400)
    ratio = np.array([tv.gold_at(T).lindemann_ratio for T in Ts]) * 100

    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    ax.axhspan(10, 15, color=PALETTE["long"], alpha=0.12)
    ax.text(40, 12.5, "Lindemann melting band (~10–15%)",
            color=PALETTE["long"], fontsize=9.5, va="center")
    ax.plot(Ts, ratio, color=PALETTE["accent"])

    for T, lbl, col in [(T0, "room T", PALETTE["short"]),
                        (tv.T_MELT_AU, "melt", PALETTE["ideal"])]:
        d = tv.gold_at(T)
        rp = d.lindemann_ratio * 100
        ax.plot([T], [rp], "o", color=col, ms=8, zorder=5)
        ax.annotate(f"{lbl}\n{rp:.1f}%", xy=(T, rp), xytext=(10, -4),
                    textcoords="offset points", fontsize=9.5, color=col,
                    fontweight="bold")

    ax.set_xlabel("temperature (K)")
    ax.set_ylabel("RMS displacement / spacing  (%)")
    ax.set_title("Gold reaches the Lindemann melting threshold right at its melting point")
    ax.set_xlim(0, Ts.max())
    ax.set_ylim(0, 16)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def generate_all(out_dir: Path, T: float) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    specs = [
        ("distribution", fig_distribution,
         "Probability of finding the atom at a given displacement: Gaussian per "
         "axis, Maxwell in 3-D magnitude. Mean, most-probable, and RMS marked."),
        ("temperature", fig_temperature,
         "3-D RMS displacement vs temperature — classical √T law, the quantum "
         "zero-point floor, and the room-temperature operating point."),
        ("scale", fig_scale,
         "The thermal jitter envelope drawn to scale against the gold lattice "
         "spacing derived from its bulk density."),
        ("lindemann", fig_lindemann,
         "RMS displacement as a fraction of nearest-neighbour spacing; gold "
         "crosses the empirical Lindemann melting band exactly at its melting point."),
    ]
    manifest = []
    for name, fn, caption in specs:
        path = out_dir / f"{name}.png"
        fn(path, T)
        manifest.append({"name": name, "path": path, "caption": caption})
    return manifest

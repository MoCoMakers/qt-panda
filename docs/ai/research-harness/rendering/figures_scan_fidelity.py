"""Figures for the scan-speed fidelity investigation.

Same contract as figures_wedge.py / figures_piezo.py: each function takes an
output path (and the resolved configs), returns the path, and generate_all
builds the manifest.

The question: why did tonight's slow legacy SCST frame (69 s) show morphology
that the "30 Hz" (truly 48.8 Hz) continuous scan of the SAME 30 nm region
could not?  These figures ground the candidate mechanisms: preamp RC blur
(speed x time-constant), the samples-per-pixel clamp, and per-pixel SNR.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from physics import scan_bandwidth as sb
from rendering.style import PALETTE, apply_house_style

# semantic colours per configuration (Okabe-Ito roles from the house palette)
CFG_COLORS = [PALETTE["accent"], PALETTE["long"], PALETTE["short"],
              "#CC79A7", PALETTE["ideal"]]


def _cfg_color(i: int) -> str:
    return CFG_COLORS[i % len(CFG_COLORS)]


def fig_blur_vs_linerate(path: Path, configs) -> Path:
    """Preamp blur length vs TRUE line rate for several capacitances."""
    apply_house_style()
    lr = np.logspace(-0.31, 2.0, 300)           # ~0.5 .. 100 Hz
    S = sb.REGION_NM

    fig, ax = plt.subplots(figsize=(9.6, 5.6))
    for c_pf, ls in zip(sb.C_SWEEP_PF, ("-", "-", "--", ":")):
        v = sb.tip_velocity_nm_s(S, lr)
        blur = v * sb.preamp_tau_s(c_pf) * 1e9 / 1e9  # nm (v already nm/s)
        blur = v * sb.preamp_tau_s(c_pf)
        ax.plot(lr, blur, ls=ls, lw=2.0, color=PALETTE["muted"] if c_pf != sb.C_NOMINAL_PF else PALETTE["ideal"],
                label=f"C = {c_pf:g} pF  (f₃dB = {sb.preamp_f3db_hz(c_pf):,.0f} Hz)")

    # pixel-limit guides
    for px, half in ((512, 256), (256, 128)):
        nyq = 2 * S / half
        ax.axhline(nyq, color=PALETTE["short"], ls=":", lw=1.0, alpha=0.6)
        ax.text(0.52, nyq * 1.07, f"2-pixel limit, {px} px/line ({nyq:.2f} nm)",
                fontsize=8, color=PALETTE["short"])

    # configuration markers at C = 1 pF
    for i, cfg in enumerate(configs):
        if cfg.stepped:
            continue
        ax.plot([cfg.true_line_rate_hz], [cfg.blur_nm(sb.C_NOMINAL_PF)], "o",
                ms=10, color=_cfg_color(i), markeredgecolor="white", zorder=6)
        # fastest config sits at the right edge: label it leftward
        rightmost = cfg.true_line_rate_hz > 40
        ax.annotate(cfg.label.replace("continuous ", ""),
                    xy=(cfg.true_line_rate_hz, max(cfg.blur_nm(sb.C_NOMINAL_PF), 2e-3)),
                    xytext=(-8 if rightmost else 6, 12),
                    textcoords="offset points",
                    ha="right" if rightmost else "left",
                    fontsize=8.5, color=_cfg_color(i), fontweight="bold")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("TRUE line rate (Hz) — firmware tick budget, not the request")
    ax.set_ylabel("preamp blur length  L = v·τ  (nm)")
    ax.set_title(f"RC blur vs scan speed over the {S:.0f} nm region\n"
                 "(markers: tonight's configurations at C = 1 pF)")
    ax.legend(fontsize=8.5, loc="upper left")
    ax.set_ylim(1e-3, 30)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def fig_mtf(path: Path, configs) -> Path:
    """MTF vs feature size for each configuration (nominal + worst-case C)."""
    apply_house_style()
    d = np.logspace(-1.3, 1.7, 400)   # 0.05 .. 50 nm

    fig, ax = plt.subplots(figsize=(9.6, 5.6))
    for i, cfg in enumerate(configs):
        if cfg.stepped:
            # settled point sampling: flat response down to the pixel limit
            h = np.where(d >= cfg.nyquist_nm, 1.0, np.nan)
            ax.plot(d, h, lw=2.4, color=_cfg_color(i),
                    label=f"{cfg.label} (settled; pixel-limited)")
            continue
        h1 = np.array([sb.mtf(x, cfg.v_nm_s, sb.C_NOMINAL_PF) for x in d])
        h1 = np.where(d >= cfg.nyquist_nm, h1, np.nan)
        ax.plot(d, h1, lw=2.2, color=_cfg_color(i),
                label=f"{cfg.label} @ 1 pF")
        h10 = np.array([sb.mtf(x, cfg.v_nm_s, 10.0) for x in d])
        h10 = np.where(d >= cfg.nyquist_nm, h10, np.nan)
        ax.plot(d, h10, lw=1.3, ls="--", color=_cfg_color(i), alpha=0.7)

    ax.axhline(0.5, color=PALETTE["muted"], ls=":", lw=1.2)
    ax.text(0.02, 0.53, "MTF = 0.5 (resolvable)", fontsize=8.5,
            color=PALETTE["muted"], transform=ax.get_yaxis_transform())
    ax.set_xscale("log")
    ax.set_xlabel("feature size (nm)")
    ax.set_ylabel("contrast transferred  |H|")
    ax.set_title("What survives the preamp at each speed\n"
                 "(solid: C = 1 pF; dashed: 10 pF; cut at 2-pixel limits)")
    ax.legend(fontsize=8, loc="lower right")
    ax.set_ylim(0, 1.05)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def fig_snr(path: Path, configs) -> Path:
    """Per-pixel SNR vs samples averaged, for a 1 nA feature."""
    apply_house_style()
    spp = np.arange(1, 101)
    snr = np.array([sb.snr_per_pixel(int(s)) for s in spp])

    fig, ax = plt.subplots(figsize=(9.0, 5.2))
    ax.plot(spp, snr, lw=2.2, color=PALETTE["ideal"])
    # short, colour-keyed annotations (full names live in the other figures);
    # stagger the low-spp cluster so labels never collide
    offsets = [(6, 20), (6, -22), (6, 14), (6, -22), (-10, 10)]
    aligns = ["left", "left", "left", "left", "right"]
    for i, cfg in enumerate(configs):
        ax.plot([cfg.spp], [cfg.snr()], "o", ms=10, color=_cfg_color(i),
                markeredgecolor="white", zorder=6)
        ax.annotate(f"spp {cfg.spp} → SNR {cfg.snr():,.0f}",
                    xy=(cfg.spp, cfg.snr()),
                    xytext=offsets[i % len(offsets)],
                    ha=aligns[i % len(aligns)],
                    textcoords="offset points", fontsize=8.5,
                    color=_cfg_color(i), fontweight="bold")
    # colour key
    handles = [plt.Line2D([], [], marker="o", ls="", ms=8, color=_cfg_color(i),
                          markeredgecolor="white", label=cfg.label)
               for i, cfg in enumerate(configs)]
    ax.legend(handles=handles, fontsize=7.6, loc="upper left")
    ax.set_xscale("log")
    ax.set_xlabel("samples averaged per pixel (spp)")
    ax.set_ylabel("per-pixel SNR for a 1 nA feature")
    ax.set_title("Averaging buys √spp — 15.6 pA rms floor, 3.125 pA/LSB\n"
                 "(even spp = 1 gives SNR ≈ 64 at 1 nA: noise is NOT tonight's killer)")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def fig_step_edge(path: Path, configs) -> Path:
    """Synthetic step edge dragged past the preamp at each config's speed."""
    apply_house_style()
    x = np.linspace(-2.0, 10.0, 1200)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 4.8), sharey=True)
    for ax, c_pf in ((ax1, sb.C_NOMINAL_PF), (ax2, 10.0)):
        ax.plot(x, np.where(x > 0, 1.0, 0.0), color=PALETTE["muted"],
                lw=1.4, ls=":", label="true edge")
        for i, cfg in enumerate(configs):
            if cfg.stepped:
                # settled sampling reproduces the edge to within a pixel
                px = cfg.pixel_nm
                xs = np.floor(x / px) * px + px / 2
                ax.plot(x, np.where(xs > 0, 1.0, 0.0), lw=1.6,
                        color=_cfg_color(i), alpha=0.9,
                        label=f"{cfg.label}")
                continue
            y = sb.step_edge_response(x, cfg.v_nm_s, c_pf)
            ax.plot(x, y, lw=2.0, color=_cfg_color(i),
                    label=f"{cfg.label} (blur {cfg.blur_nm(c_pf):.2f} nm)")
        ax.set_xlabel("position along the line (nm)")
        ax.set_title(f"C = {c_pf:g} pF   (f₃dB = {sb.preamp_f3db_hz(c_pf):,.0f} Hz)")
        ax.set_xlim(-2, 10)
    ax1.set_ylabel("normalised current response")
    ax1.legend(fontsize=7.6, loc="lower right")
    fig.suptitle("A 1-step edge dragged under the tip: what each configuration records",
                 fontweight="bold")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def fig_speed_limit(path: Path, configs) -> Path:
    """Max line rate that still resolves a given feature, vs preamp C."""
    apply_house_style()
    c = np.linspace(0.3, 10.0, 300)

    fig, ax = plt.subplots(figsize=(9.4, 5.4))
    for d_nm, color in ((1.0, PALETTE["short"]), (3.0, PALETTE["accent"]),
                        (10.0, PALETTE["long"])):
        lr = np.array([sb.max_line_rate_hz(d_nm, sb.REGION_NM, cc) for cc in c])
        ax.plot(c, lr, lw=2.2, color=color, label=f"resolve {d_nm:g} nm features")

    for i, cfg in enumerate(configs):
        if cfg.stepped:
            continue
        ax.axhline(cfg.true_line_rate_hz, color=_cfg_color(i), ls="--", lw=1.1,
                   alpha=0.8)
        ax.text(9.9, cfg.true_line_rate_hz * 1.12,
                cfg.label.replace("continuous ", ""), ha="right", fontsize=7.8,
                color=_cfg_color(i), fontweight="bold")

    ax.set_yscale("log")
    ax.set_xlabel("preamp capacitance C (pF)  — measure it from a RAWD FFT roll-off")
    ax.set_ylabel(f"max TRUE line rate (Hz) over the {sb.REGION_NM:.0f} nm region")
    ax.set_title("Speed limit for MTF > 0.5, by feature size and preamp C\n"
                 "(dashed: tonight's configurations)")
    ax.legend(fontsize=9, loc="upper right")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def generate_all(out_dir: Path, configs) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    specs = [
        ("blur_vs_linerate", fig_blur_vs_linerate,
         "Preamp RC blur length vs true line rate over the shared 30 nm region, "
         "for stray capacitance 0.3-10 pF, with tonight's configurations marked "
         "at the nominal 1 pF."),
        ("mtf", fig_mtf,
         "Contrast surviving the preamp vs feature size for each configuration "
         "(solid C = 1 pF, dashed 10 pF); the legacy stepped scan is settled and "
         "pixel-limited."),
        ("snr", fig_snr,
         "Per-pixel SNR for a 1 nA feature vs samples averaged: even the "
         "clamped spp = 1 case keeps SNR ~ 64, so noise alone cannot explain "
         "the missing morphology."),
        ("step_edge", fig_step_edge,
         "A unit step edge as each configuration records it, at nominal and "
         "worst-case capacitance: at 1 pF all continuous configs preserve the "
         "edge at the 30 nm scale; at 10 pF the 48.8 Hz scan smears it by ~3 nm."),
        ("speed_limit", fig_speed_limit,
         "The governing speed limit: fastest true line rate that resolves 1, 3 "
         "and 10 nm features vs preamp capacitance, with tonight's line rates "
         "overlaid."),
    ]
    manifest = []
    for name, fn, caption in specs:
        p = out_dir / f"{name}.png"
        fn(p, configs)
        manifest.append({"name": name, "path": p, "caption": caption})
    return manifest

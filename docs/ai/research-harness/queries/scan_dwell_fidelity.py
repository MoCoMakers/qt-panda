"""Query: why did the slow legacy scan show morphology the 30 Hz scan couldn't?

Reference question (bench, 2026-07-15): the legacy SCST "Scan" (69 s per
256x256 frame) produced a clearly-structured current map of a ~30 nm region,
while the continuous scan of the SAME region ("30 Hz" requested -> 48.8 Hz
true, samples/pixel clamped to 1) could not replicate the morphology.  The
session journal proves both scans used the identical footprint (SCSZ 39322,
XOFS/YOFS 0 == the box 13107..52429).  Quantify the physics: preamp RC
bandwidth vs tip speed, the firmware samples-per-pixel clamp, per-pixel SNR
— and say which mechanism actually bit tonight.

Physics.  The 100 MOhm transimpedance preamp is a first-order low-pass
(tau = RC) applied BEFORE the ADC — averaging cannot recover what it removes.
A tip moving at v smears the current record over L = v*tau and attenuates a
feature of size d by |H| = 1/sqrt(1+(2 pi v tau / 2d)^2).  The firmware's
tick budget (40 us ISR) sets the TRUE line rate from samples/pixel — the
"30 Hz" request truncated spp to 1 and ran 48.8 Hz.  The model puts numbers
on all four of tonight's candidate configurations and, importantly, on the
honest verdict: at C ~ 1 pF the RC blur at 30 nm scale is sub-nm, so the
missing morphology is NOT primarily preamp bandwidth unless C is ~5-10 pF
(cabled homebrew territory) — it is the measurement mode (fixed-Z current
map vs per-pixel settled/servoed sampling) plus display channel.  The RC
limit becomes decisive for sub-nm/atomic features or larger scans.
"""

from __future__ import annotations

from pathlib import Path

from models import Investigation
from physics import scan_bandwidth as sb
from rendering import figures_scan_fidelity

SLUG = "scan-dwell-fidelity"


def default_configs():
    """Tonight's four configurations over the shared 30 nm region."""
    return [
        sb.legacy_config(samples=2,
                         label="legacy SCST 256px, 2 samples (69 s frame)"),
        sb.continuous_config(pixels_per_line=512, requested_line_rate_hz=30.0,
                             sppx=0,
                             label="continuous 512px, req 30 Hz -> spp 1 (48.8 Hz)"),
        sb.continuous_config(pixels_per_line=256, requested_line_rate_hz=5.0,
                             sppx=5,
                             label="continuous 256px, SPPX 5 (19.5 Hz)"),
        sb.continuous_config(pixels_per_line=512, requested_line_rate_hz=1.0,
                             sppx=20,
                             label="continuous 512px, SPPX 20 (2.44 Hz)"),
        sb.continuous_config(pixels_per_line=512, requested_line_rate_hz=1.0,
                             sppx=0,
                             label="continuous 512px, req 1 Hz -> spp 48 (1.02 Hz)"),
    ]


def _row(cfg: sb.ScanConfig) -> dict:
    return {
        "label": cfg.label,
        "true_lr": cfg.true_line_rate_hz,
        "spp": cfg.spp,
        "dwell_ms": cfg.dwell_s * 1e3,
        "v": cfg.v_nm_s,
        "blur": cfg.blur_nm(sb.C_NOMINAL_PF),
        "blur10": cfg.blur_nm(10.0) if not cfg.stepped else 0.0,
        "dmin": cfg.d_min_nm(sb.C_NOMINAL_PF),
        "dmin10": (max(sb.d_min_mtf50_nm(cfg.v_nm_s, 10.0), cfg.nyquist_nm)
                   if not cfg.stepped else cfg.nyquist_nm),
        "snr": cfg.snr(),
        "frame_s": cfg.frame_time_s,
    }


def _table(rows) -> str:
    head = ("configuration                                true-Hz  spp  dwell   "
            "v nm/s   blur@1pF  d_min@1pF  d_min@10pF  SNR(1nA)  frame")
    lines = [head, "-" * len(head)]
    for r in rows:
        lines.append(
            f"{r['label']:<44} {r['true_lr']:6.2f}  {r['spp']:3d}  "
            f"{r['dwell_ms']:5.2f}ms {r['v']:7.1f}   {r['blur']:6.3f} nm  "
            f"{r['dmin']:6.2f} nm   {r['dmin10']:6.2f} nm   {r['snr']:6.0f}   "
            f"{r['frame_s']:5.1f} s")
    lines.append("-" * len(head))
    lines.append(f"(region {sb.REGION_NM:.1f} nm square = SCSZ {sb.REGION_LSB}; "
                 f"R = 100 MOhm; nominal C = {sb.C_NOMINAL_PF:g} pF -> "
                 f"f3dB = {sb.preamp_f3db_hz():,.0f} Hz, tau = "
                 f"{sb.preamp_tau_s()*1e6:.0f} us; ADC floor 5 LSB rms)")
    return "\n".join(lines)


def run(out_dir: Path, scan_size_nm: float | None = None) -> Investigation:
    configs = default_configs()
    if scan_size_nm:
        configs = [
            sb.legacy_config(scan_size_nm=scan_size_nm, samples=2),
            sb.continuous_config(scan_size_nm=scan_size_nm, pixels_per_line=512,
                                 requested_line_rate_hz=30.0),
            sb.continuous_config(scan_size_nm=scan_size_nm, pixels_per_line=256,
                                 requested_line_rate_hz=5.0, sppx=5),
            sb.continuous_config(scan_size_nm=scan_size_nm, pixels_per_line=512,
                                 requested_line_rate_hz=1.0, sppx=20),
            sb.continuous_config(scan_size_nm=scan_size_nm, pixels_per_line=512,
                                 requested_line_rate_hz=1.0),
        ]
    rows = [_row(c) for c in configs]
    fast = rows[1]      # tonight's failing config
    slow = rows[4]      # the 1 Hz auto recipe

    fig_dir = Path(out_dir) / "figures"
    manifest = figures_scan_fidelity.generate_all(fig_dir, configs)

    summary = (
        f"<b>The dwell-time gap is real and huge — the legacy scan spent "
        f"{sb.LEGACY_DWELL_S*1e3:.2f}&nbsp;ms settling on every pixel while the "
        f"&ldquo;30&nbsp;Hz&rdquo; continuous scan (truly {fast['true_lr']:.1f}&nbsp;Hz "
        f"after the samples-per-pixel clamp) spent 0.04&nbsp;ms — but the model "
        f"returns a sharper verdict than the bench intuition.</b> At the nominal "
        f"C&nbsp;=&nbsp;1&nbsp;pF (f<sub>3dB</sub>&nbsp;&asymp;&nbsp;1.6&nbsp;kHz) the "
        f"preamp blur at {fast['true_lr']:.1f}&nbsp;Hz over a 30&nbsp;nm region is only "
        f"{fast['blur']:.2f}&nbsp;nm and the MTF&gt;0.5 limit is {fast['dmin']:.2f}&nbsp;nm "
        f"— sub-nm, so RC filtering alone does <i>not</i> erase 3&ndash;10&nbsp;nm "
        f"morphology at this scan size <i>unless</i> the real capacitance is "
        f"5&ndash;10&nbsp;pF (entirely plausible for a cabled homebrew preamp: at "
        f"10&nbsp;pF the blur grows to {fast['blur10']:.1f}&nbsp;nm and the resolvable "
        f"limit to {fast['dmin10']:.1f}&nbsp;nm — that WOULD wipe the image). The "
        f"decisive next measurement is C itself, readable for free from the 25&nbsp;kHz "
        f"RAWD capture&rsquo;s spectral roll-off. Meanwhile the guaranteed-honest "
        f"replication recipe is the slow one: LRAT 1&nbsp;Hz auto (spp&nbsp;48) matches "
        f"the legacy dwell within 2&times; ({slow['dwell_ms']:.2f} vs "
        f"{sb.LEGACY_DWELL_S*1e3:.2f}&nbsp;ms), keeps blur "
        f"&le;&nbsp;{slow['blur10']:.2f}&nbsp;nm even at worst-case C, and lifts "
        f"per-pixel SNR to {slow['snr']:.0f}."
    )

    findings = [
        f"<b>The samples-per-pixel clamp silently tripled the requested speed.</b> "
        f"At 30&nbsp;Hz &times; 512&nbsp;px the derived spp is 1.63, truncated to 1, so "
        f"the firmware ran {fast['true_lr']:.1f}&nbsp;Hz — 63% faster than asked, with "
        f"zero averaging. Every continuous-scan comparison tonight was made at a speed "
        f"nobody chose. (FW&nbsp;5.2&rsquo;s SPPX override is the fix.)",
        f"<b>At nominal C&nbsp;=&nbsp;1&nbsp;pF, preamp blur does NOT explain tonight.</b> "
        f"Blur at {fast['true_lr']:.1f}&nbsp;Hz is {fast['blur']:.2f}&nbsp;nm and the "
        f"MTF&gt;0.5 feature limit {fast['dmin']:.2f}&nbsp;nm — an honest correction to "
        f"the bench hypothesis: 3&nbsp;nm features survive a 1&nbsp;pF preamp at 48.8&nbsp;Hz "
        f"over 30&nbsp;nm.",
        f"<b>But at C&nbsp;=&nbsp;10&nbsp;pF (160&nbsp;Hz preamp) the hypothesis comes back.</b> "
        f"Blur {fast['blur10']:.1f}&nbsp;nm, resolvable limit {fast['dmin10']:.1f}&nbsp;nm at "
        f"{fast['true_lr']:.1f}&nbsp;Hz — exactly the &ldquo;morphology low-pass-filtered "
        f"before the ADC&rdquo; failure. A cabled, unbuffered 100&nbsp;MOhm stage can "
        f"easily sit there. <b>Measure it:</b> the 25&nbsp;kHz raw capture&rsquo;s noise "
        f"spectrum roll-off gives f<sub>3dB</sub> directly — one bench minute settles "
        f"which regime the rig is in.",
        f"<b>Noise is not the culprit either.</b> Even single-sample pixels keep SNR "
        f"&asymp;&nbsp;{fast['snr']:.0f} on a 1&nbsp;nA feature (15.6&nbsp;pA rms floor); "
        f"the legacy scan&rsquo;s 2-sample average is only &radic;2 better. Averaging "
        f"buys comfort, not the missing image.",
        "<b>What certainly differed: measurement mode and channel.</b> The legacy scan "
        "settles (or Z-servos, when constant-current is latched) on each pixel and its "
        "image is the direct current map; the continuous constant-height pass at a "
        "fixed Z through 30 nm of relief spends much of the line railed (contact) or "
        "out of range (open), and its morphology lives in the Err panel, not the flat "
        "Z panel. Mode + channel choice can hide structure that both engines record.",
        f"<b>The replication recipe (guaranteed regime-independent):</b> LRAT 1&nbsp;Hz "
        f"auto → spp&nbsp;48, dwell {slow['dwell_ms']:.2f}&nbsp;ms ≈ legacy&rsquo;s "
        f"{sb.LEGACY_DWELL_S*1e3:.2f}&nbsp;ms, blur ≤ {slow['blur10']:.2f}&nbsp;nm even at "
        f"10&nbsp;pF, SNR {slow['snr']:.0f}, frame {slow['frame_s']:.0f}&nbsp;s — the "
        f"legacy scan&rsquo;s physics on the streaming engine (recorded, replayable). "
        f"SPPX&nbsp;20 at 512&nbsp;px (true 2.44&nbsp;Hz) is the 4&times;-faster compromise "
        f"that still clears worst-case C by a wide margin.",
        "<b>Note on SPPX arithmetic:</b> once SPPX pins spp, the TRUE line rate is "
        "1e6/(40·px·spp) regardless of LRAT — e.g. SPPX 20 @ 512 px is 2.44 Hz even "
        "if 1 Hz is requested; SPPX 5 @ 256 px runs 19.5 Hz. Choose spp, get the rate.",
    ]

    equations = [
        ("f<sub>3dB</sub> = 1 / (2&pi;RC), &nbsp; &tau; = RC "
         f"&rarr; {sb.preamp_f3db_hz():,.0f} Hz / {sb.preamp_tau_s()*1e6:.0f} µs at 1 pF",
         "The transimpedance preamp is a first-order low-pass BEFORE the ADC."),
        ("v = 2 · S · f<sub>line</sub> &nbsp;&nbsp; L<sub>blur</sub> = v · &tau;",
         "Tip speed over scan size S (trace+retrace) sets the spatial smear."),
        ("|H(d)| = 1 / &radic;(1 + (2&pi; v&tau; / 2d)²) ; "
         "d<sub>min</sub> = &pi;v&tau;/&radic;3 ≈ 1.814 v&tau;",
         "Contrast surviving for a feature of size d; MTF>0.5 resolvable limit."),
        ("spp = trunc(10⁶ / (f<sub>req</sub>·40·px)) clamp[1,4000] ; "
         "f<sub>true</sub> = 10⁶ / (40·px·spp)",
         "Firmware tick budget: the clamp is the 30→48.8 Hz effect; SPPX pins spp."),
        ("SNR = (I/3.125 pA) · &radic;spp / 5",
         "Per-pixel SNR on the 5-LSB rms floor; averaging buys √spp."),
    ]

    assumptions = [
        "Preamp modeled as an ideal first-order transimpedance low-pass with R = 100 "
        "MOhm; C is the union of feedback and stray capacitance and is THE "
        "unmeasured parameter (nominal 1 pF, sweeps to 10 pF). FLAG: measure f3dB "
        "from a RAWD 25 kHz capture's spectral roll-off before trusting either regime.",
        "Legacy SCST timing from tonight's measurement: 69 s per 256x256 frame -> "
        "1.05 ms/pixel including settle + 2 samples; treated as fully settled "
        "(residual exp(-dwell/tau) < 3e-5 at 1 pF).",
        "Continuous-scan geometry: pixels_per_line spans trace+retrace, so the image "
        "has px/2 pixels across the scan width; frame = px lines (square).",
        "Region 30.0 nm from tonight's calibration (SCSZ 13107 = 10.00 nm); all "
        "speed numbers scale linearly with scan size.",
        "ADC floor 5 LSB rms measured on the quiet bench (lid on); 1/f, bias and "
        "vibration noise excluded — SNR figures are ceilings.",
        "Z dynamics excluded on purpose: constant-height railing/out-of-range and "
        "feedback tracking are mode effects the bandwidth model deliberately "
        "isolates away; they are flagged qualitatively in the findings.",
    ]

    return Investigation(
        slug=SLUG,
        title="Scan Speed vs Fidelity — Why the 69 s Scan Saw What 48.8 Hz Didn't",
        question=("The slow legacy SCST frame (69 s, 256², 2 samples) showed clear "
                  "~30 nm-scale morphology; the continuous scan of the SAME region "
                  "('30 Hz' → truly 48.8 Hz, spp clamped to 1) did not. How much of "
                  "that is preamp bandwidth, dwell time, and noise — and what "
                  "settings make the continuous engine replicate the legacy image?"),
        params={
            "region": f"{sb.REGION_NM:.1f} nm square (SCSZ {sb.REGION_LSB}, journal-proven shared)",
            "preamp": f"R = 100 MOhm, C nominal {sb.C_NOMINAL_PF:g} pF (sweep 0.3–10)",
            "firmware": "FW 5.2: 40 µs ISR tick; spp derived-and-clamped, SPPX override",
            "legacy timing": f"{sb.LEGACY_FRAME_S:.0f} s / 256² = {sb.LEGACY_DWELL_S*1e3:.2f} ms/px",
            "failing config": f"req 30 Hz → spp 1 → {fast['true_lr']:.1f} Hz true",
            "recipe": f"LRAT 1 Hz auto → spp 48 → {slow['dwell_ms']:.2f} ms dwell, frame {slow['frame_s']:.0f} s",
            "engine": "NumPy closed form + Matplotlib",
        },
        summary=summary,
        findings=findings,
        equations=equations,
        assumptions=assumptions,
        table_text=_table(rows),
        ascii_blocks=[("Configuration comparison over the shared 30 nm region",
                       _table(rows))],
        figures=manifest,
        references=[
            "physics/scan_bandwidth.py: first-order transimpedance model, firmware "
            "spp/true-line-rate rules (mirrors stm_firmware.hpp updateStepSizes), "
            "SNR and step-edge response.",
            "Bench journal 2026-07-15 (logs/session_*.jsonl): SCST 13107 52429 256 "
            "... at 02:02:42→02:03:51 (69 s frame); SCSZ 39322 XOFS 0 YOFS 0 RUN at "
            "02:09:07 — same-region proof.",
            "dans-software-port/teensy/arduinosrc/main/stm_firmware.hpp: "
            "updateStepSizes() spp truncation + clamp; SPPX override (FW 5.2).",
            "Raw 25 kHz RAWD captures: the proposed f3dB measurement (noise "
            "spectrum roll-off) to pin down C.",
        ],
    )

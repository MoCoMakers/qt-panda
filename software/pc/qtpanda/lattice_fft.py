"""lattice_fft — Tier-3 analysis: is the atomic lattice in this recording?

Part of the graduation-experiment ladder (2026-07-31): median-stack EVERY
complete sweep of a .frames recording (hundreds, not the live view's 10),
2-D FFT the stack, and look for the hexagonal spot pattern of Au(111).
If found, the measured spot spacing against the nominal nm/px IS the
absolute XY calibration (the lattice is the ruler: a = 0.288 nm).

Offline and read-only: runs on the day folder's verbatim recordings, so
it can be re-run days later or mid-session from the GUI button (which
launches it as a subprocess — the GUI never blocks).

    python lattice_fft.py <scan.frames> <scan_size_nm>

Writes <base>_lattice.png (stack + annotated FFT) and
<base>_lattice.json (peaks, spacing, calibration ratio) next to the
recording, then prints the JSON to stdout.
"""
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "replay"))
import sweep_index                                     # noqa: E402

AU_LATTICE_NM = 0.288      # Au(111) nearest-neighbor spacing
DC_EXCLUDE = 3             # FFT bins around DC to ignore
MAX_PEAKS = 12


def median_stack(frames_path):
    """(stack, n_sweeps, width, channel) — median of ALL full sweeps.

    Uses the z channel when the CC loop wrote it (nonzero variance),
    else the error/current channel.  Folds at the recording's own
    geometry (record pixel count), immune to session-start settings."""
    recs = sweep_index.load_frames(frames_path)
    if not recs:
        raise SystemExit("empty frames file")
    # Dominant (modal) geometry, not the first record's: recordings often
    # change pixels/line mid-run, and keying on record 0 discarded the era
    # the operator actually cared about (audit 2026-07-31).
    widths = {}
    for r in recs:
        k = len(r[2]) // 2
        widths[k] = widths.get(k, 0) + 1
    w = max(widths, key=widths.get)
    recs = [r for r in recs if len(r[2]) // 2 == w]
    idx = sweep_index.build_index(frames_path, image_height=w, records=recs)
    full = [s for s in idx["sweeps"] if not s["partial"]]
    if len(full) < 3:
        raise SystemExit(f"only {len(full)} full sweeps — need >= 3")
    for chan in ("z_trace", "e_trace"):
        imgs = [np.asarray(sweep_index.sweep_image(recs, s, w, w, chan),
                           float) for s in full]
        imgs = [np.nan_to_num(a, nan=np.nanmedian(a)) for a in imgs]
        if np.std(imgs[0]) > 1e-9:
            return np.median(np.stack(imgs), axis=0), len(full), w, chan
    raise SystemExit("both channels are flat — nothing to analyze")


def row_align(img):
    """Median-of-diffs row alignment (display-style, offsets only)."""
    d = np.median(np.diff(img, axis=0), axis=1)
    off = np.concatenate([[0.0], np.cumsum(d)])
    return img - off[:, None]


def fft_peaks(img):
    """(power, peaks) — Hann-windowed |FFT|^2 and its top local maxima
    outside the DC exclusion, as (fy, fx, power) in cycles/px."""
    h, wid = img.shape
    win = np.outer(np.hanning(h), np.hanning(wid))
    F = np.fft.fftshift(np.abs(np.fft.fft2((img - img.mean()) * win)) ** 2)
    cy, cx = h // 2, wid // 2
    F[cy - DC_EXCLUDE:cy + DC_EXCLUDE + 1,
      cx - DC_EXCLUDE:cx + DC_EXCLUDE + 1] = 0
    peaks = []
    Fc = F.copy()
    for _ in range(MAX_PEAKS):
        iy, ix = np.unravel_index(np.argmax(Fc), Fc.shape)
        p = Fc[iy, ix]
        if p <= 0:
            break
        peaks.append(((iy - cy) / h, (ix - cx) / wid, float(p)))
        Fc[max(0, iy - 2):iy + 3, max(0, ix - 2):ix + 3] = 0   # suppress
    return F, peaks


def analyze(frames_path, scan_size_nm):
    stack, n, w, chan = median_stack(frames_path)
    aligned = row_align(stack)
    F, peaks = fft_peaks(aligned)
    nm_px = scan_size_nm / w
    floor = float(np.median(F[F > 0])) if (F > 0).any() else 1.0
    out = []
    for fy, fx, p in peaks:
        r = float(np.hypot(fy, fx))            # cycles/px
        if r <= 0:
            continue
        out.append({
            "fy_cpp": round(fy, 5), "fx_cpp": round(fx, 5),
            "spacing_nm": round(nm_px / r, 4),
            "snr": round(p / floor, 1),
        })
    # Hexagon test: >= 4 of the top 6 peaks sharing one radius (+-15%)
    # AND angular diversity — a lattice ring has spots at distinct
    # angles; collinear +-pairs are scan-axis banding (temporal tones),
    # which false-positived on the first bench run (2026-07-31: the
    # 90 Hz tone painted 0.105 nm stripes and passed a radius-only test).
    hex_found, hex_spacing = False, None
    if len(out) >= 4:
        cand = out[:6]
        med = float(np.median([p["spacing_nm"] for p in cand]))
        ring = [p for p in cand
                if abs(p["spacing_nm"] - med) / med < 0.15]
        if len(ring) >= 4:
            angles = [np.arctan2(p["fy_cpp"], p["fx_cpp"]) % np.pi
                      for p in ring]
            distinct = []
            for a in angles:
                if all(abs(a - d) > np.radians(25)
                       and abs(abs(a - d) - np.pi) > np.radians(25)
                       for d in distinct):
                    distinct.append(a)
            if len(distinct) >= 2:
                hex_found = True
                hex_spacing = float(np.mean([p["spacing_nm"] for p in ring]))
    result = {
        "frames": os.path.basename(frames_path),
        "channel": chan, "n_sweeps": n, "width_px": w,
        "scan_size_nm_nominal": scan_size_nm,
        "nm_per_px_nominal": round(nm_px, 5),
        "peaks": out[:8],
        "ring_found": hex_found,
        "ring_spacing_nm": round(hex_spacing, 4) if hex_spacing else None,
        # If the ring is the Au lattice, this factor corrects the XY cal:
        # true_nm = nominal_nm * (AU_LATTICE_NM / measured_spacing)
        "xy_cal_factor_if_au_lattice": (
            round(AU_LATTICE_NM / hex_spacing, 4) if hex_spacing else None),
    }
    return result, aligned, F, out


def save_figure(base, aligned, F, peaks, result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 5.2))
    a1.imshow(aligned, cmap="viridis", aspect="equal")
    a1.set_title(f"median of {result['n_sweeps']} sweeps "
                 f"({result['channel']})")
    a2.imshow(np.log10(F + 1), cmap="magma", aspect="equal")
    h, wid = aligned.shape
    for p in peaks[:8]:
        a2.plot(p["fx_cpp"] * wid + wid // 2, p["fy_cpp"] * h + h // 2,
                "o", mfc="none", mec="cyan", ms=12)
    ring = (f"ring @ {result['ring_spacing_nm']} nm"
            if result["ring_found"] else "no hexagonal ring")
    a2.set_title(f"log |FFT|²  —  {ring}")
    fig.tight_layout()
    fig.savefig(base + "_lattice.png", dpi=110)
    plt.close(fig)


def main():
    frames_path = sys.argv[1]
    scan_size_nm = float(sys.argv[2])
    result, aligned, F, peaks = analyze(frames_path, scan_size_nm)
    base = frames_path[:-len(".frames")]
    save_figure(base, aligned, F, result["peaks"], result)
    with open(base + "_lattice.json", "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

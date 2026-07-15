"""raw_scan_reconstruct — ground-truth spatial reconstruction from RAWD.

The strict-timing instrument (operator requirement 2026-07-15): every 40 us
ISR tick has a deterministic commanded X position (triangle sweep, spp
samples per pixel, px pixels per line covering trace+retrace).  Given a
RAWD capture taken DURING a continuous scan, this maps each raw sample to
its line phase, rebuilds pixels independently of the firmware's binning,
and answers, from first principles:

  1. alignment  — the tick offset that best matches the logged 'L' frames
                  (verifies the firmware's pixel binning is where it thinks);
  2. topology   — trace vs reversed-retrace correlation at 40 us resolution
                  (real surface signal must correlate; pure junction noise
                  cannot), plus the best lag = measured system delay
                  (preamp RC + piezo response) in samples and nm.

Usage:
    python raw_scan_reconstruct.py <capture.raw> <scan.frames> <spp> <px>
"""
import sys

import numpy as np

import frame_logger
import raw_logger


def bin_raw(err_ticks, spp, px, offset):
    """Bin raw per-tick err into (n_lines, px) pixels at a given tick offset."""
    e = err_ticks[offset:]
    n_pix = len(e) // spp
    pix = e[:n_pix * spp].reshape(n_pix, spp).mean(axis=1)
    n_lines = len(pix) // px
    return pix[:n_lines * px].reshape(n_lines, px)


def find_alignment(raw_lines_fn, frame_lines, spp, px):
    """Scan tick offsets for the best match to the logged frames' first
    usable line; returns (offset, corr)."""
    target = None
    for e in frame_lines:
        a = np.asarray(e, dtype=np.float64)
        if a.std() > 1:
            target = a
            break
    if target is None:
        return 0, 0.0
    best = (0, -2.0)
    for o in range(0, spp * px, max(1, spp // 4)):
        img = raw_lines_fn(o)
        if img.shape[0] < 2:
            continue
        # compare against every raw line; take the best single match
        c = max(np.corrcoef(target, row)[0, 1]
                for row in img[:min(len(img), 400)]
                if row.std() > 1)
        if c > best[1]:
            best = (o, c)
    return best


def spatial_verdict(img, spp):
    half = img.shape[1] // 2
    tr = img[:, :half]
    rt = img[:, half:][:, ::-1]
    cors, lags = [], []
    for a, b in zip(tr, rt):
        if a.std() < 1 or b.std() < 1:
            continue
        cors.append(np.corrcoef(a, b)[0, 1])
        c = [np.corrcoef(a[20:-20], np.roll(b, k)[20:-20])[0, 1]
             for k in range(-15, 16)]
        lags.append(int(np.argmax(c)) - 15)
    return (np.median(cors) if cors else float('nan'),
            np.median(lags) if lags else float('nan'),
            len(cors))


def main(raw_path, frames_path, spp, px):
    d = raw_logger.to_arrays(raw_path)
    err = d["err"].astype(np.float64)
    seqs = d["block_seq"].astype(np.int64)
    gaps = int((np.diff(seqs) - 1).clip(0).sum()) if len(seqs) > 1 else 0
    print(f"raw samples: {len(err)}  fw_dropped: {d['fw_dropped_samples']}  "
          f"seq_gap_blocks: {gaps}")
    frame_lines = [e for (_t, _l, _z, e) in frame_logger.read_frames(frames_path)]
    print(f"logged frame lines: {len(frame_lines)}")

    offset, corr = find_alignment(lambda o: bin_raw(err, spp, px, o),
                                  frame_lines, spp, px)
    print(f"alignment: tick offset {offset} of {spp*px}  "
          f"(match r={corr:+.3f}; > +0.9 = firmware binning verified)")

    img = bin_raw(err, spp, px, offset)
    med_r, med_lag, n = spatial_verdict(img, spp)
    print(f"ground-truth topology: trace vs retrace median r = {med_r:+.3f} "
          f"over {n} lines")
    print(f"system lag (trace/retrace half-shift): {med_lag:+.1f} px "
          f"= {med_lag * spp * 40:.0f} us" if not np.isnan(med_lag) else "")
    if med_r > 0.5:
        print("VERDICT: real spatial signal present — continuous pipeline "
              "carries topology; any display issue is downstream.")
    elif med_r > 0.15:
        print("VERDICT: weak spatial component + heavy temporal noise.")
    else:
        print("VERDICT: no spatial signal in the junction current itself — "
              "the scan engine is not the limiter; the junction is.")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))

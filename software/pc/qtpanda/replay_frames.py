"""replay_frames — faithful replay of a logged continuous-scan run (roadmap L2).

Two modes over a .frames file written by frame_logger:

  * offline (default): rebuild the four raster arrays with EXACTLY the same
    mapping LiveRaster.update_line uses (row = line % H; trace = first half;
    retrace = second half reversed) and write normalized PNGs + a .npz of the
    raw float32 arrays.

  * --live: open the real LiveRaster widget and feed it the logged frames at
    the recorded pace (scaled by --speed) — pixel-identical to what was on
    screen during the run, because it IS the same widget fed the same data.

Usage:
    python replay_frames.py scans/scan_170.....frames [--png] [--live]
                            [--speed 10] [--height 256]
"""
import argparse
import json
import os

import numpy as np

import frame_logger


def rebuild_images(frames_path, image_height=256):
    """Replay all frames through the LiveRaster mapping; returns dict of
    float32 arrays (z_trace, z_retrace, e_trace, e_retrace) plus stats."""
    z_t = z_r = e_t = e_r = None
    half = None
    n = 0
    t0 = t1 = None
    parity = False
    last_raw_row = -1
    for t, line, z, e in frame_logger.read_frames(frames_path):
        if half is None:
            half = len(z) // 2
            shape = (image_height, half)
            z_t = np.zeros(shape, np.float32)
            z_r = np.zeros(shape, np.float32)
            e_t = np.zeros(shape, np.float32)
            e_r = np.zeros(shape, np.float32)
        if len(z) < 2 * half:
            continue                       # same skip rule as LiveRaster
        # Y FOLD, matching LiveRaster: one line-counter cycle (0..2H-1) is a
        # full Y up+down triangle; descending half mirrors onto the same
        # physical rows (corrected 2026-07-15).
        raw = line % (2 * image_height)
        row = raw if raw < image_height else (2 * image_height - 1 - raw)
        z_t[row, :] = z[:half]
        z_r[row, :] = z[half:2 * half][::-1]
        e_t[row, :] = e[:half]
        e_r[row, :] = e[half:2 * half][::-1]
        t0 = t if t0 is None else t0
        t1 = t
        n += 1
    if n == 0:
        raise SystemExit(f"no frames in {frames_path}")
    return {"z_trace": z_t, "z_retrace": z_r,
            "e_trace": e_t, "e_retrace": e_r,
            "n_frames": n, "duration_s": (t1 - t0) if n > 1 else 0.0,
            "half": half}


def _to_png(arr, path):
    """1–99 percentile normalized grayscale PNG (data-faithful; the colormapped
    pixel-identical view is --live through the real widget)."""
    from PIL import Image
    lo, hi = np.percentile(arr, [1, 99])
    span = (hi - lo) or 1.0
    img = np.clip((arr - lo) / span * 255.0, 0, 255).astype(np.uint8)
    Image.fromarray(img).save(path)
    return path


def replay_offline(frames_path, image_height, write_png=True):
    out = rebuild_images(frames_path, image_height)
    base = frames_path.replace(".frames", "")
    npz = base + "_replay.npz"
    np.savez_compressed(npz, **{k: v for k, v in out.items()
                                if isinstance(v, np.ndarray)})
    made = [npz]
    if write_png:
        for key in ("z_trace", "z_retrace", "e_trace", "e_retrace"):
            made.append(_to_png(out[key], f"{base}_{key}.png"))
    rate = out["n_frames"] / out["duration_s"] if out["duration_s"] else 0.0
    print(f"{out['n_frames']} frames, {out['duration_s']:.1f} s "
          f"({rate:.2f} lines/s), {out['half']} px/direction")
    sidecar = frame_logger.read_sidecar(frames_path)
    if sidecar:
        print("settings:", json.dumps(sidecar.get("settings", {})))
        print(f"logged drops: {sidecar.get('n_dropped_lines', '?')}")
    for p in made:
        print("wrote", p)
    return made


def replay_live(frames_path, image_height, speed):
    from PySide6 import QtCore, QtWidgets
    import calibration
    import live_raster

    records = list(frame_logger.read_frames(frames_path))
    if not records:
        raise SystemExit(f"no frames in {frames_path}")
    half = len(records[0][2]) // 2
    sidecar = frame_logger.read_sidecar(frames_path)
    settings = sidecar.get("settings", {})

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    cal = calibration.Calibration.from_json()
    w = live_raster.LiveRaster(cal, image_height=image_height,
                               pixels_per_line=2 * half)
    if "scan_size_nm" in settings:
        w.set_scan_geometry(settings["scan_size_nm"],
                            settings.get("x_offset_nm", 0.0),
                            settings.get("y_offset_nm", 0.0))
    w.setWindowTitle(f"replay: {os.path.basename(frames_path)}")
    w.resize(900, 700)
    w.show()

    it = iter(records)
    prev_t = records[0][0]

    def step():
        nonlocal prev_t
        try:
            t, line, z, e = next(it)
        except StopIteration:
            timer.stop()
            print("replay complete")
            return
        w.update_line(line, z, e)
        delay = max(0.0, (t - prev_t)) / max(speed, 1e-6)
        prev_t = t
        timer.start(int(delay * 1000))

    timer = QtCore.QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(step)
    timer.start(0)
    app.exec()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("frames", help="path to a .frames file")
    ap.add_argument("--live", action="store_true",
                    help="replay through the real LiveRaster widget")
    ap.add_argument("--speed", type=float, default=1.0,
                    help="live replay speed multiplier (default 1x)")
    ap.add_argument("--height", type=int, default=256,
                    help="image height in lines (LiveRaster default 256)")
    ap.add_argument("--no-png", action="store_true")
    args = ap.parse_args()
    if args.live:
        replay_live(args.frames, args.height, args.speed)
    else:
        replay_offline(args.frames, args.height, write_png=not args.no_png)


if __name__ == "__main__":
    main()

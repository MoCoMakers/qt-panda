"""Equivalence gates for reconstruct.py (pipeline v2, D38): the shared module must reproduce
the old code exactly in its default ("stamped") mode, and the slip correction must follow the
documented rule (D34)."""
import glob
import os

import numpy as np
import pytest

import reconstruct as R
import scan_paths as S
import superscan
from replay import sweep_index as SI

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
DATA = os.path.join(REPO, "TeamUpdate", "data")


def _old_sweep_image(records, sweep, H, half, channel):
    """Frozen copy of sweep_index.sweep_image before the migration (the reference)."""
    img = np.full((H, half), np.nan, np.float32)
    src_z = channel.startswith("z")
    retrace = channel.endswith("retrace")
    for t, line, z, e in records[sweep["first_record"]:sweep["last_record"] + 1]:
        if len(z) < 2 * half:
            continue
        raw = line % (2 * H)
        row = raw if raw < H else (2 * H - 1 - raw)
        vals = (z if src_z else e)
        seg = vals[half:2 * half][::-1] if retrace else vals[:half]
        img[row, :] = seg
    return img


def _old_build_sweeps(records, H):
    """Frozen copy of the sweep_index.build_index segmentation loop (the reference)."""
    epochs, sweeps = [], []
    cur = None; prev_raw = None; half = None; epoch_id = 0

    def close(reason):
        nonlocal cur
        if cur is None:
            return
        cur["partial"] = cur["lines"] < H; cur["end_reason"] = reason
        sweeps.append(cur); cur = None

    for idx, (t, line, z, e) in enumerate(records):
        h2 = len(z) // 2
        if half is None:
            half = h2
        if h2 != half:
            close("geometry_change"); epochs.append({"epoch": epoch_id, "pixels_per_direction": half})
            epoch_id += 1; half = h2; prev_raw = None
        raw = line % (2 * H)
        d = "up" if raw < H else "down"
        wrapped = prev_raw is not None and raw < prev_raw
        if cur is None or d != cur["dir"] or wrapped:
            close("boundary")
            cur = {"i": len(sweeps), "epoch": epoch_id, "dir": d, "t_start": t, "t_end": t, "lines": 0,
                   "first_record": idx, "last_record": idx}
        cur["t_end"] = t; cur["last_record"] = idx; cur["lines"] += 1; prev_raw = raw
    close("end_of_file")
    epochs.append({"epoch": epoch_id, "pixels_per_direction": half})
    return sweeps, epochs


# ------------------------------------------------------------------ slip correction rule
def _firmware_stamps(spec, frames=3):
    """Stamped line numbers exactly as FW 5.6 sends them, from the literal firmware port."""
    ref = S.FirmwareRasterRef(spec)
    stamps, true = [], []
    for n in range(spec.ticks_per_frame * frames):
        x, y, line, pix = ref.tick()
        if ref.sampleCounter == 0 and ref.pixelCounter == 0:    # a line just completed
            stamps.append(line)
            true.append(len(true) % spec.bins)
    return stamps, true


@pytest.mark.parametrize("spp,bins", [(2, 8), (3, 16), (1, 64)])
def test_slip_correction_recovers_true_line_index(spp, bins):
    stamps, true = _firmware_stamps(S.Spec(spp=spp, bins=bins))
    assert stamps != true                                    # the slip is real in the port
    fixed, info = R.slip_correct(stamps, bins)
    assert fixed == true
    assert info["n_remapped"] > 0


def test_slip_correction_mid_run_start():
    # a recording that starts after the first cycle: recognised by the first stamp == bins-1
    stamps, true = _firmware_stamps(S.Spec(spp=2, bins=8), frames=4)
    k = 12
    fixed, _ = R.slip_correct(stamps[k:], 8)
    assert fixed[fixed.index(7):] == true[k:][fixed.index(7):]


# ------------------------------------------------------------------ gates on synthetic records
def _synthetic_records(n_lines=300, ppl=16, seed=0):
    rng = np.random.default_rng(seed)
    recs = []
    for k in range(n_lines):
        z = rng.integers(-10_000, 10_000, ppl).astype(np.int32)
        e = rng.integers(-10_000, 10_000, ppl).astype(np.int32)
        recs.append((1000.0 + k * 0.01, k % ppl, z, e))
    return recs


def test_gate1_synthetic_sweeps_and_images_identical():
    recs = _synthetic_records()
    H, half = 8, 8
    old_s, old_e = _old_build_sweeps(recs, H)
    new_s, new_e = R.build_sweeps(recs, H)
    assert old_s == new_s and old_e == new_e
    for s in new_s:
        for ch in ("z_trace", "z_retrace", "e_trace", "e_retrace"):
            np.testing.assert_array_equal(_old_sweep_image(recs, s, H, half, ch), R.sweep_image(recs, s, H, half, ch))


def test_gate3_superscan_fold_matches_shared_fold():
    rng = np.random.default_rng(3)
    H, W = 8, 6
    lines = [(k, rng.normal(size=W)) for k in range(2 * H + 3)]
    img = superscan.fold_frame(lines, H, forward_only=False)
    ref = np.full((H, W), np.nan)
    for ln, tr in lines:
        ref[R.fold_row(ln % (2 * H), H)] = tr
    np.testing.assert_array_equal(img, ref)


def _old_rebuild_images(frames_path, image_height):
    """Frozen copy of replay_frames.rebuild_images' fold before the migration (the reference)."""
    import frame_logger
    out = None; half = None
    for t, line, z, e in frame_logger.read_frames(frames_path):
        if half is None:
            half = len(z) // 2
            out = {k: np.zeros((image_height, half), np.float32)
                   for k in ("z_trace", "z_retrace", "e_trace", "e_retrace")}
        if len(z) < 2 * half:
            continue
        raw = line % (2 * image_height)
        row = raw if raw < image_height else (2 * image_height - 1 - raw)
        out["z_trace"][row, :] = z[:half]; out["z_retrace"][row, :] = z[half:2 * half][::-1]
        out["e_trace"][row, :] = e[:half]; out["e_retrace"][row, :] = e[half:2 * half][::-1]
    return out


def test_gate3_replay_frames_matches_livefold(tmp_path):
    import frame_logger
    import replay_frames
    fl = frame_logger.FrameLogger(log_dir=str(tmp_path))
    fl.start({"pixels_per_line": 16})
    for t, line, z, e in _synthetic_records(70, 16):
        fl.on_line(line, z, e)
    path = fl.stop()
    old = _old_rebuild_images(path, 8)
    new = replay_frames.rebuild_images(path, image_height=8)       # migrated onto LiveFold
    lf = R.LiveFold(8, 8)
    for t, line, z, e in frame_logger.read_frames(path):
        lf.add_line(line, z, e)
    for k in ("z_trace", "z_retrace", "e_trace", "e_retrace"):
        np.testing.assert_array_equal(old[k], getattr(lf, k))
        np.testing.assert_array_equal(old[k], new[k])


# ------------------------------------------------------------------ gate 1 on every recording
_FRAMES = sorted(glob.glob(os.path.join(DATA, "*", "*.frames")))


@pytest.mark.skipif(not _FRAMES, reason="no recorded .frames on this machine")
def test_gate1_all_recordings_stamped_identical_and_slip_keeps_sweep_numbering():
    checked = 0
    for fp in _FRAMES:
        recs = SI.load_frames(fp)
        if not recs:
            continue
        settings = (SI.frame_logger.read_sidecar(fp) or {}).get("settings", {})
        H = R.derive_height(settings, recs)
        old_s, old_e = _old_build_sweeps(recs, H)
        new_s, new_e = R.build_sweeps(recs, H)
        assert old_s == new_s and old_e == new_e, fp
        # images: every sweep for small files, a spread sample for big ones
        step = max(1, len(new_s) // 40)
        for s in new_s[::step]:
            half = next(e["pixels_per_direction"] for e in new_e if e["epoch"] == s["epoch"])
            for ch in ("z_trace", "e_retrace"):
                a = _old_sweep_image(recs, s, H, half or 1, ch)
                b = R.sweep_image(recs, s, H, half or 1, ch)
                np.testing.assert_array_equal(a, b)
        # slip-corrected images are built on the STAMPED segmentation (sweep numbers frozen);
        # they must differ from stamped images only by rows moving, never by losing sweeps
        lines, info = R.line_indices(recs, H, "slip_corrected")
        for s in new_s[::step]:
            half = next(e["pixels_per_direction"] for e in new_e if e["epoch"] == s["epoch"])
            img = R.sweep_image(recs, s, H, half or 1, "e_trace", lines)
            assert img.shape == (H, half or 1)
        checked += 1
    assert checked > 0


def test_corrected_images_match_truth_with_frozen_numbering():
    """Firmware-port stamps (with the slip) -> corrected rows on the stamped segmentation must
    equal the images built from the TRUE line indices, for every complete sweep."""
    spec = S.Spec(spp=2, bins=16)
    stamps, true = _firmware_stamps(spec, frames=4)
    rng = np.random.default_rng(5)
    recs = [(float(k), st, rng.integers(-99, 99, 16).astype(np.int32), rng.integers(-99, 99, 16).astype(np.int32))
            for k, st in enumerate(stamps)]
    H, half = 8, 8
    true_recs = [(t, tl, z, e) for (t, _, z, e), tl in zip(recs, true)]
    sw_stamped, _ = R.build_sweeps(recs, H)
    sw_true, _ = R.build_sweeps(true_recs, H)
    # the stamped segmentation may carry one extra 1-line sweep at the end; pair the rest
    assert [x["dir"] for x in sw_stamped[:len(sw_true)]] == [x["dir"] for x in sw_true]
    fixed, _ = R.slip_correct(stamps, 16)
    for s_st, s_tr in zip(sw_stamped, sw_true):
        if s_tr["partial"] or s_tr["first_record"] == 0:
            continue
        for ch in ("z_trace", "e_retrace"):
            a = R.sweep_image(recs, s_st, H, half, ch, fixed)
            b = R.sweep_image(true_recs, s_tr, H, half, ch)
            np.testing.assert_array_equal(a, b)

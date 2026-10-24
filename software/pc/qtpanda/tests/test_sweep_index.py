"""B7 (pipeline v2): sweep_index on reconstruct.py — index version + rebuild, frozen sweep
numbering (D39), slip-corrected rows with a change-log (D34), and the exact stamped revert."""
import json
import os
import struct

import numpy as np

import frame_logger
import reconstruct as R
import scan_paths as S
from replay import sweep_index as SI
from test_reconstruct_equivalence import _firmware_stamps, _old_sweep_image


def _write_frames(path, stamps, ppl, seed=1):
    rng = np.random.default_rng(seed)
    head = struct.Struct("<BdHH")
    with open(path, "wb") as f:
        for k, line in enumerate(stamps):
            z = rng.integers(-999, 999, ppl).astype("<i4"); e = rng.integers(-999, 999, ppl).astype("<i4")
            f.write(head.pack(frame_logger._MAGIC, 1000.0 + k, line, ppl)); f.write(z.tobytes()); f.write(e.tobytes())
    with open(path[:-len(".frames")] + ".json", "w") as f:
        json.dump({"settings": {"pixels_per_line": ppl}}, f)


def _recording(tmp_path):
    stamps, true = _firmware_stamps(S.Spec(spp=2, bins=16), frames=4)
    fp = str(tmp_path / "scan_1.frames")
    _write_frames(fp, stamps, 16)
    return fp, stamps, true


def test_index_version_and_rebuild(tmp_path):
    fp, _, _ = _recording(tmp_path)
    idx = SI.load_or_build(fp)
    assert idx["index_version"] == SI.INDEX_VERSION and idx["line_index"] == "slip_corrected"
    # an old (unversioned) index newer than the .frames is rebuilt, not trusted
    old = dict(idx); old.pop("index_version"); old["sweeps"] = []
    with open(SI.index_path(fp), "w") as f:
        json.dump(old, f)
    assert SI.load_or_build(fp)["sweeps"] == idx["sweeps"]


def test_numbering_frozen_and_changelog_written(tmp_path):
    fp, stamps, _ = _recording(tmp_path)
    idx = SI.write_index(fp)
    stamped = SI.build_index(fp, line_index="stamped")
    assert idx["sweeps"] == stamped["sweeps"]               # D39: same sweeps, same numbers
    log = json.load(open(R.corrections_path(fp)))
    assert log["decision"] == "D34" and "revert" in log
    assert log["info"]["affected_sweeps"] and log["info"]["examples"]


def test_stamped_revert_is_exactly_the_old_image(tmp_path):
    fp, _, _ = _recording(tmp_path)
    idx = SI.build_index(fp, line_index="stamped")
    recs = SI.load_frames(fp)
    H, half = idx["image_height"], 8
    for sw in idx["sweeps"]:
        for ch in ("z_trace", "z_retrace", "e_trace", "e_retrace"):
            np.testing.assert_array_equal(SI.sweep_image(recs, sw, H, half, ch),
                                          _old_sweep_image(recs, sw, H, half, ch))


def test_corrected_rows_are_where_lines_were_scanned(tmp_path):
    fp, stamps, true = _recording(tmp_path)
    idx = SI.build_index(fp)
    recs = SI.load_frames(fp)
    lines = SI.line_indices_for(recs, idx)
    assert lines == true
    true_recs = [(t, tl, z, e) for (t, _, z, e), tl in zip(recs, true)]
    sw_true, _ = R.build_sweeps(true_recs, idx["image_height"])
    for s_st, s_tr in zip(idx["sweeps"], sw_true):
        if s_tr["partial"] or s_tr["first_record"] == 0:
            continue
        np.testing.assert_array_equal(SI.sweep_image(recs, s_st, 8, 8, "z_trace", lines),
                                      SI.sweep_image(true_recs, s_tr, 8, 8, "z_trace"))


def test_player_daydata_toggle(tmp_path):
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "replay"))
    import sweep_player as P                   # replay/ tools import their siblings flat
    fp, _, _ = _recording(tmp_path)
    d = P.DayData(fp, None)
    i = next(k for k, s in enumerate(d.sweeps) if not s[2]["partial"] and s[2]["first_record"] > 0)
    a, _, _ = d.image(i, "z_trace")
    d.line_index = "stamped"
    b, _, _ = d.image(i, "z_trace")
    assert not np.array_equal(np.nan_to_num(a), np.nan_to_num(b))   # the toggle really changes rows

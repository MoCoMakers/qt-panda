"""Clip-series frame index (B) — pure, no GUI."""
import frame_index


def test_add_between_nearest_decimate_persist(tmp_path):
    idx = frame_index.FrameIndex(str(tmp_path / "manifest.json"))
    for i in range(10):
        idx.add(t=float(i), tm=i * 100, path=f"f{i}.png", telemetry={"i": i})

    assert len(idx) == 10
    assert [f["tm"] for f in idx.between(200, 400)] == [200, 300, 400]
    assert idx.nearest(240)["tm"] == 200
    assert idx.nearest(260)["tm"] == 300
    assert len(idx.decimate(3)) == 3
    assert idx.decimate(3)[0]["tm"] == 0            # overview spans the record

    path = idx.save()
    reloaded = frame_index.FrameIndex.load(path)
    assert len(reloaded) == 10
    assert reloaded.frames[5]["telemetry"] == {"i": 5}


def test_empty_index():
    idx = frame_index.FrameIndex("x")
    assert idx.nearest(5) is None and idx.decimate(3) == []

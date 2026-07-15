"""frame_index — clip-series index binding captured frames to the timeline (B).

The "video for the LLM" substrate: each frame (a rendered raster/plot PNG) is
recorded with its firmware time_millis + telemetry, so the agent can scrub
(between), jump (nearest), or get a decimated overview (decimate) of a run —
random access into the recording, joined to the data on the same clock.
Pure/Qt-free; the frames themselves are produced by render_screens.
"""
import json


class FrameIndex:
    def __init__(self, manifest_path):
        self.manifest_path = manifest_path
        self.frames = []

    def add(self, t, tm, path, telemetry=None):
        self.frames.append({"t": t, "tm": tm, "path": path,
                            "telemetry": telemetry or {}})
        return self

    def save(self):
        with open(self.manifest_path, "w") as f:
            json.dump({"frames": self.frames}, f, indent=2)
        return self.manifest_path

    @classmethod
    def load(cls, manifest_path):
        idx = cls(manifest_path)
        with open(manifest_path) as f:
            idx.frames = json.load(f).get("frames", [])
        return idx

    def between(self, tm0, tm1):
        """All frames whose tm falls in [tm0, tm1] (scrub a window)."""
        return [fr for fr in self.frames if tm0 <= fr["tm"] <= tm1]

    def nearest(self, tm):
        """The single frame closest to tm (jump to a moment)."""
        if not self.frames:
            return None
        return min(self.frames, key=lambda fr: abs(fr["tm"] - tm))

    def decimate(self, n):
        """Up to n evenly-spaced frames spanning the record (overview /
        contact-sheet), so the agent looks at the whole arc cheaply before
        drilling into an interesting window."""
        if n <= 0 or not self.frames:
            return []
        if len(self.frames) <= n:
            return list(self.frames)
        step = len(self.frames) / n
        return [self.frames[int(i * step)] for i in range(n)]

    def __len__(self):
        return len(self.frames)

"""scan_paths — commanded tip positions for every scan path, bit-exact with the firmware.

Design and contract: docs/test-plans/scan-path-design.md.  Rules that shape this file:

* Every named path is defined here in code, versioned.  A released (name, version) is never
  edited; a change adds a new version, so old recordings still reconstruct exactly.
* Positions are integers in the firmware's 20-bit position units (x_pos / y_pos), computed
  with integer arithmetic only, so the firmware can reproduce them bit for bit.
* Tick numbering follows controlTick(): the scan counters advance FIRST, so the sample taken
  on tick n (n = 1, 2, ...) belongs to the position of tick n.  (The ADC value read on tick n
  is the conversion started on tick n-1: a fixed one-tick delay, handled by the physics layer.)
* A bin is `spp` consecutive ticks (firmware samplesPerPixel); a segment is `bins` bins and is
  sent as one 'L' frame (for the raster: one line = trace + retrace).  A frame is
  `segments` segments.  For the raster, a frame is one full Y-cycle (up + down sweep).
* Recordings without a `scan_path` block are `raster` v1: today's FW 5.6 path.
* Release status: `raster` v1 is frozen (it IS FW 5.6).  The other v1 generators are frozen at
  the first recording or firmware build that uses them; until then they may still be corrected.

Paths
  raster v1         FW 5.6 controlTick() step 1, exact rational steps, continuous Y (mode 0)
  custom v1         vertices from a 'qtpanda-path' file, interpolated with the raster's rule
  spiral_arch v1    Archimedean spiral, constant angular speed (cav) or ~constant tip speed (clv)
  spiral_fermat v1  Fermat spiral r ~ sqrt(phase): even area per turn
  loops_centre v1   circles of growing radius, each reached and left along a spoke from the centre
  spokes v1         out-and-back rays through the centre at evenly spaced angles
  rose v1           figure-8 (x = sin t, y = sin 2t) precessing about the centre: all-sine drive
Transforms (any path, per frame): rotation by an angle (Q15 cos/sin stored as integers) and a
transpose (fast axis swap).  Sequences: `crosshatch` = transpose on every other frame.
"""
import hashlib
import json
import math

import numpy as np

LIMIT = 1 << 30                    # SCAN_COUNTER_LIMIT
NUM = 4 * LIMIT                    # counter travel per full triangle period
Q15 = 1 << 15                      # 1.0 in the Q15 cos/sin and sine table
TURN = 1 << 32                     # one full turn of a phase accumulator
SIN_BITS = 12                      # sine table: 4096 entries per turn


# ------------------------------------------------------------------ integer helpers
def isqrt_vec(v):
    """floor(sqrt(v)) for int64 arrays, exact (float estimate, then integer correction)."""
    v = np.asarray(v, dtype=np.int64)
    r = np.floor(np.sqrt(v.astype(np.float64))).astype(np.int64)
    r = np.where(r * r > v, r - 1, r)
    r = np.where((r + 1) * (r + 1) <= v, r + 1, r)
    return r


def _sin_table():
    k = np.arange((1 << SIN_BITS) + 1)
    return np.round(np.sin(2 * np.pi * k / (1 << SIN_BITS)) * Q15).astype(np.int64)


SIN_TABLE = _sin_table()           # frozen by tests (sha256); the firmware embeds the same values


def sin_q15(phase):
    """Q15 sine of a uint32 phase (2^32 = one turn): table + 16-bit linear interpolation."""
    p = np.asarray(phase, dtype=np.int64) & (TURN - 1)
    i = p >> (32 - SIN_BITS)
    f = (p >> (32 - SIN_BITS - 16)) & 0xFFFF
    a, b = SIN_TABLE[i], SIN_TABLE[i + 1]
    return a + (((b - a) * f) >> 16)


def cos_q15(phase):
    return sin_q15(np.asarray(phase, dtype=np.int64) + (TURN >> 2))


def rot_q15(deg):
    """(cos, sin) as Q15 integers for a rotation; stored in the sidecar, so reconstruction never
    depends on floating-point rounding."""
    t = math.radians(deg)
    return int(round(math.cos(t) * Q15)), int(round(math.sin(t) * Q15))


# ------------------------------------------------------------------ frame geometry
class Spec:
    """Scan geometry shared by all paths (firmware units)."""

    def __init__(self, spp, bins, segments=None, scan_size=100000, xo=0, yo=0, line_repeat=1,
                 tick_us=10.0):
        self.spp, self.bins = int(spp), int(bins)
        self.segments = int(segments if segments is not None else bins * line_repeat)
        self.scan_size, self.xo, self.yo = int(scan_size), int(xo), int(yo)
        self.line_repeat, self.tick_us = int(line_repeat), float(tick_us)

    @property
    def ticks_per_frame(self):
        return self.spp * self.bins * self.segments

    def as_dict(self):
        return dict(spp=self.spp, bins=self.bins, segments=self.segments, scan_size=self.scan_size,
                    xo=self.xo, yo=self.yo, line_repeat=self.line_repeat, tick_us=self.tick_us)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


def counter_to_pos(c, scan_size, off):
    """x_pos = ((int64_t)xCount * scanSize >> 31) + xo  (arithmetic shift = floor)."""
    return ((np.asarray(c, dtype=np.int64) * scan_size) >> 31) + off


def _fold(a):
    """Triangle wave of an unbounded counter advance `a`, starting at -LIMIT climbing.
    Equals the firmware's reflect-at-the-limits sequence (proved by FirmwareRasterRef)."""
    p = np.asarray(a, dtype=np.int64) % NUM
    return np.where(p <= 2 * LIMIT, -LIMIT + p, 3 * LIMIT - p)


def raster_dens(spec):
    xden = spec.spp * spec.bins
    yden = xden * spec.bins * spec.line_repeat
    return xden, yden


# ------------------------------------------------------------------ paths (each returns x_pos, y_pos for ticks n)
def _raster_v1(n, spec, p):
    xden, yden = raster_dens(spec)
    xc = _fold((n * NUM) // xden)
    yc = _fold((n * NUM) // yden)
    return counter_to_pos(xc, spec.scan_size, spec.xo), counter_to_pos(yc, spec.scan_size, spec.yo)


def _custom_v1(n, spec, p):
    """Vertices [[tick, X, Y], ...] in counter units x D (D = p['denominator']).  Between vertices
    k and k+1 the exact position is e = (V_k*T + (V_k+1 - V_k)*j) / (T*D); it is floored on
    rising edges and ceiled on falling edges (rounded toward the edge start), which is exactly
    what the firmware's carried-remainder stepping produces.  Ticks past the last vertex hold it."""
    V = p["_vertices"]
    D = int(p["denominator"])
    t = V[:, 0]
    k = np.clip(np.searchsorted(t, n, side="right") - 1, 0, len(t) - 2)
    T = t[k + 1] - t[k]
    j = np.clip(n - t[k], 0, T)
    out = []
    for ax in (1, 2):
        a, b = V[k, ax], V[k + 1, ax]
        delta = b - a
        TD = T * D
        # e*TD = a*T + delta*j, computed without int64 overflow:
        qa, ra = np.divmod(a, D)                      # a = qa*D + ra
        dq, dr = np.divmod(np.abs(delta), TD)         # |delta| = dq*TD + dr
        s = np.sign(delta)
        num = ra * T + s * dr * j                      # small: |ra*T| < TD, |dr*j| < TD*T
        fl = np.floor_divide(num, TD)
        ce = -np.floor_divide(-num, TD)
        c = qa + s * dq * j + np.where(delta >= 0, fl, ce)
        off = spec.xo if ax == 1 else spec.yo
        out.append(counter_to_pos(c, spec.scan_size, off))
    return out[0], out[1]


def _radius_max(spec):
    return int(spec.scan_size) >> 1                   # half the scan square, position units


def _polar(r, theta, spec, sense):
    th = theta if sense >= 0 else -theta
    return (spec.xo + ((r * cos_q15(th)) >> 15), spec.yo + ((r * sin_q15(th)) >> 15))


def _half_index(n, N, mode):
    """Index along an out path of length N/2 (out-in) or N (out / in)."""
    if mode == "out":
        return n, N
    if mode == "in":
        return N - n, N
    h = N // 2                                        # out-in: retrace the same spiral backwards
    return np.where(n <= h, n, N - n), h


def _phase(m, M, turns, speed):
    phimax = int(turns) * TURN
    m = np.clip(m, 0, M)
    if speed == "cav":
        return (m * phimax) // M, phimax
    u = isqrt_vec((m << 32) // M)                     # ~ sqrt(m/M) in [0, 2^16]: ~constant tip speed
    return (phimax * u) >> 16, phimax


def _spiral_arch_v1(n, spec, p):
    m, M = _half_index(n, spec.ticks_per_frame, p.get("direction", "out-in"))
    phi, phimax = _phase(m, M, p.get("turns", 64), p.get("speed", "clv"))
    r = (_radius_max(spec) * phi) // phimax
    return _polar(r, phi, spec, p.get("sense", 1))


def _spiral_fermat_v1(n, spec, p):
    m, M = _half_index(n, spec.ticks_per_frame, p.get("direction", "out-in"))
    phi, phimax = _phase(m, M, p.get("turns", 64), "cav")
    u = phi // (phimax >> 24)                         # phase fraction in [0, 2^24], exact, no overflow
    r = (_radius_max(spec) * isqrt_vec(u)) >> 12
    return _polar(r, phi, spec, p.get("sense", 1))


def _alloc(lengths, N):
    """Integer tick counts proportional to lengths, summing to N (cumulative rounding)."""
    c = np.cumsum(np.asarray(lengths, dtype=np.float64))
    edges = np.concatenate([[0], np.floor(c / c[-1] * N + 0.5).astype(np.int64)])
    return edges


def _loops_centre_v1(n, spec, p):
    K = int(p.get("loops", 32)); R = _radius_max(spec)
    rot = int(p.get("rotate_per_loop", TURN // 7))
    radii = [(R * (k + 1)) // K for k in range(K)]
    lengths = []
    for r in radii:
        lengths += [r, 2 * math.pi * r, r]            # spoke out, circle, spoke back
    e = _alloc(lengths, spec.ticks_per_frame)
    seg = np.clip(np.searchsorted(e, n, side="right") - 1, 0, len(lengths) - 1)
    j, T = n - e[seg], np.maximum(e[seg + 1] - e[seg], 1)
    k, part = seg // 3, seg % 3
    rk = np.asarray(radii, dtype=np.int64)[k]
    a0 = (k.astype(np.int64) * rot) & (TURN - 1)
    r = np.where(part == 0, (rk * j) // T, np.where(part == 1, rk, rk - (rk * j) // T))
    th = np.where(part == 1, a0 + (j * TURN) // T, a0)
    return _polar(r, th, spec, p.get("sense", 1))


def _spokes_v1(n, spec, p):
    M = int(p.get("spokes", 256)); R = _radius_max(spec); N = spec.ticks_per_frame
    m = np.minimum((n * M) // N, M - 1)
    j = n - (m * N) // M
    T = ((m + 1) * N) // M - (m * N) // M
    tri = np.where(2 * j <= T, (2 * j * R) // T, (2 * (T - j) * R) // T)
    stride = int(p.get("stride", 97))                 # coprime with M: spreads consecutive spokes
    th = (((m * stride) % M) * TURN) // M
    return _polar(tri, th, spec, p.get("sense", 1))


def _rose_v1(n, spec, p):
    """Figure-8 x' = A sin(t), y' = A sin(2t) rotated by a slowly precessing angle; every axis
    is a sum of a few sines (smoothest drive).  A = radius / 1.3 keeps the 8 inside the disc."""
    L = int(p.get("loops", 256)); N = spec.ticks_per_frame
    q, r = np.divmod(n * L, N)                        # L figure-8 periods per frame; only t mod TURN
    t = (r * TURN) // N                               #   matters, so drop q*TURN (no int64 overflow)
    prec = int(p.get("precession_turns_q16", 1 << 15)) # total precession in turns, Q16 (0.5 turn)
    phi = (n * prec * (TURN >> 16)) // N
    A = (_radius_max(spec) * 10) // 13
    xp = (A * sin_q15(t)) >> 15
    yp = (A * sin_q15(2 * t)) >> 15
    c, s = cos_q15(phi), sin_q15(phi)
    return spec.xo + ((xp * c - yp * s) >> 15), spec.yo + ((xp * s + yp * c) >> 15)


PATHS = {
    ("raster", 1): _raster_v1,
    ("custom", 1): _custom_v1,
    ("spiral_arch", 1): _spiral_arch_v1,
    ("spiral_fermat", 1): _spiral_fermat_v1,
    ("loops_centre", 1): _loops_centre_v1,
    ("spokes", 1): _spokes_v1,
    ("rose", 1): _rose_v1,
}
LATEST = {name: max(v for (nm, v) in PATHS if nm == name) for (name, _) in PATHS}


# ------------------------------------------------------------------ transforms and sequences
def transform(x, y, spec, cos_s=None, swap=False):
    """Rotation about the scan centre with Q15 integers, then optional transpose (swap)."""
    if cos_s is not None and tuple(cos_s) != (Q15, 0):
        c, s = cos_s
        u, v = x - spec.xo, y - spec.yo
        x, y = spec.xo + ((u * c - v * s) >> 15), spec.yo + ((u * s + v * c) >> 15)
    if swap:
        u, v = x - spec.xo, y - spec.yo
        x, y = spec.xo + v, spec.yo + u
    return x, y


def frame_swap(block, frame):
    seq = (block.get("sequence") or {}).get("id", "none")
    return seq == "crosshatch" and (frame % 2 == 1)


# ------------------------------------------------------------------ public API
def default_block(spec):
    """What a recording without a scan_path block means: today's raster (FW 5.6)."""
    return make_block("raster", {}, spec)


def make_block(name, params, spec, rotation_deg=0.0, sequence="none", custom=None):
    cs = rot_q15(rotation_deg)
    blk = {"id": name, "version": LATEST[name], "params": dict(params),
           "transform": {"rotation_deg": rotation_deg, "cos_q15": cs[0], "sin_q15": cs[1]},
           "sequence": {"id": sequence, "version": 1}, "spec": spec.as_dict(),
           "generator_sha256": generator_sha256()}
    if name == "custom":
        blk["custom_sha256"] = custom_sha256(custom)
        blk["params"] = {"denominator": custom["denominator"], "vertices": custom["vertices"]}
    return blk


def read_block(sidecar, spec_if_missing=None):
    """scan_path block of a recording sidecar; absent -> raster v1 (legacy recordings)."""
    blk = sidecar.get("scan_path") if sidecar else None
    if blk is None:
        if spec_if_missing is None:
            raise ValueError("legacy recording: pass the raster Spec from its settings")
        return default_block(spec_if_missing)
    return blk


def ticks(block, n, frame=0):
    """Commanded (x_pos, y_pos) for absolute tick numbers n (1-based within the frame)."""
    spec = Spec.from_dict(block["spec"])
    p = dict(block.get("params") or {})
    if block["id"] == "custom":
        p["_vertices"] = np.asarray(p["vertices"], dtype=np.int64)
    fn = PATHS[(block["id"], int(block["version"]))]
    x, y = fn(np.asarray(n, dtype=np.int64), spec, p)
    tr = block.get("transform") or {}
    cs = (tr.get("cos_q15", Q15), tr.get("sin_q15", 0))
    return transform(np.asarray(x, np.int64), np.asarray(y, np.int64), spec, cs, frame_swap(block, frame))


def frame_ticks(block, frame=0):
    spec = Spec.from_dict(block["spec"])
    n = np.arange(1, spec.ticks_per_frame + 1, dtype=np.int64)
    x, y = ticks(block, n, frame)
    return n, x, y


def reconstruct(block, frame=0):
    """Map of one frame: for every (segment, bin), the mean commanded position over its ticks
    (exactly what the firmware averaged over, not the bin midpoint) and the first tick.
    Returns dict of (segments, bins) arrays: x, y (position units, float64), tick0 (int64)."""
    spec = Spec.from_dict(block["spec"])
    n, x, y = frame_ticks(block, frame)
    shp = (spec.segments, spec.bins, spec.spp)
    return dict(x=x.reshape(shp).mean(-1), y=y.reshape(shp).mean(-1),
                tick0=n.reshape(shp)[..., 0], spec=spec)


# ------------------------------------------------------------------ custom path files
def raster_to_custom(spec):
    """The raster v1 frame written as a 'qtpanda-path' vertex file: one vertex at every X
    turnaround (Y turnarounds fall on those ticks too).  Exact rationals: D = yden."""
    xden, yden = raster_dens(spec)
    assert xden % 2 == 0, "pixels per line must be even"
    D = yden
    half = xden // 2
    verts = []
    for k in range(0, spec.ticks_per_frame // half + 1):
        tk = k * half
        ax = (tk * NUM) // xden                       # exact integer at X turnarounds
        x = int(_fold(ax)) * D
        ay = tk * NUM                                 # unfolded Y advance x D
        pp = ay % (NUM * D)
        y = (-LIMIT * D + pp) if pp <= 2 * LIMIT * D else (3 * LIMIT * D - pp)
        verts.append([tk, x, y])
    return {"format": "qtpanda-path", "version": 1, "units": "counter_over_D",
            "denominator": D, "vertices": verts,
            "note": "raster v1 frame expressed as vertices (validation of the custom path engine)"}


def load_custom(path):
    d = json.load(open(path, encoding="utf-8"))
    if d.get("format") != "qtpanda-path" or int(d.get("version", 0)) != 1:
        raise ValueError("not a qtpanda-path v1 file")
    v = d["vertices"]
    if any(b[0] <= a[0] for a, b in zip(v, v[1:])):
        raise ValueError("vertex ticks must increase")
    return d


def custom_sha256(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()


def generator_sha256():
    import inspect, sys
    return hashlib.sha256(inspect.getsource(sys.modules[__name__]).encode()).hexdigest()


# ------------------------------------------------------------------ literal firmware port (reference)
class FirmwareRasterRef:
    """Line-for-line port of controlTick() step 1 and the pixel/line counters (FW 5.6).
    Slow, and deliberately not vectorised: it is the audit reference the fast code is tested
    against."""

    def __init__(self, spec):
        self.spec = spec
        xden, yden = raster_dens(spec)
        self.xStep, self.xRem, self.xDen = NUM // xden, NUM % xden, xden
        self.yStep, self.yRem, self.yDen = NUM // yden, NUM % yden, yden
        self.xCount = self.yCount = -LIMIT
        self.xDir = self.yDir = 1
        self.xAcc = self.yAcc = 0
        self.sampleCounter = self.pixelCounter = self.lineCounter = 0

    def tick(self):
        sx = self.xStep; self.xAcc += self.xRem
        if self.xAcc >= self.xDen: self.xAcc -= self.xDen; sx += 1
        self.xCount += self.xDir * sx
        if self.xCount >= LIMIT:
            self.xCount = LIMIT - (self.xCount - LIMIT); self.xDir = -1
        elif self.xCount <= -LIMIT:
            self.xCount = -LIMIT + (-LIMIT - self.xCount); self.xDir = 1
        x_pos = ((self.xCount * self.spec.scan_size) >> 31) + self.spec.xo
        sy = self.yStep; self.yAcc += self.yRem
        if self.yAcc >= self.yDen: self.yAcc -= self.yDen; sy += 1
        self.yCount += self.yDir * sy
        yBottom = False
        if self.yCount >= LIMIT:
            self.yCount = LIMIT - (self.yCount - LIMIT); self.yDir = -1
        elif self.yCount <= -LIMIT:
            self.yCount = -LIMIT + (-LIMIT - self.yCount); self.yDir = 1; yBottom = True
        y_pos = ((self.yCount * self.spec.scan_size) >> 31) + self.spec.yo
        if yBottom:
            self.lineCounter = 0
        line, pix = self.lineCounter, self.pixelCounter
        self.sampleCounter += 1
        if self.sampleCounter >= self.spec.spp:
            self.sampleCounter = 0; self.pixelCounter += 1
            if self.pixelCounter >= self.spec.bins:
                self.pixelCounter = 0; self.lineCounter += 1
                if self.lineCounter >= self.spec.bins: self.lineCounter = 0
        return x_pos, y_pos, line, pix

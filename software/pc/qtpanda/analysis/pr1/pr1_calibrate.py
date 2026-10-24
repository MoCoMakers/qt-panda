"""Calibrate the PR1 metrics on synthetic images with known physics: diagonal step edges (intrinsic
10-90 % width ~2.6 px) scanned as trace/retrace, then either (a) a first-order low-pass along the
time order of each half-line, or (b) a pure latency (shift without blur).  Checks that
whole_shift recovers 2*v*tau and that edge_widths sees the extra X width only for the filter."""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pr1 as P
from scipy.signal import lfilter

rng = np.random.default_rng(4)
H, W = 256, 256


def surface(H, W, oversample=8):
    """Terraces separated by diagonal steps, sampled finely along X so lags can be fractional."""
    y, x = np.mgrid[0:H, 0:W * oversample] / np.array([[1.0], [oversample]])[1]
    y = y.astype(float)
    h = np.zeros_like(x)
    for k, off in enumerate((40, 110, 170, 230)):
        h += 1.0 * (0.5 + 0.5 * np.tanh((x - 0.35 * y - off) / 0.6))
    h += 0.6 * (0.5 + 0.5 * np.tanh((x + 0.5 * y - 300) / 0.6))
    return h


def scan(h, osamp, tau_px=0.0, latency_px=0.0, filt=True, noise=0.02):
    """Trace (left->right) and retrace (right->left, returned in X order) with a first-order filter
    (time constant tau_px, in pixels of travel) or a latency, applied in each direction's time order."""
    out = []
    for direction in (1, -1):
        rows = h[:, ::direction]
        if filt and tau_px > 0:
            a = np.exp(-1.0 / (tau_px * osamp))
            rows = lfilter([1 - a], [1, -a], rows, axis=1, zi=np.tile(rows[:, :1] * (1 - a) / (1 - a), (1, 1))) [0]
        if latency_px > 0:
            k = int(round(latency_px * osamp)); rows = np.concatenate([np.repeat(rows[:, :1], k, 1), rows[:, :-k]], 1)
        img = rows[:, ::osamp][:, :W]
        img = img[:, ::direction] if direction == -1 else img
        out.append(img + rng.normal(0, noise, img.shape))
    return out


osamp = 8
h = surface(H, W, osamp)
res = []
for kind, tau in (("none", 0.0), ("filter", 2.0), ("filter", 5.0), ("filter", 10.0), ("latency", 2.0), ("latency", 5.0), ("latency", 10.0)):
    T, R = scan(h, osamp, tau_px=tau if kind == "filter" else 0.0, latency_px=tau if kind == "latency" else 0.0, filt=(kind == "filter"))
    sh, q = P.whole_shift(T, R)
    wx = np.median(np.r_[P.edge_widths(T, 1), P.edge_widths(R, 1)]); wy = np.median(P.edge_widths(T, 0))
    excess = np.sqrt(max(wx ** 2 - wy ** 2, 0))
    r = dict(kind=kind, tau_px=tau, shift_px=sh, expected_shift_px=-2 * tau if kind != "none" else 0.0, width_x_px=float(wx), width_y_px=float(wy),
             excess_px=float(excess), expected_excess_px=2.197 * tau if kind == "filter" else 0.0)
    res.append(r)
    print(f"{kind:8s} tau {tau:4.1f} px: shift {sh:6.2f} px (expect {r['expected_shift_px']:6.1f})  width X {wx:5.2f} Y {wy:5.2f} px  "
          f"excess {excess:5.2f} px (filter expects {r['expected_excess_px']:5.2f})", flush=True)
json.dump(res, open(os.path.join(HERE, "pr1_calibration.json"), "w"), indent=1)

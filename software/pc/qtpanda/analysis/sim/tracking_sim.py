"""tracking_sim — stage-tracking (drift lock) controllers replayed on the Oct 22 drift.

Truth: the patch drifts up the frame like Oct 22 #20-#31 (0.56 px/s, a jump of ~3.6 px at each
gain change), optionally speeding up 30% for the last third to test adaptation.
Measurements: the patch's offset from its primed reference position, available only at the
times the live band tracker locked on Oct 22 (live_trail.json), with Gaussian noise.
Controllers move a virtual scan offset u; the residual r = drift - u is what the image shows.
  none      : no correction (today)
  step      : at each Y turnaround (every ~25 s) move u by the last measured residual
  alphabeta : continuous feed-forward u' = v_est, plus position/velocity updates at each lock
              (alpha-beta filter; offset moves are ramps, not steps)
"""
import os, json, argparse
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))


def truth(t, v=0.56, jumps=(137.0, 275.0), jump_px=3.6, speedup_at=None, speedup=1.3):
    """Patch position (px, up = +) at times t (s since #20)."""
    t = np.asarray(t, float)
    p = v * t
    if speedup_at is not None:
        p = p + np.where(t > speedup_at, (speedup - 1) * v * (t - speedup_at), 0.0)
    for tj in jumps:
        p = p + np.where(t >= tj, -jump_px, 0.0)
    return p


def lock_times():
    """Times of locked band updates on Oct 22 (simulated live tracker), plus a seed lock at 50 s."""
    f = os.path.join(REPO, "software", "pc", "qtpanda", "analysis", "sim", "live_trail_updates.json")
    U = json.load(open(f))
    ts = sorted({round(u["t"], 2) for u in U if u["ok"]})
    return np.array([50.0] + [x for x in ts if x > 50.0])


def simulate(ctrl, sigma=3.0, speedup_at=None, dt=0.5, T=300.0, alpha=0.5, beta=0.15, seed=1):
    rng = np.random.default_rng(seed)
    locks = lock_times()
    tt = np.arange(0, T + dt, dt)
    p = truth(tt, speedup_at=speedup_at)
    u = np.zeros_like(tt); v_est = 0.0; pending = None; moves = []; r_est = 0.0
    turn = 25.0; next_turn = turn
    li = 0
    for k in range(1, len(tt)):
        t = tt[k]
        u[k] = u[k - 1]
        if ctrl == "alphabeta":
            u[k] += v_est * dt                                     # feed-forward ramp
        # measurement at lock times
        while li < len(locks) and locks[li] <= t:
            meas = (p[k] - u[k]) + rng.normal(0, sigma)            # residual vs primed reference
            if ctrl == "step":
                pending = meas
            elif ctrl == "alphabeta":
                # alpha-beta on the residual: correct position and velocity.
                # First lock: the residual accumulated since priming gives the velocity directly.
                if li == 0:
                    v_est = meas / max(1.0, t)
                else:
                    v_est += beta * meas / max(1.0, (locks[li] - locks[li - 1]))
                corr = alpha * meas
                u[k] += corr; moves.append(abs(corr))
            li += 1
        if ctrl == "step" and t >= next_turn:
            if pending is not None:
                u[k] += pending; moves.append(abs(pending)); pending = None
            next_turn += turn
    r = p - u
    late = tt >= (locks[0] + 60.0)
    return dict(ctrl=ctrl, speedup=speedup_at is not None, rms_px=float(np.sqrt(np.mean(r ** 2))),
                steady_rms_px=float(np.sqrt(np.mean(r[late] ** 2))),
                max_px=float(np.max(np.abs(r))), final_px=float(r[-1]), offset_applied_px=float(u[-1]),
                n_moves=len(moves), max_move_px=float(max(moves) if moves else 0.0)), tt, r


if __name__ == "__main__":
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    res = []; fig, ax = plt.subplots(1, 2, figsize=(12, 3.8), sharey=True)
    for j, sp in enumerate((None, 200.0)):
        for ctrl, col in (("none", "#999"), ("step", "#1f77b4"), ("alphabeta", "#d62728")):
            rr = [simulate(ctrl, speedup_at=sp, seed=s)[0] for s in range(5)]
            m = {k: float(np.mean([x[k] for x in rr])) for k in ("rms_px", "steady_rms_px", "max_px", "final_px", "offset_applied_px", "n_moves", "max_move_px")}
            m.update(ctrl=ctrl, speedup=sp is not None); res.append(m)
            _, tt, r = simulate(ctrl, speedup_at=sp, seed=0)
            ax[j].plot(tt, r * 30 / 256, color=col, label=f"{ctrl}: rms {m['rms_px']*30/256:.2f} nm")
            print(f"{'speed-up' if sp else 'steady  '} {ctrl:9} rms {m['rms_px']:6.1f} px  after first lock+60 s {m['steady_rms_px']:5.1f} px  max {m['max_px']:6.1f} px  moves {m['n_moves']:4.0f}  largest move {m['max_move_px']:5.1f} px")
        ax[j].set_title(("Oct 22 drift" if sp is None else "Oct 22 drift, +30% speed after 200 s") + " (patch offset from start)", fontsize=9)
        ax[j].set_xlabel("s since #20"); ax[j].axhline(0, color="k", lw=0.5); ax[j].legend(fontsize=7)
    ax[0].set_ylabel("residual (nm)")
    plt.tight_layout(); fig.savefig(os.path.join(HERE, "tracking_sim.png"), dpi=95)
    json.dump(res, open(os.path.join(HERE, "tracking_sim.json"), "w"), indent=1)

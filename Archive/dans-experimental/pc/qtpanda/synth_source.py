"""synth_source — deterministic synthetic stability streams (harness H2).

Generates stability-session data with *known* statistics so the whole
analysis pipeline (stab_metrics -> stab_runner verdict -> summary) can be
validated against ground truth we set, with no instrument attached.

The output CSV is byte-compatible with what ``widget._open_stab_log`` writes
(same header/columns), so ``stab_runner.analyze(path)`` grades a synthetic
file exactly as it would a real recording.  This is the offline counterpart
to replaying the six labelled bench CSVs: replay proves we reproduce reality,
synthesis proves we get the *right answer* on data whose answer is defined.

Presets map 1:1 to the stab_runner verdicts (findings F2/F3/F5):

    tunneling  -> TUNNELING_LIKE   one-sided, signed |mean| >= 3*sigma
    noise      -> NOISE_ONLY       zero-mean electronics floor
    emi        -> EMI_CONTAMINATED bipolar zero-mean excursion bursts
    contact    -> CONTACT          a run of ADC-railed samples
    short      -> INSUFFICIENT     too few samples to judge

Usage:
    python synth_source.py --kind tunneling --out /tmp/t.csv
    python synth_source.py --kind noise --n 300 --seed 7 --out /tmp/n.csv
"""

import argparse
import csv

import numpy as np

# --- hardware constants (see interpretation-guide.md) --------------------
# LTC2326-16: +32767 counts == +10.24 V == 102.4 nA across the 100 MOhm preamp.
ADC_RAIL = 32767
A_PER_COUNT = 102.4e-9 / ADC_RAIL      # amps represented by one ADC count
CADENCE_MS = 109                       # median GSTS cadence on the bench
T0_MS = 1_000_000                      # arbitrary firmware uptime start

# CSV columns, in the exact order widget._open_stab_log writes them.
COLUMNS = ["elapsed_s", "time_millis", "adc", "current_A", "dac_z", "bias",
           "steps", "is_scanning", "is_const_current", "is_approaching"]


def _amps_to_adc(amps):
    """Amps -> integer ADC counts, saturating at the rail like the LTC2326."""
    counts = np.round(np.asarray(amps) / A_PER_COUNT)
    return np.clip(counts, -32768, ADC_RAIL).astype(int)


def generate(kind="noise", n=300, seed=0, cadence_ms=CADENCE_MS,
             bias_on=True, **overrides):
    """Build a synthetic session as a dict of parallel numpy arrays.

    Parameters shape the statistics stab_runner keys on.  All randomness is
    seeded, so a (kind, n, seed) triple is fully reproducible.

    overrides (per kind): mean_pA, sigma_pA, drift_pm_s, burst_nA,
    n_bursts, rail_frac.
    """
    rng = np.random.default_rng(seed)

    # Time base: near-uniform cadence with small realistic jitter, never <=0.
    jitter = rng.normal(0, cadence_ms * 0.03, n)
    dt = np.maximum(cadence_ms + jitter, 1.0)
    time_millis = (T0_MS + np.cumsum(dt)).astype(np.int64)
    elapsed_s = (time_millis - time_millis[0]) / 1000.0

    p = dict(mean_pA=-15.0, sigma_pA=38.0, drift_pm_s=0.0,
             burst_nA=6.0, n_bursts=8, rail_frac=0.4)
    p.update(overrides)
    pA, nA = 1e-12, 1e-9

    if kind == "noise":
        # Zero-ish mean amplifier floor; symmetric about a small offset.
        amps = rng.normal(p["mean_pA"] * pA, p["sigma_pA"] * pA, n)

    elif kind == "tunneling":
        # One-sided (all positive), signed mean well above the floor sigma.
        mean = overrides.get("mean_pA", 150.0) * pA
        sigma = overrides.get("sigma_pA", 30.0) * pA
        amps = np.abs(rng.normal(mean, sigma, n))
        if p["drift_pm_s"]:                       # optional gentle z-drift
            amps *= np.exp(-elapsed_s * p["drift_pm_s"] / 48.8 * 0.01)

    elif kind == "emi":
        # Floor + a handful of large bipolar, zero-mean excursion bursts.
        amps = rng.normal(p["mean_pA"] * pA, 30.0 * pA, n)
        idx = rng.choice(n, size=int(p["n_bursts"]), replace=False)
        signs = np.where(np.arange(idx.size) % 2 == 0, 1.0, -1.0)
        amps[idx] += signs * p["burst_nA"] * nA

    elif kind == "contact":
        # A leading run of railed samples (hard contact), then floor.
        amps = rng.normal(p["mean_pA"] * pA, 30.0 * pA, n)
        n_rail = int(n * p["rail_frac"])
        amps[:n_rail] = 102.4 * nA                # at the rail

    elif kind == "short":
        amps = rng.normal(0, 40.0 * pA, min(n, 16))
        n = amps.size
        time_millis, elapsed_s = time_millis[:n], elapsed_s[:n]

    else:
        raise ValueError(f"unknown kind {kind!r}")

    adc = _amps_to_adc(amps)
    bias_val = 30000 if bias_on else 0
    zeros = np.zeros(n, dtype=int)
    return {
        "elapsed_s": elapsed_s,
        "time_millis": time_millis,
        "adc": adc,
        "current_A": np.asarray(amps),
        "dac_z": zeros,
        "bias": np.full(n, bias_val),
        "steps": zeros,
        "is_scanning": zeros,
        "is_const_current": zeros,
        "is_approaching": zeros,
    }


def write_csv(path, data):
    """Write a generated session dict to a stability CSV (widget format)."""
    n = len(data["elapsed_s"])
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for i in range(n):
            w.writerow([
                f"{data['elapsed_s'][i]:.3f}",
                int(data["time_millis"][i]),
                int(data["adc"][i]),
                f"{data['current_A'][i]:.6e}",
                int(data["dac_z"][i]),
                int(data["bias"][i]),
                int(data["steps"][i]),
                int(data["is_scanning"][i]),
                int(data["is_const_current"][i]),
                int(data["is_approaching"][i]),
            ])


# (kind, overrides, expected stab_runner verdict) — the H3 fixture matrix.
PRESETS = {
    "tunneling": ({"kind": "tunneling"}, "TUNNELING_LIKE"),
    "noise":     ({"kind": "noise"}, "NOISE_ONLY"),
    "emi":       ({"kind": "emi"}, "EMI_CONTAMINATED"),
    "contact":   ({"kind": "contact"}, "CONTACT"),
    "short":     ({"kind": "short"}, "INSUFFICIENT"),
}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kind", default="noise", choices=list(PRESETS) + ["noise"])
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True, help="output CSV path")
    args = ap.parse_args(argv)
    write_csv(args.out, generate(kind=args.kind, n=args.n, seed=args.seed))
    print(f"[synth_source] wrote {args.kind} session -> {args.out}")


if __name__ == "__main__":
    main()

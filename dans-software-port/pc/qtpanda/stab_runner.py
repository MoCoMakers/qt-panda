"""stab_runner — automated stability-test agent (v0: verdict-only).

Grades a stability-session CSV (as written by widget.py's _open_stab_log)
against the acceptance criteria established in
documentation/docs-for-ai/StabilityResearch/
2026-07-02-first-contact-findings-and-pairing-proposal.md:

  * TUNNELING_LIKE     signed |mean| >= 3*sigma of the floor, unsaturated,
                       one-sided distribution — the record the pipeline wants.
  * CONTACT            ADC-railed samples present (hard tip-sample contact).
  * EMI_CONTAMINATED   bipolar, zero-mean excursion bursts (bench activity).
  * NOISE_ONLY         statistically identical to the electronics floor.
  * INSUFFICIENT       too short to judge.

Verdict-only mode is v0 of the runner proposed in that document; later
increments add live recording (v1) and guarded approach (v2) on top of the
same verdict logic.  Usage:

    python stab_runner.py --verdict-only <session.csv> [...] [--ledger PATH]

Exit code encodes the worst verdict across all inputs (0 TUNNELING_LIKE,
10 NOISE_ONLY, 11 CONTACT, 12 EMI_CONTAMINATED, 13 INSUFFICIENT, 2 bad input)
so wrappers/agents can branch without parsing text.  Per-file
`<name>_verdict.json` is written next to each CSV; --ledger appends one
JSON line per run to a session ledger.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime

import numpy as np

import stab_metrics

# ADC positive full scale: the LTC2326-16 reads +32767 when the preamp
# output is at/beyond +10.24 V (102.4 nA at 100 MOhm) — "railed".
ADC_RAIL = 32767

# Acceptance thresholds (see proposal doc, findings F2/F3/F5).
TUNNELING_MEAN_SIGMAS = 3.0     # signed |mean| must clear this many sigma
EMI_EXCURSION_SIGMAS = 5.0      # |I - offset| beyond this = excursion
EMI_MIN_EXCURSIONS = 5          # fewer than this is just tail samples
MIN_SAMPLES = 32
WORK_FUNCTION_EV = 4.0

EXIT_CODES = {
    "TUNNELING_LIKE": 0,
    "NOISE_ONLY": 10,
    "CONTACT": 11,
    "EMI_CONTAMINATED": 12,
    "INSUFFICIENT": 13,
}


def load_session(path):
    """Parse a stability CSV into a dict of numpy arrays (or None if
    unreadable/empty)."""
    cols = {k: [] for k in (
        "elapsed_s", "time_millis", "adc", "current_A", "bias", "steps")}
    try:
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                try:
                    vals = {k: float(row[k]) for k in cols}
                except (KeyError, ValueError):
                    continue
                for k, v in vals.items():
                    cols[k].append(v)
    except OSError as e:
        print(f"[stab_runner] cannot read {path}: {e}")
        return None
    if not cols["current_A"]:
        return None
    return {k: np.asarray(v) for k, v in cols.items()}


def started_at(path):
    """Recording start time from the epoch-ms suffix of the filename."""
    stem = os.path.basename(path).rsplit(".", 1)[0]
    try:
        return datetime.fromtimestamp(
            int(stem.split("_")[-1]) / 1000).isoformat(sep=" ")
    except (ValueError, OSError):
        return None


def analyze(path):
    """Grade one session CSV.  Returns the verdict dict."""
    v = {
        "file": os.path.abspath(path),
        "started": started_at(path),
        "analyzed": datetime.now().isoformat(sep=" ", timespec="seconds"),
        "verdict": "INSUFFICIENT",
        "flags": [],
    }
    d = load_session(path)
    if d is None or d["current_A"].size < MIN_SAMPLES:
        v["n"] = 0 if d is None else int(d["current_A"].size)
        v["flags"].append("too little data to judge")
        return v

    amps, adc, t = d["current_A"], d["adc"], d["elapsed_s"]
    n = amps.size
    dt = np.diff(d["time_millis"])
    v.update({
        "n": int(n),
        "span_s": float(t[-1] - t[0]),
        "cadence_ms_median": float(np.median(dt)) if dt.size else None,
        "polling_gaps_s": [float(g) / 1000 for g in dt[dt > 1000]],
        "bias_on": bool((d["bias"] != 0).any()),
        "motor_step_events": int((np.diff(d["steps"]) != 0).sum()),
    })
    if not v["bias_on"]:
        v["flags"].append(
            "bias=0 for entire recording - tunneling physically impossible")

    # ---- contact / rail --------------------------------------------------
    railed = adc >= ADC_RAIL
    rail_frac = float(railed.mean())
    v["rail_fraction"] = rail_frac
    if rail_frac > 0:
        # In/out transitions between railed and free.
        v["contact_transitions"] = [
            {"t_s": float(t[i + 1]),
             "direction": "release" if railed[i] else "contact"}
            for i in np.where(np.diff(railed.astype(int)) != 0)[0]
        ]
        v["flags"].append(
            f"{rail_frac:.0%} of samples at ADC full scale - contact depth "
            "unbounded (true current >= 102.4 nA)")

    # ---- floor statistics (non-railed samples) ---------------------------
    free = amps[~railed]
    if free.size < MIN_SAMPLES:
        v["verdict"] = "CONTACT"
        v["flags"].append("almost no free-tip samples to characterize")
        return v
    offset = float(np.median(free))
    mad_sigma = float(np.median(np.abs(free - offset))) * 1.4826
    sigma = mad_sigma if mad_sigma > 0 else float(free.std())
    v["floor"] = {
        "offset_pA": offset * 1e12,
        "sigma_pA": sigma * 1e12,
        "signed_mean_pA": float(free.mean()) * 1e12,
    }

    # ---- EMI: bipolar zero-mean excursion bursts (finding F5, run 3) -----
    exc = free[np.abs(free - offset) > EMI_EXCURSION_SIGMAS * sigma]
    emi = False
    if exc.size >= EMI_MIN_EXCURSIONS:
        both_signs = (exc > offset).any() and (exc < offset).any()
        zero_mean = abs(float(exc.mean() - offset)) < 0.5 * float(exc.std())
        emi = both_signs and zero_mean
        v["excursions"] = {
            "count": int(exc.size),
            "max_pA": float(np.abs(exc - offset).max()) * 1e12,
            "bipolar_zero_mean": emi,
        }
        if emi:
            v["flags"].append(
                "bipolar zero-mean excursion bursts - bench/EMI "
                "interference, not tip current")

    # ---- tunneling criterion (finding F3) --------------------------------
    mean_over_sigma = abs(float(free.mean())) / sigma if sigma > 0 else 0.0
    sd = float(free.std())
    skew = (float(np.mean(((free - free.mean()) / sd) ** 3))
            if sd > 0 else 0.0)
    v["criteria"] = {
        "signed_mean_over_sigma": mean_over_sigma,
        "required_sigmas": TUNNELING_MEAN_SIGMAS,
        "skew": skew,
        "unsaturated": rail_frac == 0.0,
        "bias_on": v["bias_on"],
    }

    # ---- derived metrics (only meaningful without contact steps) ---------
    if rail_frac == 0.0:
        pm = stab_metrics.pm_per_ln(WORK_FUNCTION_EV)
        v["drift"] = stab_metrics.drift_metrics(
            d["time_millis"], amps, pm)
        psd = stab_metrics.power_spectrum(d["time_millis"], amps)
        if psd is not None:
            v["psd"] = {k: psd[k] for k in (
                "peak_freq_hz", "peak_power", "peak_snr",
                "peak_snr_threshold", "peak_significant", "fs_hz")}
        allan = stab_metrics.allan_deviation(d["time_millis"], amps)
        if allan is not None:
            v["allan"] = {
                "slope": allan["slope"],
                "noise_type": stab_metrics.classify_allan_slope(
                    allan["slope"]),
                "tau_opt_s": allan["tau_opt_s"],
                "sigma_min_A": allan["sigma_min"],
                "sigma_min_pm": stab_metrics.sigma_to_pm(
                    allan["sigma_min"], float(free.mean()), pm),
            }

    # ---- verdict ----------------------------------------------------------
    if rail_frac > 0:
        v["verdict"] = "CONTACT"
    elif (v["bias_on"] and not emi
            and mean_over_sigma >= TUNNELING_MEAN_SIGMAS):
        v["verdict"] = "TUNNELING_LIKE"
    elif emi:
        v["verdict"] = "EMI_CONTAMINATED"
    else:
        v["verdict"] = "NOISE_ONLY"
    return v


def report(v):
    """One human-readable line per file, after the machine artifacts."""
    parts = [f'{v["verdict"]:16s}', os.path.basename(v["file"])]
    if v.get("started"):
        parts.append(f'@ {v["started"]}')
    if "floor" in v:
        f = v["floor"]
        parts.append(f'floor {f["sigma_pA"]:.0f} pA, '
                     f'mean/sigma={v["criteria"]["signed_mean_over_sigma"]:.2f}')
    if v.get("rail_fraction"):
        parts.append(f'rail {v["rail_fraction"]:.0%}, '
                     f'{len(v.get("contact_transitions", []))} transitions')
    print("  ".join(parts))
    for fl in v["flags"]:
        print(f"    ! {fl}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csvs", nargs="+", help="stability session CSV file(s)")
    ap.add_argument("--verdict-only", action="store_true",
                    help="v0 mode (currently the only mode)")
    ap.add_argument("--ledger", metavar="PATH",
                    help="append one JSON line per verdict to this file")
    ap.add_argument("--no-json", action="store_true",
                    help="don't write <name>_verdict.json next to the CSV")
    args = ap.parse_args(argv)

    worst = 0
    for path in args.csvs:
        v = analyze(path)
        report(v)
        if not args.no_json:
            out = os.path.splitext(v["file"])[0] + "_verdict.json"
            with open(out, "w") as f:
                json.dump(v, f, indent=2)
        if args.ledger:
            with open(args.ledger, "a") as f:
                f.write(json.dumps(v) + "\n")
        worst = max(worst, EXIT_CODES.get(v["verdict"], 2))
    return worst


if __name__ == "__main__":
    sys.exit(main())

"""Harness H3 core — known-answer checks, runnable with *only* numpy.

Pure/Qt-free and pytest-free so it runs directly in the software-mockup Docker
image (which has numpy but not pytest).  The pytest suite
(``tests/test_pipeline_fixtures.py``) imports these same functions, so the
docker harness and host CI check identical logic.

Run in docker:
    docker run --rm -v <host>/dans-software-port/pc/qtpanda:/work \\
        -v <host>/TeamUpdate/data:/data:ro -w /work \\
        -e QTPANDA_STAB_DATA=/data --entrypoint python \\
        software-mockup-pc:latest stab_fixtures.py
"""
import glob
import json
import os
import sys
import tempfile

import synth_source as ss
import stab_runner


def grade_synth(name, seed=0, n=300):
    """Generate one preset to a temp CSV and return (verdict_dict, expected)."""
    kw, expected = ss.PRESETS[name]
    fd, path = tempfile.mkstemp(
        suffix=f"_image_stability_{name}_1000000000000.csv")
    os.close(fd)
    try:
        ss.write_csv(path, ss.generate(seed=seed, n=n, **kw))
        return stab_runner.analyze(path), expected
    finally:
        os.unlink(path)


def check_synthetic():
    """List of (label, ok, detail) for every synthetic preset."""
    results = []
    for name in ss.PRESETS:
        v, expected = grade_synth(name)
        results.append((name, v["verdict"] == expected,
                        f'{v["verdict"]} (want {expected})'))
    return results


def real_pairs(data_dir):
    """(csv, verdict_json) pairs in data_dir that have a committed verdict."""
    if not data_dir or not os.path.isdir(data_dir):
        return []
    pairs = []
    for csv_path in sorted(glob.glob(os.path.join(data_dir, "*.csv"))):
        vj = os.path.splitext(csv_path)[0] + "_verdict.json"
        if os.path.exists(vj):
            pairs.append((csv_path, vj))
    return pairs


def check_real(data_dir):
    """Re-grade labelled bench CSVs and compare to their committed verdict."""
    results = []
    for csv_path, vj in real_pairs(data_dir):
        with open(vj) as f:
            expected = json.load(f)["verdict"]
        actual = stab_runner.analyze(csv_path)["verdict"]
        results.append((os.path.basename(csv_path), actual == expected,
                        f"{actual} (want {expected})"))
    return results


def main():
    allok = True
    print("== synthetic fixtures ==")
    for label, ok, detail in check_synthetic():
        allok &= ok
        print(f"  [{'OK' if ok else 'FAIL'}] {label:10s} {detail}")

    data_dir = os.environ.get("QTPANDA_STAB_DATA")
    real = check_real(data_dir)
    if data_dir and os.path.isdir(data_dir):
        print(f"== real bench sessions ({data_dir}) ==")
        if not real:
            print("  (no *_verdict.json pairs found)")
        for label, ok, detail in real:
            allok &= ok
            print(f"  [{'OK' if ok else 'FAIL'}] {label:40s} {detail}")
    else:
        print("== real bench sessions == (skipped; set QTPANDA_STAB_DATA)")

    print("\nALL PASS" if allok else "\nFAILURES PRESENT")
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()

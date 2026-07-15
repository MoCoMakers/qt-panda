"""Harness H3 (pytest wrapper) — pipeline regression against known answers.

The check logic lives in ``stab_fixtures`` (Qt-free, pytest-free) so the
Docker harness and this host suite validate identical code.  Two layers:

1. Synthetic presets — always run; deterministic, no external data.
2. Real bench sessions — opt-in via ``QTPANDA_STAB_DATA`` pointing at a dir of
   labelled CSVs with sibling ``*_verdict.json``; skipped when not mounted.
"""
import os

import pytest

import stab_fixtures
import synth_source as ss
import stab_runner


@pytest.mark.parametrize("name", list(ss.PRESETS))
def test_synthetic_preset_verdict(name):
    v, expected = stab_fixtures.grade_synth(name)
    assert v["verdict"] == expected, f"{name}: {v['verdict']} != {expected}"

    # Assert the property that actually drives each verdict, not just the label.
    if name == "tunneling":
        assert v["criteria"]["signed_mean_over_sigma"] >= \
            stab_runner.TUNNELING_MEAN_SIGMAS
        assert v["bias_on"] and v["rail_fraction"] == 0.0
    elif name == "noise":
        assert v["criteria"]["signed_mean_over_sigma"] < \
            stab_runner.TUNNELING_MEAN_SIGMAS
        assert v["rail_fraction"] == 0.0
    elif name == "emi":
        assert v["excursions"]["bipolar_zero_mean"] is True
    elif name == "contact":
        assert v["rail_fraction"] > 0.0


def test_synthetic_is_deterministic():
    a, _ = stab_fixtures.grade_synth("tunneling")
    b, _ = stab_fixtures.grade_synth("tunneling")
    assert a["floor"] == b["floor"]


_REAL = stab_fixtures.real_pairs(os.environ.get("QTPANDA_STAB_DATA"))


@pytest.mark.skipif(not _REAL, reason="QTPANDA_STAB_DATA not set / no fixtures")
@pytest.mark.parametrize("csv_path,verdict_json", _REAL)
def test_real_session_matches_committed_verdict(csv_path, verdict_json):
    import json
    with open(verdict_json) as f:
        expected = json.load(f)["verdict"]
    assert stab_runner.analyze(csv_path)["verdict"] == expected

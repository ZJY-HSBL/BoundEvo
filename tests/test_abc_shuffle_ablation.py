"""Ablation verification: no fabricated trials are published."""

import importlib.util
from pathlib import Path
from xml.etree import ElementTree

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/aggregate_abc_shuffle_ablation.py"
SPEC = importlib.util.spec_from_file_location("abc_shuffle_ablation", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def test_exact_sign_probability():
    assert analysis.sign_test(10, 0) == pytest.approx(2 / 1024)
    assert analysis.sign_test(5, 5) == 1
    assert analysis.sign_test(0, 0) == 1


def test_svg_is_valid_and_seed_effects_are_not_invented():
    effects = {fid: [0.02*(i-5) for i in range(10)] for fid in analysis.FUNCTIONS}
    tests = [
        {
            "function_id": fid, "shuffled_wins": 4, "shuffled_losses": 5,
            "mean_paired_log1p_gain": -0.01,
            "bootstrap_paired_ci95_low": -0.035,
            "bootstrap_paired_ci95_high": 0.025,
            "holm_sign_p": 1.0,
        }
        for fid in analysis.FUNCTIONS
    ]
    svg = analysis.render_svg(tests, effects)
    assert ElementTree.fromstring(svg).tag.endswith("svg")
    assert "80" not in svg
    assert "F10" in svg and "F22" in svg
    assert len(svg) > 3500

"""Unit tests of the coefficient-index mechanism; synthetic fixtures never become results."""

import importlib.util
from pathlib import Path
from xml.etree import ElementTree

import pytest

FILE = Path(__file__).resolve().parents[1] / "scripts/aggregate_abc_reverse_mechanism.py"
SPEC = importlib.util.spec_from_file_location("abc_reverse_analysis", FILE)
assert SPEC is not None and SPEC.loader is not None
study = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(study)


def test_exact_sign_and_holm_counts() -> None:
    assert study.exact_sign_p(12, 0) == pytest.approx(2/4096)
    assert study.exact_sign_p(6, 6) == 1
    assert study.exact_sign_p(0, 0) == 1


def test_three_arm_mechanism_svg_parses_with_controlled_test_fixture() -> None:
    comparisons = [
        {
            "function_id": fid, "contrast": f"{m}_vs_abc",
            "paired_mean_log1p_gain": 0.01,
            "bootstrap_ci95_low": -0.03,
            "bootstrap_ci95_high": 0.05,
            "holm_sign_p": 1.0,
        }
        for fid in study.FUNCTIONS for m in study.CONTROLS
    ]
    effects = [
        {
            "function_id": fid, "method": m, "repeat": seed,
            "paired_log1p_gain": (seed-6)*0.015,
        }
        for fid in study.FUNCTIONS for m in study.CONTROLS
        for seed in range(study.REPEATS)
    ]
    result = study.effects_svg(comparisons, effects)
    assert ElementTree.fromstring(result).tag.endswith("svg")
    assert "paired seed" in result.lower()
    assert "F22" in result


def test_coefficient_position_distribution_figure_and_sampling_integrity() -> None:
    from boundevo.coefficients import adaptive_boundary_coefficients, is_valid_coefficients
    import numpy as np

    rng = np.random.default_rng(study.AUDIT_SEED)
    for _ in range(300):
        record = adaptive_boundary_coefficients(15, rng)
        assert record.attempts == 1
        assert is_valid_coefficients(record.coefficients)
    diagnostic = [
        {
            "index": i, "mean_alpha": 0.05,
            "median_alpha": 0.04,
            "q25_alpha": -0.10,
            "q75_alpha": 0.16,
        }
        for i in range(1, 16)
    ]
    overview = {"mean_elite_share_absolute_mass": 0.3}
    svg = study.coefficient_svg(diagnostic, overview)
    assert ElementTree.fromstring(svg).tag.endswith("svg")
    assert "50,000" in svg

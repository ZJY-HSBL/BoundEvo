"""Regression gates for anytime research; synthetic values never enter published figures."""

import importlib.util
import math
from pathlib import Path
from xml.etree import ElementTree

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts/research_anytime_visuals.py"
SPEC = importlib.util.spec_from_file_location("anytime_research", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
study = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(study)


def test_log_budget_sample_and_hold_integral_is_exact():
    samples = [(10_000, 9.0), (100_000, 1.0)]
    assert study.anytime_loss(samples) == pytest.approx(math.log1p(9.0))
    points = [(10_000, 9.0), (math.isqrt(10_000*100_000), 8.0), (100_000, 1.0)]
    # Intermediate point is not necessarily on the geometric midpoint.
    expected = (
        math.log1p(9) * math.log(points[1][0] / 10_000)
        + math.log1p(8) * math.log(100_000 / points[1][0])
    ) / math.log(10)
    assert study.anytime_loss(points) == pytest.approx(expected)
    with pytest.raises(ValueError):
        study.anytime_loss([(10_000, 10.0), (50_000, 11.0), (100_000, 9.0)])


def test_quantile_sign_and_svg_markup():
    assert study.quantile([1, 2, 3, 4, 5], 0.25) == 2
    assert study.quantile([1, 2, 3, 4], 0.5) == 2.5
    assert study.sign_p(20, 0) == pytest.approx(2/(2**20))
    assert study.sign_p(10, 10) == 1.0
    sample = study.svg_start(300, 180, "Research & Accuracy", "30D")
    assert ElementTree.fromstring("\n".join(sample + ["</svg>"])).tag.endswith("svg")


def test_original_100k_data_reconciled_and_real_figures_parse():
    index, traces, steps = study.verify()
    assert len(index) == 120
    assert len(traces) == 120
    assert len(steps) == 112
    assert steps[0] == 100 and steps[-1] == 100_000
    summary, tests, profiles = study.analyse(index, traces, steps)
    assert len(summary) == 6 and len(tests) == 4 and len(profiles) == 60
    assert all(0 <= float(row["attainment_fraction"]) <= 1 for row in profiles)
    for fig in (
        study.svg_ribbons(traces, steps),
        study.svg_paired(index),
        study.svg_ecdf(profiles),
        study.svg_auc(tests),
    ):
        assert ElementTree.fromstring(fig).tag.endswith("svg")
        assert len(fig) > 3000

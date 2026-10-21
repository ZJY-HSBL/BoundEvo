"""Regression gates for full-function CEC2017 inference and measured-data figure code."""

import importlib.util
from pathlib import Path
from xml.etree import ElementTree

import numpy as np
import pytest

FILE = Path(__file__).resolve().parents[1] / "scripts/aggregate_fullsuite_de.py"
SPEC = importlib.util.spec_from_file_location("full_suite_inference", FILE)
assert SPEC is not None and SPEC.loader is not None
study = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(study)


def test_full_suite_covers_exact_official_29_function_ids() -> None:
    from boundevo.cec2017 import PAPER_FUNCTION_IDS

    assert study.FUNCTIONS == tuple(PAPER_FUNCTION_IDS)
    assert len(study.FUNCTIONS) == 29
    assert set(study.FUNCTIONS) == {1, *range(3, 31)}
    assert [fid for chunk in study.SIX_SHARDS for fid in chunk] == list(study.FUNCTIONS)
    assert study.REPEATS == 5 and study.BUDGET == 10000


def test_exact_function_sign_and_tied_ranks() -> None:
    assert study.exact_sign_test(29, 0) == pytest.approx(2/2**29)
    assert study.exact_sign_test(14, 15) == 1
    assert study.rank3([1.0, 2.0, 3.0]) == [1.0, 2.0, 3.0]
    assert study.rank3([2.0, 2.0, 1.0]) == [2.5, 2.5, 1.0]
    assert study.rank3([7.0, 7.0, 7.0]) == [2.0, 2.0, 2.0]
    assert study.friedman_statistic(np.ones((3, 3))*2) == pytest.approx(0.0)
    q = study.friedman_statistic(np.tile([1.0, 2.0, 3.0], (29, 1)))
    assert q == pytest.approx(58.0)


def test_data_derived_figures_can_render_valid_xml() -> None:
    rank_rows = []
    for fid in study.FUNCTIONS:
        for idx, method in enumerate(study.METHODS):
            rank_rows.append({
                "function_id": fid,
                "method": method,
                "rank": idx+1,
                "relative_to_function_best": float(idx+1),
            })
    stats = {
        "function_block_mean_ranks": dict(zip(study.METHODS, [1., 2., 3.])),
        "function_best_mean_error_counts": dict(zip(study.METHODS, [29, 0, 0])),
        "friedman_rank_statistic": 58.,
        "permutation_p": 0.00005,
    }
    tests = []
    heatmap = study.heatmap_svg(rank_rows)
    ranks_svg = study.ranks_svg(stats, tests)
    for svg in (heatmap, ranks_svg):
        assert ElementTree.fromstring(svg).tag.endswith("svg")
        assert "F30" in heatmap and "ABC" in ranks_svg

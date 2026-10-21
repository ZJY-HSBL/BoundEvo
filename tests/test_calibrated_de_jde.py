"""Scientific regression tests: calibration/evaluation separation and inference helpers.

All SVG fixtures here are synthetic test-only records and are never published
to docs/experiments or docs/figures.
"""

import importlib.util
import sys
from pathlib import Path
from xml.etree import ElementTree

import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
SCRIPT = SCRIPTS/"aggregate_calibrated_de_jde.py"
SPEC = importlib.util.spec_from_file_location("calibrated_de_jde_stats",SCRIPT)
assert SPEC is not None and SPEC.loader is not None
analysis=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def test_frozen_calibration_holdout_functions_and_disjoint_seed_cohorts() -> None:
    from boundevo.cec2017 import PAPER_FUNCTION_IDS
    from run_tuned_de_jde import (
        CANDIDATES,DEV_FUNCTIONS,DEV_SEED,TEST_FUNCTIONS,TEST_SEED,
        TEST_SHARDS,
    )

    assert len(CANDIDATES)==6
    assert DEV_FUNCTIONS==(3,10,20,30)
    assert not set(DEV_FUNCTIONS)&set(TEST_FUNCTIONS)
    assert set(DEV_FUNCTIONS)|set(TEST_FUNCTIONS)==set(PAPER_FUNCTION_IDS)
    assert len(TEST_FUNCTIONS)==25
    assert len(TEST_SHARDS)==5 and all(len(x)==5 for x in TEST_SHARDS)
    assert [fid for shard in TEST_SHARDS for fid in shard]==list(TEST_FUNCTIONS)
    dev_seeds={DEV_SEED+10000*fid+i for fid in DEV_FUNCTIONS for i in range(3)}
    test_seeds={TEST_SEED+10000*fid+i for fid in TEST_FUNCTIONS for i in range(10)}
    assert not dev_seeds&test_seeds


def test_exact_sign_and_tied_function_rank_statistics() -> None:
    assert analysis.sign(25,0)==pytest.approx(2/2**25)
    assert analysis.sign(12,13)==pytest.approx(1.)
    assert analysis.sign(0,0)==1
    assert analysis.midrank3([4,1,4])==[2.5,1.,2.5]
    assert analysis.midrank3([1,1,1])==[2.,2.,2.]
    assert analysis.friedman(np.tile([2.,2.,2.],(25,1)))==0
    assert analysis.friedman(np.tile([1.,2.,3.],(25,1)))==pytest.approx(50.)


def test_calibration_and_evaluation_original_data_figures_parse() -> None:
    board=[
        {"candidate_id":candidate,
         "average_development_function_rank":rank}
        for candidate,rank in zip(
            ("rand050cr090","rand080cr030","rand080cr090",
             "best050cr090","best080cr030","best080cr090"),
            (1.,3.,4.,5.,2.,6.)
        )
    ]
    choice={"selected":"rand050cr090"}
    svg=analysis.calibration_svg(board,choice)
    assert ElementTree.fromstring(svg).tag.endswith("svg")
    assert "SELECTED" in svg

    rank_rows=[
        {"function_id":fid,"method":method,
         "relative_to_function_best":float(index+1)}
        for fid in analysis.TEST_FUNCTIONS
        for index,method in enumerate(analysis.METHODS)
    ]
    svg=analysis.error_heatmap(rank_rows)
    assert ElementTree.fromstring(svg).tag.endswith("svg")
    assert "F29" in svg

    stats={
        "mean_function_ranks":dict(zip(analysis.METHODS,(1.,2.,3.))),
        "function_winner_counts":dict(zip(analysis.METHODS,(25,0,0))),
        "friedman_statistic":50.,"permutation_p":0.0001,
    }
    svg=analysis.ranking_svg(stats,[])
    assert ElementTree.fromstring(svg).tag.endswith("svg")
    assert "jDE" in svg or "JDE" in svg

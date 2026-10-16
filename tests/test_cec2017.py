import pytest

from boundevo.cec2017 import PAPER_FUNCTION_IDS, _benchmark_class_name, validate_function_ids
from boundevo.experiments import TrialRecord, paper_config, summarize


def test_paper_function_set_contains_29_functions_without_f2() -> None:
    assert len(PAPER_FUNCTION_IDS) == 29
    assert PAPER_FUNCTION_IDS[0] == 1
    assert 2 not in PAPER_FUNCTION_IDS
    assert PAPER_FUNCTION_IDS[-1] == 30


def test_function_class_name() -> None:
    assert _benchmark_class_name(1) == "F12017"
    assert _benchmark_class_name(3) == "F22017"
    assert _benchmark_class_name(10) == "F92017"
    assert _benchmark_class_name(30) == "F292017"
    with pytest.raises(ValueError):
        _benchmark_class_name(0)


def test_validate_function_ids() -> None:
    assert validate_function_ids([1, 3, 30]) == (1, 3, 30)
    with pytest.raises(ValueError):
        validate_function_ids([])
    with pytest.raises(ValueError):
        validate_function_ids([31])
    with pytest.raises(ValueError):
        validate_function_ids([2])


def test_official_opfunu_mapping_and_bias() -> None:
    pytest.importorskip("opfunu")
    from boundevo.cec2017 import make_cec2017_case

    # F30 class mapping is verifiable, but opfunu 1.0.1 can return NaN at
    # certain points and therefore is not included in the finite pilot.
    for fid in (1, 3, 10, 20, 30):
        case = make_cec2017_case(fid, 10)
        assert case.function_id == fid
        assert case.name.startswith(f"F{fid}:")
        assert case.optimum == pytest.approx(100.0 * fid)
        assert case.problem.dimension == 10
        if fid != 30:
            assert case.problem.evaluate(case.problem.lower * 0.0).objective >= 0


def test_paper_config() -> None:
    config = paper_config(method="abc", max_evaluations=100_000, seed=7)
    assert config.population_size == 100
    assert config.parent_count == 15
    assert config.elite_parent_count == 5
    assert config.offspring_count == 1
    assert config.max_evaluations == 100_000
    assert config.coefficient_method == "abc"
    assert config.seed == 7


def test_summarize_groups_trials() -> None:
    records = [
        TrialRecord(1, "F1", 10, "abc", 0, 1, 101.0, 100.0, 1.0, 0.0, 100, 5, 5, 0.1, True),
        TrialRecord(1, "F1", 10, "abc", 1, 2, 103.0, 100.0, 3.0, 0.0, 120, 6, 6, 0.3, False),
    ]
    row = summarize(records)[0]
    assert row.trials == 2
    assert row.best_objective == 101.0
    assert row.mean_objective == 102.0
    assert row.mean_error == 2.0
    assert row.median_error == 2.0
    assert row.mean_evaluations == 110.0
    assert row.mean_elapsed_seconds == pytest.approx(0.2)
    assert row.convergence_rate == 0.5

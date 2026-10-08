from pathlib import Path

import pytest

from boundevo.efficiency import estimate_efficiency
from boundevo.sweep import (
    PAPER_PARENT_COUNTS,
    PAPER_SWEEP_FUNCTION_IDS,
    ParentSweepTrial,
    render_source_style_tables,
    summarize_parent_sweep,
    sweep_config,
    write_source_style_tables,
)


def test_source_aligned_sweep_constants() -> None:
    assert PAPER_PARENT_COUNTS == (10, 11, 12, 13, 14, 15, 16)
    assert PAPER_SWEEP_FUNCTION_IDS == (1, 10, 20, 30)


def test_sweep_config_varies_only_parent_count() -> None:
    config = sweep_config(12, method="abc", max_evaluations=1234, seed=7)
    assert config.population_size == 100
    assert config.parent_count == 12
    assert config.elite_parent_count == 5
    assert config.offspring_count == 1
    assert config.max_evaluations == 1234
    assert config.coefficient_method == "abc"
    assert config.seed == 7


def test_sweep_config_rejects_invalid_parent_count() -> None:
    with pytest.raises(ValueError):
        sweep_config(4)
    with pytest.raises(ValueError):
        sweep_config(101)


def test_parent_sweep_summary_and_source_style_table(tmp_path: Path) -> None:
    records = [
        ParentSweepTrial(
            1, "F1", 10, 10, "abc", 0, 1, 101.0, 100.0, 1.0,
            1000, 10, 10, 0.2, True
        ),
        ParentSweepTrial(
            1, "F1", 10, 10, "abc", 1, 2, 103.0, 100.0, 3.0,
            1200, 12, 12, 0.4, False
        ),
    ]
    row = summarize_parent_sweep(records)[0]
    assert row.parent_count == 10
    assert row.best_objective == 101.0
    assert row.best_error == 1.0
    assert row.mean_objective == 102.0
    assert row.mean_error == 2.0
    assert row.mean_evaluations == 1100.0
    assert row.mean_elapsed_seconds == pytest.approx(0.3)
    assert row.convergence_rate == 0.5

    rendered = render_source_style_tables([row])
    assert "## F1" in rendered
    assert "EP-GTA" not in rendered
    assert "BoundEvo (ABC)" in rendered
    assert "Mean runtime (s)" in rendered

    output = tmp_path / "tables.md"
    write_source_style_tables(output, [row])
    assert output.read_text(encoding="utf-8") == rendered


def test_abc_efficiency_is_exact() -> None:
    point = estimate_efficiency(20, method="abc", trials=1000)
    assert point.accepted == 1000
    assert point.efficiency == 1.0


@pytest.mark.parametrize("method", ["re", "edbf"])
def test_estimated_efficiency_is_a_probability(method: str) -> None:
    point = estimate_efficiency(
        5,
        method=method,
        trials=5000,
        seed=123,
        batch_size=1000,
    )
    assert 0 <= point.accepted <= point.trials
    assert 0.0 <= point.efficiency <= 1.0

"""README scientific figures must be reproducible from actual experiment CSVs."""

import importlib.util
from pathlib import Path
from xml.etree import ElementTree

_SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "update_readme_results.py"
_SPEC = importlib.util.spec_from_file_location("readme_evidence_generator", _SOURCE)
assert _SPEC is not None and _SPEC.loader is not None
_SCRIPT = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_SCRIPT)

evidence_ratio_svg = _SCRIPT.evidence_ratio_svg
parse_data = _SCRIPT.parse_data
runtime_svg = _SCRIPT.runtime_svg
screen_winners = _SCRIPT.screen_winners
screening_svg = _SCRIPT.screening_svg


def test_main_figures_parse_as_svg_and_reflect_actual_experiment() -> None:
    _directory, environment, summary, _pilot = parse_data()
    assert environment["dimension"] == 30
    assert environment["repeats"] == 10
    assert environment["evaluations"] == 3000
    assert len(summary) == 12

    for figure in (evidence_ratio_svg(summary, environment), runtime_svg(summary, environment)):
        svg = ElementTree.fromstring(figure)
        assert svg.tag.endswith("svg")
        assert "F10" in figure
        assert "F30" in figure
        assert "3,000" in figure


def test_screening_winners_and_svg_are_computed_from_source_metrics() -> None:
    functions = [1, *range(3, 31)]
    environment = {
        "functions": functions,
        "dimension": 30,
        "repeats": 3,
        "evaluations": 1200,
    }
    rows = []
    for index, function_id in enumerate(functions):
        winner = ("abc", "edbf", "re")[index % 3]
        for method in ("abc", "edbf", "re"):
            rows.append(
                {
                    "function_id": function_id,
                    "method": method,
                    "mean_error": 0.2 if method == winner else 5.0,
                    "repeats": 3,
                }
            )

    winners, counts = screen_winners(environment, rows)
    assert len(winners) == 29
    assert sum(counts.values()) == 29
    assert counts == {"abc": 10, "edbf": 10, "re": 9, "tie": 0}
    figure = screening_svg(environment, rows)
    assert ElementTree.fromstring(figure).tag.endswith("svg")
    assert "F30" in figure
    assert "29-function screening" in figure


def test_log_plot_auto_scales_genuine_large_improvements() -> None:
    # These are synthetic *unit-test fixtures*, not published experiment data.
    environment = {"functions": [10, 20, 22, 30], "dimension": 30, "repeats": 10, "evaluations": 10000}
    rows = []
    for fid in environment["functions"]:
        for method, error in (("abc", 0.000001), ("edbf", 0.01), ("re", 1.0)):
            rows.append({"function_id": fid, "method": method, "mean_error": error})
    svg = evidence_ratio_svg(rows, environment)
    assert ElementTree.fromstring(svg).tag.endswith("svg")
    assert "10,000" in svg


def test_longbudget_section_preserves_separate_budgets() -> None:
    environment = {"functions": [10, 20, 22, 30], "dimension": 30, "repeats": 10, "evaluations": 10000}
    previous = {"functions": [1, 3, 10, 30], "dimension": 30, "repeats": 10, "evaluations": 3000}
    data = []
    prior_data = []
    trials = []
    for fid in environment["functions"]:
        for method, error in (("abc", 1.0), ("edbf", 2.0), ("re", 3.0)):
            data.append({"function_id": fid, "method": method, "mean_error": error})
            if fid in (10, 30):
                prior_data.append({"function_id": fid, "method": method, "mean_error": error * 10})
            for rep in range(10):
                trials.append({"function_id": fid, "method": method, "repeat": rep, "error": error})
    folder = _SCRIPT.ROOT / "docs" / "experiments" / "synthetic-test-placeholder"
    cn = _SCRIPT.longbudget_markdown(folder, environment, data, trials, "cn", previous, prior_data)
    assert "10,000" in cn
    assert "3,000" in cn
    assert "F20" in cn and "F22" in cn
    assert "F10" in cn and "F30" in cn
    assert "vs EDBF 40/40" in cn
    assert "not" not in cn

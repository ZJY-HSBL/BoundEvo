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

import json
from pathlib import Path

import pytest

from boundevo.cli import build_parser
from boundevo.config import int_selection, load_json_config, string_selection


def test_json_config_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"dimension": 10}), encoding="utf-8")
    assert load_json_config(path) == {"dimension": 10}


def test_integer_selection_supports_ranges_and_preset() -> None:
    assert int_selection("10-12,15", preset=(1, 2)) == (10, 11, 12, 15)
    assert int_selection("paper", preset=(1, 3, 4)) == (1, 3, 4)
    assert int_selection([1, 10, 20], preset=(2,)) == (1, 10, 20)


def test_string_selection() -> None:
    assert string_selection("re,edbf,abc", default=("abc",)) == ("re", "edbf", "abc")
    assert string_selection(["abc"], default=("re",)) == ("abc",)


def test_cli_subcommands_parse() -> None:
    parser = build_parser()
    assert parser.parse_args(["benchmark"]).command == "benchmark"
    assert parser.parse_args(["sweep"]).command == "sweep"
    assert parser.parse_args(["efficiency"]).command == "efficiency"
    assert parser.parse_args(["analyze"]).command == "analyze"
    assert parser.parse_args(["report"]).command == "report"
    assert parser.parse_args(["pipeline"]).command == "pipeline"


def test_integer_selection_rejects_empty() -> None:
    with pytest.raises(ValueError):
        int_selection("", preset=(1,))

from datetime import datetime, timezone
from pathlib import Path

import pytest

from boundevo.runs import create_run_directory, generate_run_id, validate_run_id


def test_generate_run_id_is_stable_with_explicit_time_and_token() -> None:
    run_id = generate_run_id(
        "Experiment",
        now=datetime(2026, 10, 8, 15, 0, tzinfo=timezone.utc),
        token="ABC12345",
    )
    assert run_id == "experiment-20261008T150000Z-abc12345"


def test_validate_run_id_rejects_path_separators() -> None:
    with pytest.raises(ValueError):
        validate_run_id("../bad")


def test_create_run_directory_does_not_overwrite(tmp_path: Path) -> None:
    run = create_run_directory(kind="test", root=tmp_path, run_id="test-run")
    assert run.path == tmp_path / "test-run"
    assert run.path.is_dir()
    assert run.file("benchmark", "summary.csv") == run.path / "benchmark" / "summary.csv"

    with pytest.raises(FileExistsError):
        create_run_directory(kind="test", root=tmp_path, run_id="test-run")

import json
from pathlib import Path

from boundevo import __version__
from boundevo.reproducibility import capture_manifest, write_manifest


def test_capture_and_write_manifest(tmp_path: Path) -> None:
    manifest = capture_manifest(
        command="benchmark",
        config={"dimension": 10, "methods": ("abc", "edbf")},
        outputs={"summary": tmp_path / "summary.csv"},
    )
    assert manifest.schema_version == 1
    assert manifest.command == "benchmark"
    assert manifest.boundevo_version == __version__
    assert manifest.python_version
    assert "numpy" in manifest.dependencies
    assert manifest.config["methods"] == ["abc", "edbf"]

    path = tmp_path / "manifest.json"
    write_manifest(path, manifest)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["command"] == "benchmark"
    assert payload["config"]["dimension"] == 10
    assert payload["outputs"]["summary"].endswith("summary.csv")

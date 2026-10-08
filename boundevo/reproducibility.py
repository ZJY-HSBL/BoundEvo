"""Reproducibility metadata for BoundEvo experiment runs."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from . import __version__


@dataclass(frozen=True, slots=True)
class RunManifest:
    schema_version: int
    created_at_utc: str
    command: str
    run_id: str | None
    boundevo_version: str
    python_version: str
    python_executable: str
    platform: str
    source_revision: str | None
    dependencies: dict[str, str | None]
    config: dict[str, Any]
    outputs: dict[str, str]


def _package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _git_revision() -> str | None:
    github_sha = os.environ.get("GITHUB_SHA")
    if github_sha:
        return github_sha
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    revision = result.stdout.strip()
    return revision or None


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def capture_manifest(
    *,
    command: str,
    config: dict[str, Any],
    outputs: dict[str, str | Path],
    run_id: str | None = None,
) -> RunManifest:
    """Capture the resolved run configuration and execution environment."""

    dependencies = {
        name: _package_version(name)
        for name in ("numpy", "scipy", "opfunu", "matplotlib")
    }
    return RunManifest(
        schema_version=1,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        command=command,
        run_id=run_id,
        boundevo_version=__version__,
        python_version=platform.python_version(),
        python_executable=sys.executable,
        platform=platform.platform(),
        source_revision=_git_revision(),
        dependencies=dependencies,
        config=_jsonable(config),
        outputs={key: str(value) for key, value in outputs.items()},
    )


def write_manifest(path: str | Path, manifest: RunManifest) -> None:
    """Write a stable, human-readable JSON run manifest."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        json.dump(asdict(manifest), handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")

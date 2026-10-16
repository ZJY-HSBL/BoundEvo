"""Read-only discovery of managed BoundEvo experiment directories.

A registry is derived from on-disk run bundles. No database or mutable central
index is required. Only fixed relative paths are read; manifest output paths are
not followed.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RunEntry:
    run_id: str
    directory: Path
    status: str
    created_at_utc: str | None
    version: str | None
    dimension: int | None
    methods: tuple[str, ...]
    function_ids: tuple[int, ...]
    evaluation_budget: int | None
    repeats: int | None
    platform: str | None
    source_revision: str | None
    issues: tuple[str, ...]

    def to_dict(self) -> dict:
        record = asdict(self)
        record["directory"] = str(self.directory)
        return record


@dataclass(frozen=True, slots=True)
class BenchmarkMetric:
    case: tuple[int, int, str]
    mean_error: float
    mean_elapsed_seconds: float
    mean_evaluations: float


def _integer(value: object) -> int | None:
    try:
        return None if value is None else int(value)
    except (ValueError, TypeError):
        return None


def _integer_tuple(value: object) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    result = [_integer(item) for item in value]
    return tuple(item for item in result if item is not None)


def scan_runs(root: str | Path = "results/runs") -> list[RunEntry]:
    """Discover completed, incomplete, and invalid experiment run bundles."""

    path = Path(root)
    if not path.exists():
        return []
    if not path.is_dir():
        raise ValueError(f"run root is not a directory: {path}")

    entries: list[RunEntry] = []
    for directory in sorted(path.iterdir()):
        if not directory.is_dir() or directory.is_symlink():
            continue
        manifest_path = directory / "manifest.json"
        issues: list[str] = []
        payload: dict = {}
        if not manifest_path.is_file():
            issues.append("root manifest is missing")
        else:
            try:
                with manifest_path.open(encoding="utf-8") as handle:
                    raw = json.load(handle)
                if not isinstance(raw, dict):
                    raise TypeError("root manifest must be an object")
                payload = raw
            except (TypeError, ValueError, OSError) as exc:
                issues.append(f"invalid root manifest: {exc}")

        if payload and payload.get("run_id") != directory.name:
            issues.append("manifest run_id does not match the directory name")
        config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
        summary_path = directory / "benchmark" / "summary.csv"
        report_path = directory / "report" / "report.html"
        if not summary_path.is_file():
            issues.append("benchmark/summary.csv is missing")
        if not report_path.is_file():
            issues.append("report/report.html is missing")

        invalid = any(
            issue.startswith(("invalid root manifest", "manifest run_id does not match"))
            for issue in issues
        )
        status = "invalid" if invalid else ("complete" if not issues else "incomplete")
        methods_value = config.get("methods")
        methods = (
            tuple(str(item) for item in methods_value)
            if isinstance(methods_value, (list, tuple))
            else ()
        )
        entries.append(
            RunEntry(
                run_id=directory.name,
                directory=directory,
                status=status,
                created_at_utc=payload.get("created_at_utc"),
                version=payload.get("boundevo_version"),
                dimension=_integer(config.get("dimension")),
                methods=methods,
                function_ids=_integer_tuple(config.get("function_ids")),
                evaluation_budget=_integer(config.get("max_evaluations")),
                repeats=_integer(config.get("repeats")),
                platform=payload.get("platform"),
                source_revision=payload.get("source_revision"),
                issues=tuple(issues),
            )
        )
    return entries


def read_benchmark_metrics(run: RunEntry) -> dict[tuple[int, int, str], BenchmarkMetric]:
    """Read validated per-function, per-method summary rows from one run."""

    if run.status != "complete":
        raise ValueError(f"run {run.run_id!r} is not complete ({run.status})")
    summary = run.directory / "benchmark" / "summary.csv"
    rows: dict[tuple[int, int, str], BenchmarkMetric] = {}
    with summary.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {
            "function_id",
            "dimension",
            "method",
            "mean_error",
            "mean_elapsed_seconds",
            "mean_evaluations",
        }
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"run {run.run_id!r} lacks columns {sorted(missing)}")
        for row in reader:
            try:
                key = (int(row["function_id"]), int(row["dimension"]), row["method"])
                values = (
                    float(row["mean_error"]),
                    float(row["mean_elapsed_seconds"]),
                    float(row["mean_evaluations"]),
                )
            except (TypeError, ValueError, KeyError) as exc:
                raise ValueError(f"invalid summary row in run {run.run_id!r}") from exc
            if not key[2] or any(not math.isfinite(value) or value < 0 for value in values):
                raise ValueError(f"invalid metric values in run {run.run_id!r}")
            if key in rows:
                raise ValueError(f"duplicate benchmark case {key!r} in run {run.run_id!r}")
            rows[key] = BenchmarkMetric(key, *values)
    if not rows:
        raise ValueError(f"run {run.run_id!r} has no benchmark summary rows")
    return rows

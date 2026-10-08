"""Managed experiment run directories and unique run identifiers."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


@dataclass(frozen=True, slots=True)
class RunDirectory:
    run_id: str
    path: Path

    def file(self, *parts: str) -> Path:
        return self.path.joinpath(*parts)


def generate_run_id(
    kind: str,
    *,
    now: datetime | None = None,
    token: str | None = None,
) -> str:
    """Generate a compact run id such as benchmark-20261008T150000Z-a1b2c3d4."""

    safe_kind = re.sub(r"[^A-Za-z0-9_-]+", "-", kind.strip()).strip("-").lower()
    if not safe_kind:
        raise ValueError("run kind must contain at least one alphanumeric character")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    stamp = current.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = (token or uuid.uuid4().hex[:8]).strip().lower()
    suffix = re.sub(r"[^a-z0-9]+", "", suffix)[:12]
    if not suffix:
        raise ValueError("run token must contain an alphanumeric character")
    return f"{safe_kind}-{stamp}-{suffix}"


def validate_run_id(run_id: str) -> str:
    """Validate a run id before using it as a directory name."""

    if not _SAFE_RUN_ID.fullmatch(run_id):
        raise ValueError(
            "run_id must be 1-128 characters and contain only letters, numbers, '.', '_', or '-'"
        )
    return run_id


def create_run_directory(
    *,
    kind: str,
    root: str | Path = "results/runs",
    run_id: str | None = None,
) -> RunDirectory:
    """Create a new non-overwriting experiment directory."""

    resolved_id = validate_run_id(run_id) if run_id is not None else generate_run_id(kind)
    path = Path(root) / resolved_id
    path.mkdir(parents=True, exist_ok=False)
    return RunDirectory(resolved_id, path)

"""Small JSON configuration helpers used by the command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_config(path: str | Path | None) -> dict[str, Any]:
    """Load a JSON object from path, or return an empty mapping when omitted."""

    if path is None:
        return {}
    config_path = Path(path)
    with config_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"configuration root must be a JSON object: {config_path}")
    return payload


def int_selection(
    value: object,
    *,
    preset: tuple[int, ...],
    preset_name: str = "paper",
) -> tuple[int, ...]:
    """Resolve an integer list, a comma/range string, or a named preset."""

    if value is None:
        return preset
    if isinstance(value, str):
        text_value = value.strip().lower()
        if text_value == preset_name:
            return preset
        values: list[int] = []
        for token in text_value.split(","):
            token = token.strip()
            if not token:
                continue
            if "-" in token:
                start_text, end_text = token.split("-", maxsplit=1)
                start, end = int(start_text), int(end_text)
                step = 1 if end >= start else -1
                values.extend(range(start, end + step, step))
            else:
                values.append(int(token))
        if not values:
            raise ValueError("integer selection cannot be empty")
        return tuple(values)
    if isinstance(value, list):
        if not value:
            raise ValueError("integer selection cannot be empty")
        return tuple(int(item) for item in value)
    raise TypeError(f"unsupported integer selection: {value!r}")


def string_selection(value: object, *, default: tuple[str, ...]) -> tuple[str, ...]:
    """Resolve a string list from JSON configuration."""

    if value is None:
        return default
    if isinstance(value, str):
        values = tuple(token.strip() for token in value.split(",") if token.strip())
    elif isinstance(value, list):
        values = tuple(str(item) for item in value)
    else:
        raise TypeError(f"unsupported string selection: {value!r}")
    if not values:
        raise ValueError("string selection cannot be empty")
    return values

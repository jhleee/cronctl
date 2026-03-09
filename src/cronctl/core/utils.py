from __future__ import annotations

import os
import random
import re
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

_BOOL_TRUE = {"1", "true", "yes", "on"}
_BOOL_FALSE = {"0", "false", "no", "off"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso8601(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def from_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def generate_run_id(now: datetime | None = None) -> str:
    ts = (now or utc_now()).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    rand = "".join(random.choice("0123456789ABCDEFGHJKMNPQRSTVWXYZ") for _ in range(8))
    return f"{ts}-{rand}"


def tail_lines(text: str, limit: int) -> tuple[str, bool]:
    if limit <= 0:
        return "", bool(text)
    lines = text.splitlines()
    if len(lines) <= limit:
        return text, False
    return "\n".join(lines[-limit:]), True


def safe_load_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def safe_dump_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            data,
            handle,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=False,
        )


def expand_path(value: str | os.PathLike[str]) -> Path:
    return Path(value).expanduser().resolve()


def shell_quote(value: str) -> str:
    return shlex.quote(value)


def shell_join(parts: list[str]) -> str:
    return " ".join(shell_quote(part) for part in parts)


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in _BOOL_TRUE:
        return True
    if normalized in _BOOL_FALSE:
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def parse_scalar(value: str) -> Any:
    stripped = value.strip()
    if stripped.lower() in _BOOL_TRUE | _BOOL_FALSE:
        return parse_bool(stripped)
    if re.fullmatch(r"-?\d+", stripped):
        return int(stripped)
    if stripped == "null":
        return None
    return stripped

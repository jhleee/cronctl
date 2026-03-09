from __future__ import annotations

from pathlib import Path


def template_path() -> Path:
    return Path(__file__).with_name("SKILL.md")

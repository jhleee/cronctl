from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from cronctl.core.models import AppConfig
from cronctl.core.utils import safe_dump_yaml, safe_load_yaml


@dataclass(frozen=True)
class AppPaths:
    home: Path

    @property
    def config_path(self) -> Path:
        return self.home / "config.yaml"

    @property
    def jobs_dir(self) -> Path:
        return self.home / "jobs"

    @property
    def scripts_dir(self) -> Path:
        return self.home / "scripts"

    @property
    def hooks_dir(self) -> Path:
        return self.home / "hooks"

    @property
    def logs_dir(self) -> Path:
        return self.home / "logs"

    @property
    def db_path(self) -> Path:
        return self.logs_dir / "cronctl.db"


def build_paths(home: str | Path) -> AppPaths:
    return AppPaths(Path(home).expanduser())


def ensure_home(paths: AppPaths) -> None:
    paths.home.mkdir(parents=True, exist_ok=True)
    paths.jobs_dir.mkdir(parents=True, exist_ok=True)
    paths.scripts_dir.mkdir(parents=True, exist_ok=True)
    paths.hooks_dir.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)


def load_config(paths: AppPaths) -> AppConfig:
    data = safe_load_yaml(paths.config_path)
    return AppConfig.from_dict(data if isinstance(data, dict) else None)


def save_config(paths: AppPaths, config: AppConfig) -> None:
    safe_dump_yaml(paths.config_path, config.to_dict())


def copy_skill_template(destination: Path) -> Path:
    from cronctl.skill import template_path

    destination.mkdir(parents=True, exist_ok=True)
    target = destination / "cronctl.md"
    shutil.copyfile(template_path(), target)
    return target

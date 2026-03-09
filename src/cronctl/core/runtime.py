from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from cronctl.core.config import build_paths, ensure_home, load_config
from cronctl.core.db import RunLogDB
from cronctl.core.executor import Executor
from cronctl.core.job_manager import CrontabBackend, JobManager
from cronctl.core.notifier import Notifier

if TYPE_CHECKING:
    from pathlib import Path

    from cronctl.core.config import AppPaths
    from cronctl.core.models import AppConfig


@dataclass
class Runtime:
    paths: AppPaths
    config: AppConfig
    db: RunLogDB
    jobs: JobManager
    notifier: Notifier
    executor: Executor


def build_runtime(home: str | Path, backend: CrontabBackend | None = None) -> Runtime:
    paths = build_paths(home)
    ensure_home(paths)
    config = load_config(paths)
    db = RunLogDB(paths.db_path)
    jobs = JobManager(paths, backend=backend)
    notifier = Notifier()
    executor = Executor(paths=paths, config=config, job_manager=jobs, db=db, notifier=notifier)
    return Runtime(
        paths=paths,
        config=config,
        db=db,
        jobs=jobs,
        notifier=notifier,
        executor=executor,
    )

from __future__ import annotations

from pathlib import Path

from cronctl.core.config import build_paths
from cronctl.core.db import RunLogDB
from cronctl.core.executor import Executor
from cronctl.core.job_manager import JobManager, MemoryCrontabBackend
from cronctl.core.models import AppConfig, Job, RetryPolicy, RunStatus


def test_job_manager_sync_preserves_existing_entries(tmp_path: Path) -> None:
    backend = MemoryCrontabBackend("0 12 * * * /usr/bin/something")
    paths = build_paths(tmp_path / "home")
    manager = JobManager(paths, backend=backend)
    manager.save(Job(id="backup-db", schedule="0 3 * * *", command="printf backup"))
    manager.save(
        Job(id="disabled-job", schedule="*/5 * * * *", command="printf skip", enabled=False)
    )

    result = manager.sync()

    assert result["synced"] is True
    assert "0 12 * * * /usr/bin/something" in backend.text
    assert "0 3 * * *" in backend.text
    assert "backup-db" in backend.text
    assert "disabled-job" not in backend.text


def test_executor_records_success_and_timeout(tmp_path: Path) -> None:
    paths = build_paths(tmp_path / "home")
    manager = JobManager(paths, backend=MemoryCrontabBackend())
    config = AppConfig(default_timeout=1)
    db = RunLogDB(paths.db_path)
    executor = Executor(paths=paths, config=config, job_manager=manager, db=db)

    manager.save(Job(id="hello", schedule="* * * * *", command="printf hello"))
    manager.save(
        Job(
            id="slow-job",
            schedule="* * * * *",
            command="python -c 'import time; time.sleep(2)'",
            timeout=1,
            retry=RetryPolicy(max_attempts=1, delay=0),
        )
    )

    success = executor.execute("hello")
    timeout = executor.execute("slow-job")

    assert success.status == RunStatus.SUCCESS
    assert success.stdout == "hello"
    assert timeout.status == RunStatus.TIMEOUT
    assert "timed out" in timeout.error_msg.lower()

    runs = db.get_runs("slow-job", last=1)
    assert runs[0].status == RunStatus.TIMEOUT

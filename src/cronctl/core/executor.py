from __future__ import annotations

import logging
import os
import subprocess
import time
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from cronctl.core.db import RunLogDB
from cronctl.core.job_manager import JobManager
from cronctl.core.models import AppConfig, Job, RetryPolicy, RunResult, RunStatus
from cronctl.core.notifier import Notifier, should_notify
from cronctl.core.utils import generate_run_id, tail_lines, utc_now

if TYPE_CHECKING:
    from datetime import datetime

    from cronctl.core.config import AppPaths

logger = logging.getLogger(__name__)


class Executor:
    def __init__(
        self,
        paths: AppPaths,
        config: AppConfig,
        job_manager: JobManager | None = None,
        db: RunLogDB | None = None,
        notifier: Notifier | None = None,
    ) -> None:
        self.paths = paths
        self.config = config
        self.job_manager = job_manager or JobManager(paths)
        self.db = db or RunLogDB(paths.db_path)
        self.notifier = notifier or Notifier()

    def execute(self, job_id: str) -> RunResult:
        job = self.job_manager.load(job_id)
        run = RunResult(run_id=generate_run_id(), job_id=job.id, started_at=utc_now())
        self.db.insert_run(run)
        previous_status = self.db.latest_terminal_status(job.id)
        retry = job.retry or self.config.default_retry or RetryPolicy()
        attempts = max(retry.max_attempts, 1)
        final_result = run
        for attempt in range(1, attempts + 1):
            result = self._run_attempt(job, run.run_id, run.started_at, attempt)
            final_result = result
            if result.status == RunStatus.SUCCESS:
                self.db.update_run(result)
                if previous_status in {RunStatus.FAILED, RunStatus.TIMEOUT} and should_notify(
                    self.config, job, "recovery"
                ):
                    self.notifier.send(self.config, job, result, "recovery")
                return result
            if attempt < attempts:
                retrying = replace(result, status=RunStatus.RETRYING)
                self.db.update_run(retrying)
                time.sleep(max(retry.delay, 0))
        self.db.update_run(final_result)
        self._run_hook("on_failure", job, final_result)
        event = "timeout" if final_result.status == RunStatus.TIMEOUT else "failure"
        if should_notify(self.config, job, event):
            self.notifier.send(self.config, job, final_result, event)
        return final_result

    def _run_attempt(self, job: Job, run_id: str, started_at: datetime, attempt: int) -> RunResult:
        timeout = job.timeout if job.timeout is not None else self.config.default_timeout
        env = os.environ.copy()
        env.update(job.env)
        command = job.command
        process = subprocess.Popen(
            command,
            shell=True,
            executable="/bin/sh",
            cwd=str(Path.home()),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        error_msg = ""
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            exit_code = process.returncode
            status = RunStatus.SUCCESS if exit_code == 0 else RunStatus.FAILED
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            exit_code = process.returncode
            status = RunStatus.TIMEOUT
            error_msg = f"Process timed out after {timeout} seconds"
        except OSError as exc:
            stdout = ""
            stderr = str(exc)
            exit_code = None
            status = RunStatus.FAILED
            error_msg = str(exc)
        finished_at = utc_now()
        stdout, stdout_truncated = tail_lines(stdout or "", self.config.max_log_lines)
        stderr, stderr_truncated = tail_lines(stderr or "", self.config.max_log_lines)
        if stdout_truncated or stderr_truncated:
            note = "Output truncated to the last configured log lines"
            error_msg = note if not error_msg else f"{error_msg}; {note}"
        return RunResult(
            run_id=run_id,
            job_id=job.id,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=int((finished_at - started_at).total_seconds() * 1000),
            exit_code=exit_code,
            status=status,
            attempt=attempt,
            stdout=stdout,
            stderr=stderr,
            error_msg=error_msg,
        )

    def _run_hook(self, event: str, job: Job, result: RunResult) -> None:
        hook = self.config.hooks.get(event)
        if not hook:
            return
        path = Path(hook).expanduser()
        if not path.exists():
            logger.warning("Hook path does not exist: %s", path)
            return
        env = os.environ.copy()
        env.update(
            {
                "CRONCTL_EVENT": event,
                "CRONCTL_JOB_ID": job.id,
                "CRONCTL_RUN_ID": result.run_id,
                "CRONCTL_STATUS": result.status.value,
                "CRONCTL_EXIT_CODE": "" if result.exit_code is None else str(result.exit_code),
                "CRONCTL_ATTEMPT": str(result.attempt),
            }
        )
        try:
            subprocess.run(
                ["/bin/sh", str(path)],
                check=False,
                cwd=str(Path.home()),
                env=env,
                capture_output=True,
                text=True,
            )
        except OSError as exc:  # pragma: no cover
            logger.warning("Hook execution failed: %s", exc)

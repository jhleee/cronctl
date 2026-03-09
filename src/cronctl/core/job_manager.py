from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from cronctl.core.config import AppPaths, ensure_home
from cronctl.core.cron import next_run as cron_next_run
from cronctl.core.cron import validate_cron_expression
from cronctl.core.models import JOB_ID_PATTERN, Job
from cronctl.core.utils import parse_bool, safe_dump_yaml, safe_load_yaml, shell_join

MANAGED_START = "# --- CRONCTL MANAGED START ---"
MANAGED_END = "# --- CRONCTL MANAGED END ---"


class CrontabBackend:
    def read(self) -> str:
        raise NotImplementedError

    def write(self, text: str) -> None:
        raise NotImplementedError


class SystemCrontabBackend(CrontabBackend):
    def __init__(self, executable: str | None = None) -> None:
        self.executable = executable or os.environ.get("CRONCTL_CRONTAB_BIN") or "crontab"

    def read(self) -> str:
        proc = subprocess.run(
            [self.executable, "-l"],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            return proc.stdout.rstrip("\n")
        stderr = proc.stderr.strip().lower()
        if proc.returncode == 1 and ("no crontab" in stderr or "can't open" in stderr):
            return ""
        raise RuntimeError(proc.stderr.strip() or "Failed to read crontab")

    def write(self, text: str) -> None:
        proc = subprocess.run(
            [self.executable, "-"],
            input=text,
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "Failed to write crontab")


class MemoryCrontabBackend(CrontabBackend):
    def __init__(self, initial: str = "") -> None:
        self.text = initial

    def read(self) -> str:
        return self.text

    def write(self, text: str) -> None:
        self.text = text


class JobManager:
    def __init__(self, paths: AppPaths, backend: CrontabBackend | None = None) -> None:
        self.paths = paths
        self.backend = backend or SystemCrontabBackend()
        ensure_home(paths)

    def job_path(self, job_id: str) -> Path:
        return self.paths.jobs_dir / f"{job_id}.yaml"

    def load(self, job_id: str) -> Job:
        path = self.job_path(job_id)
        data = safe_load_yaml(path)
        if not isinstance(data, dict):
            raise FileNotFoundError(f"Job not found: {job_id}")
        return Job.from_dict(data)

    def save(self, job: Job, overwrite: bool = False) -> Path:
        self.validate(job, allow_existing=overwrite)
        path = self.job_path(job.id)
        if path.exists() and not overwrite:
            raise ValueError(f"Job already exists: {job.id}")
        safe_dump_yaml(path, job.to_dict())
        return path

    def delete(self, job_id: str) -> bool:
        path = self.job_path(job_id)
        if not path.exists():
            raise FileNotFoundError(f"Job not found: {job_id}")
        path.unlink()
        return True

    def list(self, tag: str | None = None, status: str = "all") -> list[Job]:
        jobs: list[Job] = []
        for path in sorted(self.paths.jobs_dir.glob("*.yaml")):
            data = safe_load_yaml(path)
            if not isinstance(data, dict):
                continue
            jobs.append(Job.from_dict(data))
        if tag is not None:
            jobs = [job for job in jobs if tag in job.tags]
        if status == "enabled":
            jobs = [job for job in jobs if job.enabled]
        elif status == "disabled":
            jobs = [job for job in jobs if not job.enabled]
        return jobs

    def update(self, job_id: str, assignments: list[str]) -> tuple[Job, list[str]]:
        job = self.load(job_id)
        data = job.to_dict()
        changed: list[str] = []
        for assignment in assignments:
            key, _, raw_value = assignment.partition("=")
            if not key or not _:
                raise ValueError(f"Invalid assignment: {assignment}")
            normalized_key = key.strip()
            self._apply_assignment(data, normalized_key, raw_value.strip())
            changed.append(normalized_key)
        updated = Job.from_dict(data)
        self.validate(updated, allow_existing=True)
        self.save(updated, overwrite=True)
        return updated, changed

    def export_jobs(self) -> dict[str, Any]:
        return {"jobs": [job.to_dict() for job in self.list()]}

    def import_jobs(self, source: Path, replace_existing: bool = False) -> list[Job]:
        payload = safe_load_yaml(source)
        raw_jobs = payload.get("jobs", []) if isinstance(payload, dict) else payload
        if not isinstance(raw_jobs, list):
            raise ValueError("Import file must contain a jobs list")
        imported: list[Job] = []
        for item in raw_jobs:
            if not isinstance(item, dict):
                raise ValueError("Each imported job must be a mapping")
            job = Job.from_dict(item)
            self.save(job, overwrite=replace_existing)
            imported.append(job)
        return imported

    def validate(self, job: Job, allow_existing: bool = False) -> None:
        if not JOB_ID_PATTERN.fullmatch(job.id):
            raise ValueError("Job id must match ^[a-z][a-z0-9-]{0,63}$")
        validate_cron_expression(job.schedule)
        if not job.command.strip():
            raise ValueError("Command must not be empty")
        if job.timeout is not None and job.timeout <= 0:
            raise ValueError("Timeout must be greater than 0")
        if job.retry is not None:
            if job.retry.max_attempts <= 0:
                raise ValueError("Retry max_attempts must be greater than 0")
            if job.retry.delay < 0:
                raise ValueError("Retry delay must be >= 0")
        if any(not tag.strip() for tag in job.tags):
            raise ValueError("Tags must not be empty")
        existing = self.job_path(job.id).exists()
        if existing and not allow_existing:
            raise ValueError(f"Job already exists: {job.id}")
        self._validate_command(job.command)

    def sync(self) -> dict[str, Any]:
        current = self.backend.read()
        rendered = self.render_crontab(current)
        self.backend.write(rendered)
        return {"synced": True, "job_count": len([job for job in self.list() if job.enabled])}

    def render_crontab(self, existing: str) -> str:
        lines = existing.splitlines()
        managed = self.render_managed_block().splitlines()
        if MANAGED_START in lines and MANAGED_END in lines:
            start = lines.index(MANAGED_START)
            end = lines.index(MANAGED_END)
            if end < start:
                raise ValueError("Malformed managed crontab region")
            lines = lines[:start] + managed + lines[end + 1 :]
        else:
            if lines and lines[-1].strip():
                lines.append("")
            lines.extend(managed)
        return "\n".join(lines).rstrip() + "\n"

    def render_managed_block(self) -> str:
        executable = shutil.which("cronctl") or "cronctl"
        lines = [MANAGED_START]
        for job in self.list(status="enabled"):
            command = [executable]
            if str(self.paths.home.expanduser()) != str((Path.home() / ".cronctl").expanduser()):
                command.extend(["--home", str(self.paths.home)])
            command.extend(["exec", job.id])
            lines.append(f"{job.schedule} {shell_join(command)} 2>&1")
        lines.append(MANAGED_END)
        return "\n".join(lines)

    def status_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for job in self.list():
            next_at = cron_next_run(job.schedule)
            rows.append(
                {
                    "id": job.id,
                    "schedule": job.schedule,
                    "description": job.description,
                    "enabled": job.enabled,
                    "tags": job.tags,
                    "next_at": next_at.isoformat() if next_at else None,
                }
            )
        return rows

    def _validate_command(self, command: str) -> None:
        stripped = command.strip()
        if not stripped:
            raise ValueError("Command must not be empty")
        if any(token in stripped for token in ("|", ">", "<", "&", ";", "$(", "`")):
            return
        first = stripped.split()[0]
        if first.startswith(("~", "/", ".")):
            path = Path(first).expanduser()
            if not path.exists():
                raise ValueError(f"Command path does not exist: {first}")

    def _apply_assignment(self, data: dict[str, Any], key: str, raw_value: str) -> None:
        if key.startswith("env."):
            env = dict(data.get("env", {}))
            env[key.split(".", 1)[1]] = str(raw_value)
            data["env"] = env
            return
        if key == "tags":
            data["tags"] = [part.strip() for part in raw_value.split(",") if part.strip()]
            return
        if key == "retry.max_attempts":
            retry = dict(data.get("retry") or {})
            retry["max_attempts"] = int(raw_value)
            data["retry"] = retry
            return
        if key == "retry.delay":
            retry = dict(data.get("retry") or {})
            retry["delay"] = int(raw_value)
            data["retry"] = retry
            return
        if key in {"enabled", "notify"}:
            data[key] = None if raw_value.strip().lower() == "null" else parse_bool(raw_value)
            return
        if key == "timeout":
            data[key] = int(raw_value)
            return
        if key in {"id", "schedule", "command", "description"}:
            data[key] = raw_value
            return
        raise ValueError(f"Unsupported field: {key}")

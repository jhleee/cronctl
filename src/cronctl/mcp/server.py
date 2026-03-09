from __future__ import annotations

import json
from pathlib import Path

import yaml

from cronctl.core.cron import next_run
from cronctl.core.models import Job, RetryPolicy
from cronctl.core.runtime import build_runtime
from cronctl.core.utils import safe_load_yaml

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    FastMCP = None


def serve_mcp(home: Path | None = None) -> None:
    if FastMCP is None:
        raise SystemExit("MCP support is not installed. Install with: pip install 'cronctl[mcp]'")
    runtime = build_runtime(home or Path.home() / ".cronctl")
    server = FastMCP(name="cronctl", instructions="Manage local cron-backed jobs.", debug=False)

    @server.tool(name="cronctl_list_jobs", structured_output=True)
    def list_jobs(tag: str | None = None, status: str = "all") -> dict:
        jobs = runtime.jobs.list(tag=tag, status=status)
        payload = []
        for job in jobs:
            last_run = runtime.db.get_last_run(job.id)
            item = job.to_dict()
            if last_run:
                item["last_run"] = {
                    "status": last_run.status.value,
                    "at": last_run.finished_at.isoformat() if last_run.finished_at else None,
                    "duration_ms": last_run.duration_ms,
                }
            payload.append(item)
        return {"jobs": payload}

    @server.tool(name="cronctl_create_job", structured_output=True)
    def create_job(
        id: str,
        schedule: str,
        command: str,
        description: str = "",
        timeout: int | None = None,
        retry_max: int | None = None,
        retry_delay: int | None = None,
        tags: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> dict:
        retry = None
        if retry_max is not None or retry_delay is not None:
            retry = RetryPolicy(max_attempts=retry_max or 1, delay=retry_delay or 30)
        job = Job(
            id=id,
            schedule=schedule,
            command=command,
            description=description,
            timeout=timeout,
            retry=retry,
            tags=tags or [],
            env=env or {},
        )
        yaml_path = runtime.jobs.save(job)
        sync = runtime.jobs.sync()
        return {"created": True, "job_id": job.id, "crontab_synced": sync["synced"], "yaml_path": str(yaml_path)}

    @server.tool(name="cronctl_delete_job", structured_output=True)
    def delete_job(job_id: str) -> dict:
        runtime.jobs.delete(job_id)
        sync = runtime.jobs.sync()
        return {"deleted": True, "job_id": job_id, "crontab_synced": sync["synced"]}

    @server.tool(name="cronctl_update_job", structured_output=True)
    def update_job(
        job_id: str,
        schedule: str | None = None,
        command: str | None = None,
        description: str | None = None,
        timeout: int | None = None,
        enabled: bool | None = None,
    ) -> dict:
        changes: list[str] = []
        if schedule is not None:
            changes.append(f"schedule={schedule}")
        if command is not None:
            changes.append(f"command={command}")
        if description is not None:
            changes.append(f"description={description}")
        if timeout is not None:
            changes.append(f"timeout={timeout}")
        if enabled is not None:
            changes.append(f"enabled={'true' if enabled else 'false'}")
        job, changed = runtime.jobs.update(job_id, changes)
        sync = runtime.jobs.sync()
        return {"updated": True, "job_id": job.id, "changes": changed, "crontab_synced": sync["synced"]}

    @server.tool(name="cronctl_run_job", structured_output=True)
    def run_job(job_id: str) -> dict:
        result = runtime.executor.execute(job_id)
        return result.to_dict()

    @server.tool(name="cronctl_get_logs", structured_output=True)
    def get_logs(job_id: str, last: int = 10, status_filter: str = "all") -> dict:
        runs = runtime.db.get_runs(job_id, last=last, status_filter=status_filter)
        return {"job_id": job_id, "runs": [run.to_dict() for run in runs]}

    @server.tool(name="cronctl_system_status", structured_output=True)
    def system_status() -> dict:
        jobs = runtime.jobs.list()
        enabled = [job for job in jobs if job.enabled]
        next_runs = []
        for job in enabled:
            next_at = next_run(job.schedule)
            next_runs.append({"job_id": job.id, "next_at": next_at.isoformat() if next_at else None})
        next_runs.sort(key=lambda item: item["next_at"] or "")
        return {
            "total_jobs": len(jobs),
            "enabled": len(enabled),
            "disabled": len(jobs) - len(enabled),
            "recent_runs": runtime.db.recent_summary(),
            "failed_jobs": runtime.db.failed_jobs([job.id for job in jobs]),
            "next_runs": next_runs[:10],
        }

    @server.resource("cronctl://jobs", mime_type="application/json")
    def jobs_resource() -> str:
        return json.dumps(runtime.jobs.export_jobs(), indent=2, sort_keys=False)

    @server.resource("cronctl://jobs/{job_id}", mime_type="application/yaml")
    def job_resource(job_id: str) -> str:
        payload = safe_load_yaml(runtime.jobs.job_path(job_id))
        if payload is None:
            raise ValueError(f"Job not found: {job_id}")
        return yaml.safe_dump(payload, sort_keys=False, default_flow_style=False)

    @server.resource("cronctl://config", mime_type="application/yaml")
    def config_resource() -> str:
        return yaml.safe_dump(runtime.config.to_dict(), sort_keys=False, default_flow_style=False)

    server.run(transport="stdio")

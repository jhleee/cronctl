from __future__ import annotations

from pathlib import Path

import click
import yaml

from cronctl.cli.support import emit, exit_with_error, format_job_line, get_runtime_for_context
from cronctl.core.models import Job, RetryPolicy


@click.command()
@click.option("--id", "job_id", help="Job identifier")
@click.option("--schedule", help="Cron schedule")
@click.option("--command", help="Shell command to execute")
@click.option("--description", default="", help="Job description")
@click.option("--timeout", type=int, default=None, help="Timeout in seconds")
@click.option("--retry-max", type=int, default=None, help="Max retry attempts")
@click.option("--retry-delay", type=int, default=None, help="Retry delay in seconds")
@click.option("--tag", "tags", multiple=True, help="Tag to attach to the job")
@click.option("--env", "env_pairs", multiple=True, help="Environment variable KEY=VALUE")
@click.option("--file", "job_file", type=click.Path(path_type=Path), default=None, help="YAML file")
@click.option("--enabled/--disabled", default=True, help="Create the job enabled or disabled")
@click.option("--notify/--no-notify", default=None, help="Override notifications for this job")
@click.pass_context
def add(
    ctx: click.Context,
    job_id: str | None,
    schedule: str | None,
    command: str | None,
    description: str,
    timeout: int | None,
    retry_max: int | None,
    retry_delay: int | None,
    tags: tuple[str, ...],
    env_pairs: tuple[str, ...],
    job_file: Path | None,
    enabled: bool,
    notify: bool | None,
) -> None:
    """Create and register a job."""
    runtime = get_runtime_for_context(ctx)
    try:
        if job_file:
            with job_file.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle)
            if not isinstance(payload, dict):
                raise ValueError("Job YAML must contain a mapping")
            job = Job.from_dict(payload)
        else:
            if not job_id or not schedule or not command:
                raise ValueError("--id, --schedule, and --command are required without --file")
            env: dict[str, str] = {}
            for item in env_pairs:
                key, _, value = item.partition("=")
                if not key or not _:
                    raise ValueError(f"Invalid env assignment: {item}")
                env[key] = value
            retry = None
            if retry_max is not None or retry_delay is not None:
                retry = RetryPolicy(max_attempts=retry_max or 1, delay=retry_delay or 30)
            job = Job(
                id=job_id,
                schedule=schedule,
                command=command,
                description=description,
                timeout=timeout,
                retry=retry,
                env=env,
                tags=list(tags),
                enabled=enabled,
                notify=notify,
            )
        yaml_path = runtime.jobs.save(job)
        sync = runtime.jobs.sync()
    except Exception as exc:
        exit_with_error(ctx, str(exc))
        return
    emit(
        ctx,
        {
            "created": True,
            "job_id": job.id,
            "crontab_synced": sync["synced"],
            "yaml_path": str(yaml_path),
        },
        human=f"Created job {job.id}",
    )


@click.command(name="remove")
@click.argument("job_id")
@click.pass_context
def remove_job(ctx: click.Context, job_id: str) -> None:
    """Delete a job and sync crontab."""
    runtime = get_runtime_for_context(ctx)
    try:
        runtime.jobs.delete(job_id)
        sync = runtime.jobs.sync()
    except Exception as exc:
        exit_with_error(ctx, str(exc))
        return
    emit(
        ctx,
        {"deleted": True, "job_id": job_id, "crontab_synced": sync["synced"]},
        human=f"Removed job {job_id}",
    )


@click.command()
@click.argument("job_id")
@click.option("--set", "assignments", multiple=True, required=True, help="Set key=value")
@click.pass_context
def edit(ctx: click.Context, job_id: str, assignments: tuple[str, ...]) -> None:
    """Update job properties inline."""
    runtime = get_runtime_for_context(ctx)
    try:
        job, changed = runtime.jobs.update(job_id, list(assignments))
        sync = runtime.jobs.sync()
    except Exception as exc:
        exit_with_error(ctx, str(exc))
        return
    emit(
        ctx,
        {"updated": True, "job_id": job.id, "changes": changed, "crontab_synced": sync["synced"]},
        human=f"Updated job {job.id}: {', '.join(changed)}",
    )


@click.command(name="list")
@click.option("--tag", default=None, help="Filter by tag")
@click.option(
    "--status",
    type=click.Choice(["all", "enabled", "disabled"], case_sensitive=False),
    default="all",
    show_default=True,
)
@click.pass_context
def list_jobs(ctx: click.Context, tag: str | None, status: str) -> None:
    """List registered jobs."""
    runtime = get_runtime_for_context(ctx)
    jobs = runtime.jobs.list(tag=tag, status=status)
    payload = {"jobs": [job.to_dict() for job in jobs]}
    if ctx.obj["json"]:
        emit(ctx, payload)
        return
    if not jobs:
        click.echo("No jobs found.")
        return
    for job in jobs:
        click.echo(format_job_line(job))


@click.command()
@click.argument("job_id")
@click.pass_context
def enable(ctx: click.Context, job_id: str) -> None:
    """Enable a job."""
    _set_enabled(ctx, job_id, True)


@click.command()
@click.argument("job_id")
@click.pass_context
def disable(ctx: click.Context, job_id: str) -> None:
    """Disable a job."""
    _set_enabled(ctx, job_id, False)


def _set_enabled(ctx: click.Context, job_id: str, enabled: bool) -> None:
    runtime = get_runtime_for_context(ctx)
    try:
        job, _ = runtime.jobs.update(job_id, [f"enabled={'true' if enabled else 'false'}"])
        sync = runtime.jobs.sync()
    except Exception as exc:
        exit_with_error(ctx, str(exc))
        return
    action = "Enabled" if enabled else "Disabled"
    emit(
        ctx,
        {"updated": True, "job_id": job.id, "enabled": enabled, "crontab_synced": sync["synced"]},
        human=f"{action} job {job.id}",
    )

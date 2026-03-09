from __future__ import annotations

from datetime import datetime

import click

from cronctl.cli.support import emit, exit_with_error, format_run_line, get_runtime_for_context
from cronctl.core.cron import next_run
from cronctl.core.models import RunStatus


@click.command(name="exec")
@click.argument("job_id")
@click.pass_context
def exec_job(ctx: click.Context, job_id: str) -> None:
    """Run a job immediately."""
    runtime = get_runtime_for_context(ctx)
    try:
        result = runtime.executor.execute(job_id)
    except Exception as exc:
        exit_with_error(ctx, str(exc))
        return
    emit(ctx, result.to_dict(), human=format_run_line(result))
    if result.status != RunStatus.SUCCESS:
        raise click.exceptions.Exit(2)


@click.command()
@click.argument("job_id")
@click.option("--last", type=int, default=10, show_default=True, help="How many runs to show")
@click.option(
    "--status-filter",
    type=click.Choice(["all", "success", "failed", "timeout", "retrying"], case_sensitive=False),
    default="all",
    show_default=True,
)
@click.pass_context
def logs(ctx: click.Context, job_id: str, last: int, status_filter: str) -> None:
    """Show execution history for a job."""
    runtime = get_runtime_for_context(ctx)
    try:
        runs = runtime.db.get_runs(job_id, last=last, status_filter=status_filter)
    except Exception as exc:
        exit_with_error(ctx, str(exc))
        return
    payload = {"job_id": job_id, "runs": [run.to_dict() for run in runs]}
    if ctx.obj["json"]:
        emit(ctx, payload)
        return
    if not runs:
        click.echo("No runs found.")
        return
    for run in runs:
        click.echo(format_run_line(run))


@click.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show overall job status."""
    runtime = get_runtime_for_context(ctx)
    jobs = runtime.jobs.list()
    enabled = [job for job in jobs if job.enabled]
    recent_runs = runtime.db.recent_summary()
    failed_jobs = runtime.db.failed_jobs([job.id for job in jobs])
    next_runs: list[dict[str, str | None]] = []
    now = datetime.now().astimezone()
    for job in enabled:
        next_at = next_run(job.schedule, after=now)
        next_runs.append({"job_id": job.id, "next_at": next_at.isoformat() if next_at else None})
    next_runs.sort(key=lambda item: item["next_at"] or "")
    payload = {
        "total_jobs": len(jobs),
        "enabled": len(enabled),
        "disabled": len(jobs) - len(enabled),
        "recent_runs": recent_runs,
        "failed_jobs": failed_jobs,
        "next_runs": next_runs[:10],
    }
    if ctx.obj["json"]:
        emit(ctx, payload)
        return
    click.echo(
        "Jobs: "
        f"{payload['total_jobs']} total, "
        f"{payload['enabled']} enabled, "
        f"{payload['disabled']} disabled"
    )
    click.echo(
        f"Recent runs: {recent_runs['last_24h']} in last 24h, "
        f"{recent_runs['success']} success, {recent_runs['failed']} failed"
    )
    if failed_jobs:
        click.echo("Failures:")
        for item in failed_jobs:
            click.echo(
                f"  {item['job_id']} status={item['status']} exit={item['exit_code']} "
                f"consecutive={item['consecutive_failures']}"
            )

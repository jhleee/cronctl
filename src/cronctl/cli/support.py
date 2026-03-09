from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click
import yaml

from cronctl.core.runtime import Runtime, build_runtime

if TYPE_CHECKING:
    from cronctl.core.models import Job, RunResult


@dataclass
class CLIState:
    home: Path
    output_json: bool


def get_state(ctx: click.Context) -> CLIState:
    state = ctx.ensure_object(dict)
    return CLIState(home=Path(state["home"]), output_json=bool(state["json"]))


def get_runtime_for_context(ctx: click.Context) -> Runtime:
    state = get_state(ctx)
    return build_runtime(state.home)


def emit(ctx: click.Context, payload: Any, human: str | None = None) -> None:
    state = get_state(ctx)
    if state.output_json:
        click.echo(json.dumps(payload, indent=2, sort_keys=False, default=str))
    elif human is not None:
        click.echo(human)


def emit_yaml(ctx: click.Context, payload: Any) -> None:
    state = get_state(ctx)
    if state.output_json:
        click.echo(json.dumps(payload, indent=2, sort_keys=False, default=str))
    else:
        click.echo(yaml.safe_dump(payload, sort_keys=False, default_flow_style=False).rstrip())


def exit_with_error(ctx: click.Context, message: str, code: int = 1) -> None:
    state = get_state(ctx)
    if state.output_json:
        click.echo(json.dumps({"ok": False, "error": message}))
        raise click.exceptions.Exit(code)
    raise click.ClickException(message)


def format_job_line(job: Job) -> str:
    status = "enabled" if job.enabled else "disabled"
    description = f" - {job.description}" if job.description else ""
    return f"{job.id} [{status}] {job.schedule}{description}"


def format_run_line(run: RunResult) -> str:
    exit_code = "-" if run.exit_code is None else run.exit_code
    return f"{run.job_id} {run.status.value} exit={exit_code} attempt={run.attempt}"

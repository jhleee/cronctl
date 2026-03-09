from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import click
import yaml

from cronctl.cli.support import emit, emit_yaml, exit_with_error, get_runtime_for_context, get_state
from cronctl.core.config import copy_skill_template, ensure_home, save_config
from cronctl.core.models import AppConfig, NotifyChannel
from cronctl.core.runtime import build_runtime


@click.command()
@click.option("--non-interactive", is_flag=True, help="Do not prompt; use defaults")
@click.option("--discord-webhook", default=None, help="Discord webhook URL")
@click.option("--slack-webhook", default=None, help="Slack webhook URL")
@click.option("--webhook-url", default=None, help="Generic webhook URL")
@click.option(
    "--skill-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Copy skill manifest",
)
@click.option(
    "--register-claude-mcp",
    is_flag=True,
    help="Register cronctl mcp in ~/.claude/settings.json",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing config values for init-managed settings",
)
@click.pass_context
def init(
    ctx: click.Context,
    non_interactive: bool,
    discord_webhook: str | None,
    slack_webhook: str | None,
    webhook_url: str | None,
    skill_path: Path | None,
    register_claude_mcp: bool,
    force: bool,
) -> None:
    """Interactive first-time setup."""
    state = get_state(ctx)
    runtime = build_runtime(state.home)
    config = runtime.config if not force else AppConfig()
    ensure_home(runtime.paths)
    runtime.db.initialize()

    created_channels: list[NotifyChannel] = []
    if discord_webhook:
        created_channels.append(NotifyChannel(type="discord", webhook_url=discord_webhook))
    if slack_webhook:
        created_channels.append(NotifyChannel(type="slack", webhook_url=slack_webhook))
    if webhook_url:
        created_channels.append(NotifyChannel(type="webhook", url=webhook_url))
    if not non_interactive and not created_channels and click.confirm(
        "Configure notifications now?", default=False
    ):
        choice = click.Choice(["discord", "slack", "webhook"], case_sensitive=False)
        while True:
            channel_type = click.prompt("Channel type", type=choice)
            if channel_type == "discord":
                created_channels.append(
                    NotifyChannel(type="discord", webhook_url=click.prompt("Discord webhook URL"))
                )
            elif channel_type == "slack":
                created_channels.append(
                    NotifyChannel(type="slack", webhook_url=click.prompt("Slack webhook URL"))
                )
            else:
                created_channels.append(
                    NotifyChannel(type="webhook", url=click.prompt("Webhook URL"))
                )
            if not click.confirm("Add another channel?", default=False):
                break
    if created_channels:
        config.notifications.channels = created_channels
    save_config(runtime.paths, config)

    copied_skill = None
    if skill_path is not None:
        copied_skill = copy_skill_template(skill_path)
    elif not non_interactive and click.confirm(
        "Copy SKILL.md to a project directory?", default=False
    ):
        copied_skill = copy_skill_template(Path(click.prompt("Skill directory", default=".")))

    claude_settings = None
    should_register_mcp = register_claude_mcp or (
        not non_interactive
        and click.confirm(
            "Register MCP in ~/.claude/settings.json?",
            default=False,
        )
    )
    if should_register_mcp:
        claude_settings = _register_claude_mcp()

    cron = _detect_cron()
    payload = {
        "initialized": True,
        "home": str(runtime.paths.home),
        "jobs_dir": str(runtime.paths.jobs_dir),
        "scripts_dir": str(runtime.paths.scripts_dir),
        "hooks_dir": str(runtime.paths.hooks_dir),
        "db_path": str(runtime.paths.db_path),
        "cron": cron,
        "skill_path": str(copied_skill) if copied_skill else None,
        "claude_settings": str(claude_settings) if claude_settings else None,
    }
    human = f"Initialized cronctl home at {runtime.paths.home}"
    emit(ctx, payload, human=human)


@click.command()
@click.pass_context
def sync(ctx: click.Context) -> None:
    """Regenerate crontab from job definitions."""
    runtime = get_runtime_for_context(ctx)
    try:
        result = runtime.jobs.sync()
    except Exception as exc:
        exit_with_error(ctx, str(exc))
        return
    emit(ctx, result, human=f"Synchronized {result['job_count']} job(s) to crontab")


@click.command()
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Write export to a file",
)
@click.pass_context
def export(ctx: click.Context, output: Path | None) -> None:
    """Export all jobs as YAML."""
    runtime = get_runtime_for_context(ctx)
    payload = runtime.jobs.export_jobs()
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        emit(
            ctx,
            {"exported": True, "path": str(output), "job_count": len(payload["jobs"])},
            human=str(output),
        )
        return
    emit_yaml(ctx, payload)


@click.command(name="import")
@click.argument("source", type=click.Path(path_type=Path))
@click.option("--replace", is_flag=True, help="Replace existing jobs")
@click.pass_context
def import_jobs(ctx: click.Context, source: Path, replace: bool) -> None:
    """Import jobs from exported YAML."""
    runtime = get_runtime_for_context(ctx)
    try:
        jobs = runtime.jobs.import_jobs(source, replace_existing=replace)
        sync_result = runtime.jobs.sync()
    except Exception as exc:
        exit_with_error(ctx, str(exc))
        return
    emit(
        ctx,
        {
            "imported": len(jobs),
            "job_ids": [job.id for job in jobs],
            "crontab_synced": sync_result["synced"],
        },
        human=f"Imported {len(jobs)} job(s)",
    )


@click.command()
@click.option("--days", type=int, default=None, help="Delete logs older than N days")
@click.pass_context
def gc(ctx: click.Context, days: int | None) -> None:
    """Garbage collect old log entries."""
    runtime = get_runtime_for_context(ctx)
    retention = days if days is not None else runtime.config.log_retention_days
    deleted = runtime.db.gc(retention)
    emit(ctx, {"deleted": deleted, "days": retention}, human=f"Deleted {deleted} old log entries")


@click.command()
@click.pass_context
def doctor(ctx: click.Context) -> None:
    """Diagnose common local issues."""
    runtime = get_runtime_for_context(ctx)
    cron = _detect_cron()
    crontab_bin = shutil.which("crontab")
    payload: dict[str, Any] = {
        "home": str(runtime.paths.home),
        "config_exists": runtime.paths.config_path.exists(),
        "db_exists": runtime.paths.db_path.exists(),
        "crontab_binary": crontab_bin,
        "cron": cron,
        "notify_available": runtime.notifier.available(),
        "mcp_available": _has_module("mcp"),
    }
    if ctx.obj["json"]:
        emit(ctx, payload)
        return
    click.echo(f"Home: {payload['home']}")
    click.echo(f"Config: {'ok' if payload['config_exists'] else 'missing'}")
    click.echo(f"DB: {'ok' if payload['db_exists'] else 'missing'}")
    click.echo(f"crontab: {crontab_bin or 'missing'}")
    click.echo(f"cron service: {cron['service']}")
    click.echo(f"notify extra: {'installed' if payload['notify_available'] else 'missing'}")
    click.echo(f"mcp extra: {'installed' if payload['mcp_available'] else 'missing'}")


def _detect_cron() -> dict[str, Any]:
    result = {"crontab_access": shutil.which("crontab") is not None, "service": "unknown"}
    candidates = (["systemctl", "is-active", "cron"], ["systemctl", "is-active", "crond"])
    for command in candidates:
        if shutil.which(command[0]) is None:
            continue
        proc = subprocess.run(command, capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            result["service"] = "running"
            return result
        output = (proc.stdout or proc.stderr).strip()
        if output:
            result["service"] = output
    return result


def _register_claude_mcp() -> Path:
    settings_path = Path.home() / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
    mcp_servers = dict(data.get("mcpServers", {}))
    mcp_servers["cronctl"] = {"command": "cronctl", "args": ["mcp"]}
    data["mcpServers"] = mcp_servers
    settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return settings_path


def _has_module(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False

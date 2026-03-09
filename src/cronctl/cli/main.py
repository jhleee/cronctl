from __future__ import annotations

from pathlib import Path

import click

from cronctl.cli.jobs import add, disable, edit, enable, list_jobs, remove_job
from cronctl.cli.notify import notify
from cronctl.cli.run import exec_job, logs, status
from cronctl.cli.system import doctor, export, gc, import_jobs, init, sync


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--json", "output_json", is_flag=True, help="Machine-readable JSON output")
@click.option(
    "--home",
    type=click.Path(path_type=Path),
    envvar="CRONCTL_HOME",
    default=Path("~/.cronctl"),
    show_default=True,
    help="cronctl home directory",
)
@click.pass_context
def cli(ctx: click.Context, output_json: bool, home: Path) -> None:
    """Local cron job manager."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = output_json
    ctx.obj["home"] = home.expanduser()


@cli.command(name="mcp")
@click.pass_context
def mcp_command(ctx: click.Context) -> None:
    """Start the MCP server."""
    from cronctl.mcp.server import serve_mcp

    serve_mcp(Path(ctx.obj["home"]))


cli.add_command(init)
cli.add_command(add)
cli.add_command(remove_job)
cli.add_command(edit)
cli.add_command(list_jobs)
cli.add_command(enable)
cli.add_command(disable)
cli.add_command(sync)
cli.add_command(exec_job)
cli.add_command(logs)
cli.add_command(status)
cli.add_command(notify)
cli.add_command(export)
cli.add_command(import_jobs)
cli.add_command(gc)
cli.add_command(doctor)


def main() -> None:
    cli(obj={})

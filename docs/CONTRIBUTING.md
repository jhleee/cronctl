# Contributing to cronctl

## Development Setup

```bash
git clone https://github.com/jhleee/cronctl.git
cd cronctl
uv sync --dev
```

## Running Tests

```bash
uv run pytest                    # all tests
uv run pytest tests/test_db.py   # single module
uv run pytest -x                 # stop on first failure
```

## Linting & Type Checking

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run mypy src/
```

## Project Layout

```
src/cronctl/
├── __init__.py
├── __main__.py        # Entry point, calls cli.main()
├── cli/
│   ├── __init__.py    # Click group registration
│   ├── main.py        # Top-level group, global options
│   ├── jobs.py        # add, remove, edit, list, enable, disable
│   ├── run.py         # exec, logs, status
│   ├── system.py      # init, sync, export, import, gc, doctor
│   └── notify.py      # notify setup, notify test
├── core/
│   ├── models.py      # Dataclasses: Job, RunResult, RetryPolicy, NotifyChannel
│   ├── job_manager.py # YAML CRUD + crontab sync
│   ├── executor.py    # Subprocess execution + retry + notification
│   ├── db.py          # SQLite operations
│   └── notifier.py    # Discord / Slack / webhook dispatcher
├── mcp/
│   └── server.py      # MCP stdio server (optional dep)
└── skill/
    └── SKILL.md       # Skill manifest template
```

## Design Rules

These rules keep cronctl lightweight and predictable:

1. **No daemon processes.** cronctl must never require a long-running process. System cron is the scheduler.
2. **Core has minimal dependencies.** click + PyYAML + SQLite only. MCP and notifications are optional extras.
3. **All interfaces share one core.** CLI, MCP, and any future interface must call the same core functions. No duplicated logic.
4. **YAML is the source of truth for jobs.** Never read job definitions from crontab or SQLite. Always from YAML files.
5. **`cronctl exec` is the single execution path.** Whether cron calls it or a user calls it, the behavior and logging must be identical.
6. **`--json` on everything.** Every CLI command that produces output must support `--json` for machine consumption.
7. **Optional features degrade gracefully.** If `httpx` isn't installed, notification commands print a hint. If `mcp` isn't installed, `cronctl mcp` does the same. Never crash.

## Adding a New CLI Command

1. Determine which submodule it belongs to (`jobs.py`, `run.py`, `system.py`, `notify.py`)
2. Add the click command with appropriate decorators
3. Implement the core logic in the appropriate `core/` module
4. Wire the CLI handler to the core function
5. Handle `--json` output via the context `ctx.obj["json"]`
6. Write tests using `click.testing.CliRunner`
7. Update README.md CLI Reference table

**Example:**
```python
# cli/system.py
@click.command()
@click.option("--days", default=30, help="Delete logs older than N days")
@click.pass_context
def gc(ctx, days):
    """Garbage collect old log entries."""
    deleted = db.gc(days=days)
    if ctx.obj["json"]:
        click.echo(json.dumps({"deleted": deleted, "days": days}))
    else:
        click.echo(f"Deleted {deleted} log entries older than {days} days.")
```

## Adding a New MCP Tool

1. Add the core function if it doesn't exist
2. Add the tool handler in `mcp/server.py`
3. Define the input schema (JSON Schema)
4. Write tests using the MCP test client
5. Update MCP.md documentation

## Commit Messages

Use conventional commits:

```
feat: add cronctl gc command for log cleanup
fix: handle missing YAML file in executor
docs: update MCP tool schemas
test: add retry exhaustion test case
refactor: extract crontab sync into separate function
```

## Pull Request Process

1. Fork and create a feature branch from `main`
2. Ensure all tests pass: `uv run pytest`
3. Ensure no lint errors: `uv run ruff check`
4. Ensure types check: `uv run mypy src/`
5. Update documentation if behavior changes
6. Submit PR with a clear description of what and why

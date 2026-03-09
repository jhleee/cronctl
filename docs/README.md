# cronctl

A lightweight, AI-agent-compatible cron job manager for local environments.

**cronctl** wraps system crontab with structured job definitions, execution logging, and machine-friendly interfaces — CLI, MCP Server, and Skill manifest — so both humans and AI agents can manage scheduled tasks through a single tool.

## Current Status

The repository currently implements the core CLI, execution engine, notifications, MCP server, skill template, import/export flow, and a basic test suite. The examples in `docs/wiki/` were captured from real command executions against the current codebase.

## Why cronctl?

Existing cron managers fall into two camps: heavyweight orchestrators (Airflow, Prefect) that are overkill for local tasks, and MCP-based schedulers that run their own daemon and die when the process stops. cronctl takes a different approach:

- **System cron does the scheduling.** No daemon to babysit. If cron runs, your jobs run.
- **cronctl does everything else.** Structured job definitions, execution logs, retry, timeout, and CRUD — all through a single CLI.
- **AI agents are first-class users.** MCP Server, Skill manifest, and `--json` output make cronctl a native tool for Claude Code, Cursor, and any MCP-compatible agent.

## Features

- **YAML-based job definitions** — one file per job, single source of truth
- **SQLite execution log** — every run recorded with exit code, duration, stdout/stderr
- **Retry & timeout** — configurable per job, handled by the execution wrapper
- **Crontab sync** — auto-generates crontab entries from job definitions, never touches your existing cron entries
- **Notification hooks** — Discord, Slack, custom webhook on failure (optional)
- **Interactive onboarding** — `cronctl init` walks you through setup step by step
- **MCP Server** — stdio transport, 7 tools for full CRUD + monitoring
- **Skill manifest** — SKILL.md for AI agent context injection
- **Lightweight deps** — click + PyYAML + SQLite, notifications are optional

## Documentation Map

- [`../README.md`](../README.md) — repository overview and current quick start
- [`wiki/README.md`](wiki/README.md) — wiki index
- [`wiki/QUICKSTART.md`](wiki/QUICKSTART.md) — step-by-step walkthrough
- [`wiki/CLI-IO.md`](wiki/CLI-IO.md) — command-by-command I/O examples from real runs
- [`SKILLS.md`](SKILLS.md) — cross-client skill compatibility notes for Claude-style skills, OpenCode, and OpenClaw
- [`MCP.md`](MCP.md) — MCP tools, resources, and setup notes
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — implementation structure and core flow
- [`ROADMAP.md`](ROADMAP.md) — completed work and remaining gaps

## Agent Bootstrap Assets

The repository now includes the minimum assets an agent usually needs to self-bootstrap from a cold checkout:

- `.python-version`
- `uv.lock`
- `install.sh`
- `scripts/bootstrap.sh`
- `Makefile`
- `.mcp.json.example`
- `.claude/settings.cronctl.json.example`

## Quick Start

```bash
# Remote bootstrap from the public repository
bash <(curl -fsSL https://raw.githubusercontent.com/jhleee/cronctl/main/install.sh)
cd "${XDG_DATA_HOME:-$HOME/.local/share}/cronctl/repo"

# Or from source
git clone https://github.com/jhleee/cronctl.git
cd cronctl
./scripts/bootstrap.sh

# Sanity check the environment
uv run python -m cronctl --json doctor

# Non-interactive setup
uv run python -m cronctl init --non-interactive

# Create and register a job
uv run python -m cronctl add \
    --id backup-db \
    --schedule "0 3 * * *" \
    --command "$HOME/.cronctl/scripts/backup-db.sh"

# Run it immediately
uv run python -m cronctl exec backup-db

# Check logs and overall status
uv run python -m cronctl logs backup-db --last 5
uv run python -m cronctl status
```

## Installation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
# Install via the public raw script
bash <(curl -fsSL https://raw.githubusercontent.com/jhleee/cronctl/main/install.sh)

# Or bootstrap from a checkout
git clone https://github.com/jhleee/cronctl.git && cd cronctl && ./scripts/bootstrap.sh

# Run without installing globally
uv run python -m cronctl --help
```

## CLI Reference

All output-producing commands support the global `--json` flag for machine-readable output. Built with [click](https://click.palletsprojects.com/).

| Command | Description |
|---------|-------------|
| `cronctl init [--non-interactive]` | Create the home layout, write config, optionally register MCP and copy skill |
| `cronctl add` | Create a job from flags or a YAML file |
| `cronctl remove <job_id>` | Delete a job and its crontab entry |
| `cronctl edit <job_id> --set key=value` | Update supported job fields inline (`description`, `schedule`, `command`, `timeout`, `enabled`, `notify`, `retry.*`, `tags`, `env.*`) |
| `cronctl list [--tag=TAG] [--status=all|enabled|disabled]` | List registered jobs |
| `cronctl enable <job_id>` | Enable a disabled job |
| `cronctl disable <job_id>` | Disable a job without removing it |
| `cronctl sync` | Regenerate crontab from all job definitions |
| `cronctl exec <job_id>` | Run a job immediately through the same execution path cron uses |
| `cronctl logs <job_id> [--last=N] [--status-filter=...]` | Show execution history |
| `cronctl status` | Overview: job count, recent failures, next runs |
| `cronctl mcp` | Start MCP server (stdio transport) |
| `cronctl notify test` | Send a test notification to configured channels |
| `cronctl notify setup [--replace]` | Configure notification channels interactively or via flags |
| `cronctl export [--output=FILE]` | Export all jobs as YAML |
| `cronctl import <file> [--replace]` | Import jobs from exported YAML |
| `cronctl gc [--days=30]` | Garbage collect old log entries |
| `cronctl doctor` | Report basic environment diagnostics: home, config/db presence, cron/crontab, optional deps |

## AI Agent Integration

cronctl provides three layers of AI compatibility:

### 1. CLI with `--json`

Any agent that can execute shell commands can use cronctl. All commands produce structured JSON output with `--json`.

```bash
cronctl --json status | jq '.failed_jobs'
cronctl --json logs backup-db --last=3
```

### 2. MCP Server

cronctl ships an MCP (Model Context Protocol) server for direct tool integration with Claude Code, Cursor, and other MCP-compatible environments.

```bash
# Start manually
cronctl mcp

# Or register in Claude Code settings
# ~/.claude/settings.json
{
  "mcpServers": {
    "cronctl": {
      "command": "cronctl",
      "args": ["mcp"]
    }
  }
}
```

Available MCP tools: `cronctl_list_jobs`, `cronctl_create_job`, `cronctl_delete_job`, `cronctl_update_job`, `cronctl_run_job`, `cronctl_get_logs`, `cronctl_system_status`

### 3. Skill Manifest

For agents that use context injection, cronctl provides an AgentSkills-compatible `cronctl/SKILL.md`:

```bash
cronctl init --skill-path /path/to/project/.claude/skills/
```

This writes `/path/to/project/.claude/skills/cronctl/SKILL.md` so the agent knows when and how to use cronctl.

Other common targets:

```bash
cronctl init --skill-path /path/to/project/.opencode/skills/
cronctl init --skill-path /path/to/project/skills/
```

See [`SKILLS.md`](SKILLS.md) for cross-client compatibility notes.

## Configuration

### Global Config (`~/.cronctl/config.yaml`)

```yaml
log_retention_days: 30
max_log_lines: 200
default_timeout: 600
default_retry:
  max_attempts: 1
  delay: 30

notifications:
  on_failure: true       # send notification when a job fails (after all retries)
  on_timeout: true       # send notification on timeout
  on_recovery: false     # send notification when a previously-failed job succeeds
  channels:
    - type: discord
      webhook_url: "https://discord.com/api/webhooks/..."
    - type: slack
      webhook_url: "https://hooks.slack.com/services/..."
    - type: webhook
      url: "https://example.com/hook"
      method: POST
      headers:
        Authorization: "Bearer ..."

hooks:
  on_failure: "~/.cronctl/hooks/on-failure.sh"  # shell hook (always available, no deps)
```

### Job Definition (`~/.cronctl/jobs/<job_id>.yaml`)

```yaml
id: backup-db
description: "PostgreSQL daily backup"
schedule: "0 3 * * *"
command: "~/.cronctl/scripts/backup-db.sh"
timeout: 300
retry:
  max_attempts: 3
  delay: 60
env:
  DB_HOST: localhost
  DB_NAME: myapp
tags: ["db", "backup"]
enabled: true
```

## How It Works

### Execution Flow

When cron fires, it calls `cronctl exec <job_id>`. This is the same entry point used for manual runs, so behavior is always identical.

```
cron → cronctl exec <job_id>
         ├─ Load job YAML
         ├─ Record run start in SQLite
         ├─ Execute command (subprocess)
         │    ├─ Capture stdout/stderr
         │    └─ Enforce timeout
         ├─ Record result in SQLite
         └─ On failure: retry loop → hook
```

### Crontab Sync

cronctl manages a fenced region in your crontab. Existing entries are never touched.

```
# your existing cron entries stay here
0 12 * * * /usr/bin/something

# --- CRONCTL MANAGED START ---
0 3 * * * cronctl exec backup-db 2>&1
*/30 * * * * cronctl exec sync-s3 2>&1
# --- CRONCTL MANAGED END ---
```

## Project Structure

```
cronctl/
├── pyproject.toml
├── README.md
├── src/
│   └── cronctl/
│       ├── __init__.py
│       ├── __main__.py        # Entry point
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py        # Top-level group, global options
│       │   ├── jobs.py        # add, remove, edit, list, enable, disable
│       │   ├── run.py         # exec, logs, status
│       │   ├── system.py      # init, sync, export, import, gc, doctor
│       │   ├── notify.py      # notify setup, notify test
│       │   └── support.py     # shared CLI helpers
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py      # home/config management
│       │   ├── cron.py        # cron expression parsing / next-run calculation
│       │   ├── models.py      # Job, RunResult, RetryPolicy, NotifyChannel
│       │   ├── job_manager.py # YAML CRUD, crontab sync
│       │   ├── executor.py    # Run, retry, timeout
│       │   ├── db.py          # SQLite operations
│       │   ├── notifier.py    # Notification dispatcher
│       │   ├── runtime.py     # service wiring
│       │   └── utils.py       # shared helpers
│       ├── mcp/
│       │   ├── __init__.py
│       │   └── server.py      # MCP stdio server
│       └── skill/
│           ├── __init__.py
│           └── SKILL.md       # Skill manifest template
├── tests/
│   ├── conftest.py
│   ├── test_cli.py
│   └── test_core.py
└── docs/
    ├── ARCHITECTURE.md
    ├── MCP.md
    ├── SKILL.md
    └── wiki/
```

## Development

```bash
git clone https://github.com/jhleee/cronctl.git
cd cronctl
uv sync --dev
uv run pytest
uv run python -m cronctl --help
```

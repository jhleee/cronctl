# cronctl

A lightweight, AI-agent-compatible cron job manager for local environments.

**cronctl** wraps system crontab with structured job definitions, execution logging, and machine-friendly interfaces — CLI, MCP Server, and Skill manifest — so both humans and AI agents can manage scheduled tasks through a single tool.

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

## Quick Start

```bash
# Install
uv tool install cronctl

# Interactive setup — creates ~/.cronctl/, detects cron, configures notifications
cronctl init

# Create and register a job
cronctl add --id backup-db \
            --schedule "0 3 * * *" \
            --command "$HOME/.cronctl/scripts/backup-db.sh"

# Test it
cronctl exec backup-db

# Check logs
cronctl logs backup-db --last=5

# See overall status
cronctl status
```

## Installation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
# As a CLI tool (recommended)
uv tool install cronctl

# With notification support (Discord, Slack)
uv tool install "cronctl[notify]"

# With everything (MCP + notifications)
uv tool install "cronctl[all]"

# As a project dependency
uv add cronctl

# From source
git clone https://github.com/yourname/cronctl.git
cd cronctl
uv sync
```

## CLI Reference

All commands support `--json` for machine-readable output. Built with [click](https://click.palletsprojects.com/).

| Command | Description |
|---------|-------------|
| `cronctl init` | Interactive setup: directory, cron detection, notifications |
| `cronctl add` | Create a job from flags or a YAML file |
| `cronctl remove <job_id>` | Delete a job and its crontab entry |
| `cronctl edit <job_id> --set key=value` | Update job properties |
| `cronctl list [--tag=TAG]` | List registered jobs |
| `cronctl enable <job_id>` | Enable a disabled job |
| `cronctl disable <job_id>` | Disable a job without removing it |
| `cronctl sync` | Regenerate crontab from all job definitions |
| `cronctl exec <job_id>` | Run a job immediately (same path as cron) |
| `cronctl logs <job_id> [--last=N]` | Show execution history |
| `cronctl status` | Overview: job count, recent failures, next runs |
| `cronctl mcp` | Start MCP server (stdio transport) |
| `cronctl notify test` | Send a test notification to configured channels |
| `cronctl notify setup` | Interactive notification channel configuration |
| `cronctl export` | Export all jobs as a single YAML |
| `cronctl import <file>` | Import jobs from exported YAML |
| `cronctl gc [--days=30]` | Garbage collect old log entries |
| `cronctl doctor` | Diagnose common issues (cron running, PATH, permissions) |

## AI Agent Integration

cronctl provides three layers of AI compatibility:

### 1. CLI with `--json`

Any agent that can execute shell commands can use cronctl. All commands produce structured JSON output with `--json`.

```bash
cronctl status --json | jq '.failed_jobs'
cronctl logs backup-db --last=3 --json
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

For agents that use context injection (like Claude Code's CLAUDE.md or project skills), cronctl provides a SKILL.md:

```bash
cronctl init --skill-path /path/to/project/.claude/skills/
```

This copies the skill manifest so the agent knows when and how to use cronctl.

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
├── LICENSE
├── src/
│   └── cronctl/
│       ├── __init__.py
│       ├── __main__.py        # Entry point
│       ├── cli/
│       │   ├── __init__.py    # Click group + plugin loading
│       │   ├── main.py        # Top-level group, global options
│       │   ├── jobs.py        # add, remove, edit, list, enable, disable
│       │   ├── run.py         # exec, logs, status
│       │   ├── system.py      # init, sync, export, import, gc, doctor
│       │   └── notify.py      # notify setup, notify test
│       ├── core/
│       │   ├── __init__.py
│       │   ├── models.py      # Job, RunResult, RetryPolicy, NotifyChannel
│       │   ├── job_manager.py # YAML CRUD, crontab sync
│       │   ├── executor.py    # Run, retry, timeout
│       │   ├── db.py          # SQLite operations
│       │   └── notifier.py    # Notification dispatcher
│       ├── mcp/
│       │   ├── __init__.py
│       │   └── server.py      # MCP stdio server
│       └── skill/
│           └── SKILL.md       # Skill manifest template
├── tests/
│   ├── test_models.py
│   ├── test_job_manager.py
│   ├── test_executor.py
│   ├── test_db.py
│   ├── test_cli.py
│   ├── test_notifier.py
│   └── test_mcp.py
└── docs/
    ├── ARCHITECTURE.md
    ├── MCP.md
    └── SKILL.md
```

## Development

```bash
git clone https://github.com/yourname/cronctl.git
cd cronctl
uv sync --dev
uv run pytest
uv run cronctl --help
```

## License

MIT

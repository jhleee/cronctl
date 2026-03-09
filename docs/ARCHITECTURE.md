# Architecture

## Design Principles

1. **Cron is the scheduler.** cronctl never runs a daemon. System cron handles timing; cronctl handles everything else.
2. **YAML is the source of truth.** Crontab entries are derived artifacts, regenerated on every sync.
3. **Single execution path.** `cronctl exec` is the only way jobs run — whether triggered by cron or manually. This guarantees logging consistency.
4. **AI agents are users, not special cases.** CLI, MCP, and Skill are three interfaces to the same core. No interface has privileged access.
5. **Minimal dependencies.** click + PyYAML + SQLite for core. MCP SDK and httpx (notifications) are optional extras.

## Component Overview

```
┌──────────────────────────────────────────────────┐
│                   Interfaces                      │
│                                                   │
│   CLI (click)      MCP Server      Skill.md       │
│       │               │              │            │
│       └───────┬───────┘              │            │
│               │               (documentation)     │
│               ▼                                   │
│        ┌──────────────┐                           │
│        │     Core     │                           │
│        │              │                           │
│        │ JobManager   │  YAML CRUD + sync         │
│        │ Executor     │  run + retry + timeout    │
│        │ DB           │  SQLite log store          │
│        │ Notifier     │  Discord / Slack / webhook │
│        │ Models       │  dataclasses               │
│        └──────────────┘                           │
│               │                                   │
│               ▼                                   │
│  ┌────────┐ ┌──────────┐ ┌────────────┐          │
│  │ YAML   │ │ SQLite   │ │ system     │          │
│  │ files  │ │ log DB   │ │ cron       │          │
│  └────────┘ └──────────┘ └────────────┘          │
└──────────────────────────────────────────────────┘
```

## Core Modules

### models.py

Defines the data structures used across all modules.

```python
@dataclass
class Job:
    id: str                    # kebab-case identifier
    schedule: str              # cron expression (5-field)
    command: str               # shell command to execute
    description: str = ""
    timeout: int | None = None # seconds, None = use global default
    retry: RetryPolicy | None = None
    env: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    enabled: bool = True
    notify: bool | None = None # per-job override; None = use global setting

@dataclass
class RetryPolicy:
    max_attempts: int = 1
    delay: int = 30            # seconds between retries

@dataclass
class NotifyChannel:
    type: str                  # "discord" | "slack" | "webhook"
    webhook_url: str = ""      # for discord/slack
    url: str = ""              # for generic webhook
    method: str = "POST"       # for generic webhook
    headers: dict[str, str] = field(default_factory=dict)

@dataclass
class RunResult:
    run_id: str                # ULID or timestamp-based
    job_id: str
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int | None = None
    exit_code: int | None = None
    status: RunStatus = RunStatus.RUNNING
    attempt: int = 1
    stdout: str = ""
    stderr: str = ""
    error_msg: str = ""        # timeout, signal, etc.

class RunStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRYING = "retrying"
```

### job_manager.py

Handles CRUD operations on job YAML files and crontab synchronization.

**Responsibilities:**
- Load/save/delete job YAML files in `~/.cronctl/jobs/`
- Validate job definitions (id format, cron expression, command existence)
- Sync job definitions to crontab (fenced region only)
- List jobs with optional filtering (tag, enabled/disabled)

**Crontab sync algorithm:**
1. Read current crontab (`crontab -l`)
2. Find `CRONCTL MANAGED START/END` markers
3. Preserve everything outside the markers
4. Generate new entries from enabled jobs
5. Write back (`crontab -`)
6. If markers don't exist, append them at the end

**Job ID rules:**
- Lowercase alphanumeric + hyphens only
- Must start with a letter
- Max 64 characters
- Must be unique across all jobs
- Regex: `^[a-z][a-z0-9-]{0,63}$`

### executor.py

Runs a job and records the result. This is the core execution engine.

**Execution sequence:**

```
def execute(job_id: str) -> RunResult:
    job = job_manager.load(job_id)
    run_id = generate_run_id()
    
    db.insert_run(run_id, job_id, status=RUNNING)
    
    for attempt in range(1, max_attempts + 1):
        result = _run_subprocess(job, attempt)
        
        if result.status == SUCCESS:
            db.update_run(run_id, result)
            # Recovery notification: job was failing, now succeeded
            if _was_previously_failing(job_id) and config.notifications.on_recovery:
                notifier.send(job, result, event="recovery")
            return result
        
        if attempt < max_attempts:
            db.update_run(run_id, status=RETRYING, attempt=attempt)
            time.sleep(retry_delay)
    
    # All retries exhausted
    db.update_run(run_id, result)
    _run_hook("on_failure", job, result)        # shell hook (always)
    notifier.send(job, result, event="failure") # channel notifications (if configured)
    return result
```

**Subprocess management:**
- Uses `subprocess.Popen` with `stdout=PIPE, stderr=PIPE`
- Timeout via `process.wait(timeout=job.timeout)`
- On timeout: `process.kill()`, then `process.wait()`, status = TIMEOUT
- Environment: merge `os.environ` + `job.env`
- Working directory: user's home
- Shell: `/bin/sh -c` (consistent with cron)

**Log truncation:**
- stdout/stderr are captured in full during execution
- Before writing to DB, truncate to `config.max_log_lines` (tail)
- Truncation is noted in `error_msg` field

### db.py

SQLite operations for the execution log.

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS job_runs (
    run_id      TEXT PRIMARY KEY,
    job_id      TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    duration_ms INTEGER,
    exit_code   INTEGER,
    status      TEXT NOT NULL,
    attempt     INTEGER DEFAULT 1,
    stdout      TEXT,
    stderr      TEXT,
    error_msg   TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_job_runs_job_id ON job_runs(job_id);
CREATE INDEX IF NOT EXISTS idx_job_runs_started ON job_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_job_runs_status ON job_runs(status);
```

**Design decisions:**
- **stdout/stderr in DB, not files.** One fewer thing to manage. AI agents can query logs with a single command. Trade-off: DB size grows, mitigated by `max_log_lines` and `gc` command.
- **No WAL mode by default.** Single writer (cronctl exec) is the typical pattern. WAL can be enabled in config if concurrent access is needed.
- **ISO 8601 timestamps.** Sortable, unambiguous, timezone-aware.
- **ULID for run_id.** Lexicographically sortable, embeds timestamp, no collisions.

**Garbage collection:**
```sql
DELETE FROM job_runs
WHERE created_at < datetime('now', '-{days} days');
VACUUM;
```

### notifier.py

Dispatches notifications to configured channels when jobs fail, timeout, or recover.

**Architecture:**
- Notification sending is fire-and-forget — it must never block or crash the execution flow
- All errors are logged, never raised
- If the `notify` optional dependency (`httpx`) is not installed, the module degrades gracefully (logs a warning, does nothing)

**Channel types:**

| Type | Transport | Payload |
|------|-----------|---------|
| `discord` | POST to webhook URL | Discord embed object (colored by status) |
| `slack` | POST to webhook URL | Slack Block Kit message |
| `webhook` | Configurable method/headers | Generic JSON payload |

**Discord payload:**
```python
{
    "embeds": [{
        "title": f"cronctl — {event_type}",
        "description": f"Job `{job.id}` {status}",
        "color": 0xE74C3C if failed else 0x2ECC71,  # red / green
        "fields": [
            {"name": "Exit Code", "value": str(result.exit_code), "inline": True},
            {"name": "Duration", "value": f"{result.duration_ms}ms", "inline": True},
            {"name": "Attempt", "value": str(result.attempt), "inline": True},
            {"name": "stderr (tail)", "value": f"```{result.stderr[-500:]}```"},
        ],
        "timestamp": result.finished_at.isoformat()
    }]
}
```

**Slack payload:**
```python
{
    "blocks": [
        {"type": "header", "text": {"type": "plain_text", "text": f"cronctl — {event_type}"}},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"*Job:* `{job.id}`\n*Status:* {status}\n*Exit:* {result.exit_code}"}},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"```{result.stderr[-500:]}```"}}
    ]
}
```

**Generic webhook payload:**
```python
{
    "event": "job_failure",       # or "job_timeout", "job_recovery"
    "job_id": job.id,
    "job_description": job.description,
    "status": result.status,
    "exit_code": result.exit_code,
    "duration_ms": result.duration_ms,
    "attempt": result.attempt,
    "stderr_tail": result.stderr[-500:],
    "timestamp": result.finished_at.isoformat()
}
```

**Per-job override:**
Jobs can set `notify: false` to suppress notifications, or `notify: true` to force them even if globally disabled. `notify: null` (default) follows the global setting.

**Event types and triggers:**

| Event | Trigger | Config key |
|-------|---------|------------|
| `failure` | All retries exhausted, final status FAILED | `notifications.on_failure` |
| `timeout` | Job killed by timeout | `notifications.on_timeout` |
| `recovery` | Job succeeds after previous consecutive failures | `notifications.on_recovery` |

## Interfaces

### CLI (cli/)

Built with [click](https://click.palletsprojects.com/). Split into submodules by domain.

**Module structure:**

```
cli/
├── __init__.py    # Click group, registers subcommands
├── main.py        # @click.group(), global --json option, context setup
├── jobs.py        # add, remove, edit, list, enable, disable
├── run.py         # exec, logs, status
├── system.py      # init, sync, export, import, gc, doctor
└── notify.py      # notify setup, notify test
```

**Why click over argparse:**
- Declarative command definition reduces boilerplate
- Built-in support for nested groups (`cronctl notify setup`)
- `click.prompt()` and `click.confirm()` for interactive onboarding
- Color/formatting via `click.echo()` and `click.style()`
- Easier to test (CliRunner)

**Output contract:**
- Default: human-readable colored text via `click.echo(click.style(...))`
- `--json`: JSON object with consistent structure, no color codes
- Exit codes: 0 = success, 1 = error, 2 = job execution failed

**Global context pattern:**

```python
@click.group()
@click.option("--json", "output_json", is_flag=True, help="Machine-readable JSON output")
@click.option("--home", type=click.Path(), envvar="CRONCTL_HOME", default="~/.cronctl")
@click.pass_context
def cli(ctx, output_json, home):
    ctx.ensure_object(dict)
    ctx.obj["json"] = output_json
    ctx.obj["home"] = Path(home).expanduser()
```

### Onboarding (`cronctl init`)

Interactive setup flow using click prompts. Designed for both first-time users and AI agents (supports `--non-interactive` for automated setup).

**Interactive flow:**

```
$ cronctl init

  cronctl — Local Cron Job Manager

  [1/4] Creating directory structure...
        ~/.cronctl/jobs/
        ~/.cronctl/scripts/
        ~/.cronctl/hooks/
        ~/.cronctl/logs/
        ✓ Done

  [2/4] Checking system cron...
        ✓ cron is running (crond, PID 1234)
        ✓ Current user can write crontab

  [3/4] Notifications (optional)
        Set up Discord/Slack notifications? [y/N]: y
        
        Channel type [discord/slack/webhook]: discord
        Webhook URL: https://discord.com/api/webhooks/...
        Sending test notification... ✓ Delivered
        
        Add another channel? [y/N]: n

  [4/4] AI Agent integration (optional)
        Set up MCP server for Claude Code? [y/N]: y
        ✓ Added to ~/.claude/settings.json
        
        Copy SKILL.md to a project? [y/N]: n

  ✓ cronctl is ready. Try: cronctl add --id hello --schedule "* * * * *" --command "echo hello"
```

**Non-interactive mode (for AI agents):**

```bash
cronctl init --non-interactive
cronctl init --non-interactive --discord-webhook "https://..."
cronctl init --non-interactive --slack-webhook "https://..."
```

**JSON output structure (example for `cronctl status --json`):**

```json
{
  "total_jobs": 5,
  "enabled": 4,
  "disabled": 1,
  "recent_runs": {
    "last_24h": 12,
    "success": 10,
    "failed": 2
  },
  "failed_jobs": [
    {
      "job_id": "backup-db",
      "last_failure": "2025-01-15T03:01:23Z",
      "exit_code": 1,
      "consecutive_failures": 3
    }
  ]
}
```

### MCP Server (mcp/server.py)

Implements MCP stdio transport using the `mcp` Python SDK.

**Transport:** stdio (no HTTP, no ports, no daemon). The MCP client (Claude Code, Cursor, etc.) launches `cronctl mcp` as a child process.

**Tools exposed:**

| Tool | Core function | Description |
|------|--------------|-------------|
| `cronctl_list_jobs` | `job_manager.list()` | List jobs with optional filters |
| `cronctl_create_job` | `job_manager.create()` | Create a job from parameters |
| `cronctl_delete_job` | `job_manager.delete()` | Remove a job |
| `cronctl_update_job` | `job_manager.update()` | Modify job properties |
| `cronctl_run_job` | `executor.execute()` | Run immediately, return result |
| `cronctl_get_logs` | `db.get_runs()` | Query execution history |
| `cronctl_system_status` | `db.status_summary()` | Aggregate overview |

**Resources exposed:**

| Resource | URI | Description |
|----------|-----|-------------|
| Job list | `cronctl://jobs` | All job definitions |
| Job detail | `cronctl://jobs/{id}` | Single job YAML content |
| Config | `cronctl://config` | Global configuration |

**Error handling:**
- Invalid job_id → MCP error response with descriptive message
- Execution failure → success response with failure details in content (not an MCP error, because the tool worked correctly)

### Skill Manifest (skill/SKILL.md)

A markdown document that provides AI agents with context about cronctl: when to use it, what workflows to follow, and what conventions to respect.

**Placement options:**
- `~/.claude/skills/cronctl.md` for Claude Code
- Project `.claude/skills/` for project-scoped agents
- System prompt injection for custom agent frameworks
- `cronctl init --skill-path <dir>` copies it automatically

## Directory Layout

```
~/.cronctl/                    # XDG_DATA_HOME/cronctl in future
├── config.yaml                # Global settings + notification channels
├── jobs/                      # Job definitions (YAML)
│   ├── backup-db.yaml
│   └── sync-s3.yaml
├── scripts/                   # User scripts (optional convention)
│   ├── backup-db.sh
│   └── sync-s3.py
├── hooks/                     # Event hooks (shell scripts)
│   └── on-failure.sh
└── logs/
    └── cronctl.db             # SQLite execution log
```

**Why `~/.cronctl/` and not XDG?**
Simplicity for v1. The path is configurable via `CRONCTL_HOME` environment variable. XDG compliance can be added later without breaking existing installations.

## Error Handling Strategy

### Job execution errors

| Scenario | Behavior |
|----------|----------|
| Command not found | status=FAILED, error_msg explains |
| Non-zero exit | status=FAILED, exit_code recorded |
| Timeout | SIGKILL, status=TIMEOUT |
| Permission denied | status=FAILED, stderr captured |
| Retry exhausted | Final status=FAILED, hook fired |

### System errors

| Scenario | Behavior |
|----------|----------|
| Job YAML not found | CLI error exit 1, MCP error response |
| SQLite locked | Retry with backoff (3 attempts) |
| Crontab write failed | CLI error, no partial write |
| Invalid cron expression | Rejected at creation time |

## Concurrency

cronctl does not implement its own locking. If the same job is scheduled to run while a previous instance is still running, both will execute. This matches standard cron behavior.

For jobs that must not overlap, users can use `flock` in their command:

```yaml
command: "flock -n /tmp/backup-db.lock ~/.cronctl/scripts/backup-db.sh"
```

A future version may add a `singleton: true` option that wraps commands with flock automatically.

## Security Considerations

- Jobs execute with the current user's permissions (same as crontab)
- No root access required or requested
- SQLite DB is user-readable only (0600 permissions set on creation)
- Environment variables in YAML are stored in plaintext — secrets should use external references (e.g., `command: "source ~/.secrets && ./script.sh"`)
- MCP server runs as a child process, inheriting the parent's permissions
- No network listeners (stdio only)

## Future Considerations (out of scope for v1)

- `singleton: true` — auto-flock for non-overlapping execution
- Job dependency chains — `depends_on: [job-a, job-b]`
- Read-only web status viewer (single HTML file, no server)
- Additional notification channels — Telegram, email, PagerDuty
- XDG base directory compliance
- `cronctl doctor` — diagnose common issues (cron not running, PATH problems)
- Import from existing crontab — parse raw crontab into job YAMLs

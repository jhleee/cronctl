# Quick Start

This page walks through the shortest path from a fresh checkout to a working local job.

## 1. Install and run from source

```bash
git clone https://github.com/jhleee/cronctl.git
cd cronctl
uv sync
uv run python -m cronctl --help
```

If you want a dedicated tool entry instead of `uv run`, install the checkout itself:

```bash
uv tool install .
```

## 2. Initialize the cronctl home

For local automation and CI, the safest default is non-interactive setup:

```bash
uv run python -m cronctl --home /tmp/cronctl-docs-home-init --json init --non-interactive
```

Example output:

```json
{
  "initialized": true,
  "home": "/tmp/cronctl-docs-home-init",
  "jobs_dir": "/tmp/cronctl-docs-home-init/jobs",
  "scripts_dir": "/tmp/cronctl-docs-home-init/scripts",
  "hooks_dir": "/tmp/cronctl-docs-home-init/hooks",
  "db_path": "/tmp/cronctl-docs-home-init/logs/cronctl.db",
  "cron": {
    "crontab_access": true,
    "service": "running"
  },
  "skill_path": null,
  "claude_settings": null
}
```

Use `--register-claude-mcp` if you want `cronctl mcp` written into `~/.claude/settings.json`, and `--skill-path` if you want the skill manifest copied into a project.

## 3. Add a job

```bash
uv run python -m cronctl --home /tmp/cronctl-docs-home --json add \
  --id hello \
  --schedule "* * * * *" \
  --command "printf hello from cronctl" \
  --description "Demo job" \
  --tag demo \
  --env DEMO=1
```

Example output:

```json
{
  "created": true,
  "job_id": "hello",
  "crontab_synced": true,
  "yaml_path": "/tmp/cronctl-docs-home/jobs/hello.yaml"
}
```

## 4. Run it immediately

```bash
uv run python -m cronctl --home /tmp/cronctl-docs-home --json exec hello
```

Example output:

```json
{
  "run_id": "20260309T120305454863Z-ZS0DFRW5",
  "job_id": "hello",
  "started_at": "2026-03-09T12:03:05.455849Z",
  "finished_at": "2026-03-09T12:03:05.468277Z",
  "duration_ms": 12,
  "exit_code": 0,
  "status": "success",
  "attempt": 1,
  "stdout": "hello",
  "stderr": "",
  "error_msg": ""
}
```

## 5. Inspect logs and status

```bash
uv run python -m cronctl --home /tmp/cronctl-docs-home --json logs hello --last 1
uv run python -m cronctl --home /tmp/cronctl-docs-home --json status
```

Status output example:

```json
{
  "total_jobs": 1,
  "enabled": 1,
  "disabled": 0,
  "recent_runs": {
    "last_24h": 1,
    "success": 1,
    "failed": 0,
    "timeout": 0
  },
  "failed_jobs": [],
  "next_runs": [
    {
      "job_id": "hello",
      "next_at": "2026-03-09T12:04:00+00:00"
    }
  ]
}
```

## 6. Edit jobs carefully

Inline updates use repeated `--set key=value`. If the value contains spaces, quote the whole assignment:

```bash
uv run python -m cronctl --home /tmp/cronctl-docs-home --json edit hello \
  --set 'description=Updated demo job' \
  --set retry.max_attempts=2 \
  --set retry.delay=5
```

Without quoting, the shell will split `description=Updated demo job` into extra arguments and Click will reject the command before `cronctl` sees it.

## 7. Export, import, and notifications

- Export all jobs: `uv run python -m cronctl --home /tmp/cronctl-docs-home export`
- Export to a file: `uv run python -m cronctl --home /tmp/cronctl-docs-home --json export --output jobs.yaml`
- Import from YAML: `uv run python -m cronctl --home /tmp/cronctl-docs-home --json import jobs.yaml`
- Configure notifications: `uv run python -m cronctl --home /tmp/cronctl-docs-home --json notify setup --non-interactive --webhook-url http://127.0.0.1:18765/hook`
- Send a test notification: `uv run python -m cronctl --home /tmp/cronctl-docs-home --json notify test`

## 8. Next pages

- Command-by-command examples: [`CLI-IO.md`](CLI-IO.md)
- MCP usage: [`../MCP.md`](../MCP.md)

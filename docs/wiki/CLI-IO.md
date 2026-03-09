# CLI I/O Examples

This page contains real command examples captured from the current implementation. For reproducibility, the examples used:

```bash
export CRONCTL_CRONTAB_BIN=/tmp/cronctl-docs-fake-crontab
```

and a demo home at `/tmp/cronctl-docs-home`.

## `scripts/bootstrap.sh`

```text
$ ./scripts/bootstrap.sh
==> Ensuring Python 3.11 is available
==> Lockfile status
Using existing uv.lock
==> Syncing project with all extras
==> Bootstrap complete
Next steps:
  uv run python -m cronctl init --non-interactive
  cp .mcp.json.example .mcp.json
  cp .claude/settings.cronctl.json.example ~/.claude/settings.json
```

## `install.sh`

Real run against a local `file://` snapshot and a fake crontab backend:

```text
$ CRONCTL_INSTALL_REPO=file:///tmp/cronctl-install-source \
  CRONCTL_INSTALL_ROOT=/tmp/cronctl-install-root \
  CRONCTL_HOME=/tmp/cronctl-install-home \
  CRONCTL_CRONTAB_BIN=/tmp/cronctl-install-fake-crontab \
  ./install.sh
==> Cloning file:///tmp/cronctl-install-source into /tmp/cronctl-install-root/repo
==> Bootstrapping repository dependencies
==> Ensuring Python 3.11 is available
Python 3.11 is already installed
==> Lockfile status
Using existing uv.lock
==> Syncing project with all extras
Using CPython 3.11.14
Creating virtual environment at: .venv
Resolved 45 packages in 2ms
...
==> Bootstrap complete
Next steps:
  uv run python -m cronctl init --non-interactive
  cp .mcp.json.example .mcp.json
  cp .claude/settings.cronctl.json.example ~/.claude/settings.json
==> Running doctor diagnostics
{
  "ready": true,
  "repo_bootstrap_ready": true,
  "home": "/tmp/cronctl-install-home",
  "python": {
    "version": "3.11.14",
    "executable": "/tmp/cronctl-install-root/repo/.venv/bin/python3",
    "requires": ">=3.11",
    "compatible": true
  },
  "uv": {
    "binary": "/home/ng0301/.local/bin/uv"
  },
  "crontab": {
    "binary": "/tmp/cronctl-install-fake-crontab",
    "readable": true,
    "read_error": null
  },
  "cron": {
    "crontab_access": true,
    "service": "running"
  },
  "paths": {
    "home": "/tmp/cronctl-install-home",
    "home_exists": false,
    "home_writable": true,
    "config_exists": false,
    "jobs_dir_exists": false,
    "scripts_dir_exists": false,
    "hooks_dir_exists": false,
    "logs_dir_exists": false,
    "db_exists": false
  },
  "extras": {
    "notify_available": true,
    "mcp_available": true
  },
  "bootstrap_assets": {
    "python_version_file": true,
    "uv_lock": true,
    "install_script": true,
    "bootstrap_script": true,
    "makefile": true,
    "mcp_example": true,
    "claude_example": true
  },
  "checks": [
    {
      "name": "python",
      "ok": true,
      "detail": "Detected Python 3.11.14; requires >=3.11."
    },
    {
      "name": "uv",
      "ok": true,
      "detail": "uv binary: /home/ng0301/.local/bin/uv"
    },
    {
      "name": "crontab",
      "ok": true,
      "detail": "crontab binary: /tmp/cronctl-install-fake-crontab"
    },
    {
      "name": "home",
      "ok": true,
      "detail": "Home path: /tmp/cronctl-install-home"
    }
  ],
  "next_steps": []
}
==> Initializing cronctl home
Initialized cronctl home at /tmp/cronctl-install-home
==> Install complete
Repository: /tmp/cronctl-install-root/repo
Home: /tmp/cronctl-install-home
```

## `init`

```bash
$ python -m cronctl --home /tmp/cronctl-docs-home-init --json init --non-interactive
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

## `add`

```bash
$ python -m cronctl --home /tmp/cronctl-docs-home --json add --id hello --schedule '* * * * *' --command 'printf hello from cronctl' --description 'Demo job' --tag demo --env DEMO=1
{
  "created": true,
  "job_id": "hello",
  "crontab_synced": true,
  "yaml_path": "/tmp/cronctl-docs-home/jobs/hello.yaml"
}
```

## `list`

Human-readable:

```text
$ python -m cronctl --home /tmp/cronctl-docs-home list
hello [enabled] * * * * * - Demo job
```

JSON:

```json
$ python -m cronctl --home /tmp/cronctl-docs-home --json list --tag demo
{
  "jobs": [
    {
      "id": "hello",
      "description": "Demo job",
      "schedule": "* * * * *",
      "command": "printf hello from cronctl",
      "env": {
        "DEMO": "1"
      },
      "tags": [
        "demo"
      ],
      "enabled": true
    }
  ]
}
```

## `edit`

```json
$ python -m cronctl --home /tmp/cronctl-docs-home --json edit hello --set 'description=Updated demo job' --set retry.max_attempts=2 --set retry.delay=5
{
  "updated": true,
  "job_id": "hello",
  "changes": [
    "description",
    "retry.max_attempts",
    "retry.delay"
  ],
  "crontab_synced": true
}
```

Resulting job definition:

```json
$ python -m cronctl --home /tmp/cronctl-docs-home --json list
{
  "jobs": [
    {
      "id": "hello",
      "description": "Updated demo job",
      "schedule": "* * * * *",
      "command": "printf hello from cronctl",
      "retry": {
        "max_attempts": 2,
        "delay": 5
      },
      "env": {
        "DEMO": "1"
      },
      "tags": [
        "demo"
      ],
      "enabled": true
    }
  ]
}
```

## `enable` / `disable`

```json
$ python -m cronctl --home /tmp/cronctl-docs-home --json disable hello
{
  "updated": true,
  "job_id": "hello",
  "enabled": false,
  "crontab_synced": true
}

$ python -m cronctl --home /tmp/cronctl-docs-home --json enable hello
{
  "updated": true,
  "job_id": "hello",
  "enabled": true,
  "crontab_synced": true
}
```

## `exec`

```json
$ python -m cronctl --home /tmp/cronctl-docs-home --json exec hello
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

## `logs`

```json
$ python -m cronctl --home /tmp/cronctl-docs-home --json logs hello --last 1
{
  "job_id": "hello",
  "runs": [
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
  ]
}
```

## `status`

Human-readable:

```text
$ python -m cronctl --home /tmp/cronctl-docs-home status
Jobs: 1 total, 1 enabled, 0 disabled
Recent runs: 1 in last 24h, 1 success, 0 failed
```

JSON:

```json
$ python -m cronctl --home /tmp/cronctl-docs-home --json status
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

## `export`

Plain YAML:

```yaml
$ python -m cronctl --home /tmp/cronctl-docs-home export
jobs:
- id: hello
  description: Demo job
  schedule: '* * * * *'
  command: printf hello from cronctl
  env:
    DEMO: '1'
  tags:
  - demo
  enabled: true
```

Write to a file:

```json
$ python -m cronctl --home /tmp/cronctl-docs-home --json export --output /tmp/cronctl-docs-export.yaml
{
  "exported": true,
  "path": "/tmp/cronctl-docs-export.yaml",
  "job_count": 1
}
```

## `import`

```json
$ python -m cronctl --home /tmp/cronctl-docs-home --json import /tmp/cronctl-docs-import.yaml
{
  "imported": 1,
  "job_ids": [
    "imported-job"
  ],
  "crontab_synced": true
}
```

## `remove`

```json
$ python -m cronctl --home /tmp/cronctl-docs-home --json remove imported-job
{
  "deleted": true,
  "job_id": "imported-job",
  "crontab_synced": true
}
```

## `gc`

```json
$ python -m cronctl --home /tmp/cronctl-docs-home --json gc --days 0
{
  "deleted": 1,
  "days": 0
}
```

## `doctor`

```json
$ python -m cronctl --home /tmp/cronctl-docs-home --json doctor
{
  "ready": false,
  "repo_bootstrap_ready": true,
  "home": "/tmp/cronctl-docs-home",
  "python": {
    "version": "3.10.12",
    "executable": "/usr/bin/python",
    "requires": ">=3.11",
    "compatible": false
  },
  "uv": {
    "binary": "/home/ng0301/.local/bin/uv"
  },
  "crontab": {
    "binary": "/tmp/cronctl-docs-fake-crontab",
    "readable": true,
    "read_error": null
  },
  "cron": {
    "crontab_access": true,
    "service": "running"
  },
  "paths": {
    "home": "/tmp/cronctl-docs-home",
    "home_exists": true,
    "home_writable": true,
    "config_exists": true,
    "jobs_dir_exists": true,
    "scripts_dir_exists": true,
    "hooks_dir_exists": true,
    "logs_dir_exists": true,
    "db_exists": true
  },
  "extras": {
    "notify_available": true,
    "mcp_available": true
  },
  "bootstrap_assets": {
    "python_version_file": true,
    "uv_lock": true,
    "bootstrap_script": true,
    "makefile": true,
    "mcp_example": true,
    "claude_example": true
  },
  "checks": [
    {
      "name": "python",
      "ok": false,
      "detail": "Detected Python 3.10.12; requires >=3.11."
    },
    {
      "name": "uv",
      "ok": true,
      "detail": "uv binary: /home/ng0301/.local/bin/uv"
    },
    {
      "name": "crontab",
      "ok": true,
      "detail": "crontab binary: /tmp/cronctl-docs-fake-crontab"
    },
    {
      "name": "home",
      "ok": true,
      "detail": "Home path: /tmp/cronctl-docs-home"
    }
  ],
  "next_steps": [
    "Install Python 3.11+ or run ./scripts/bootstrap.sh from the repo root."
  ]
}
```

## `notify setup`

```json
$ python -m cronctl --home /tmp/cronctl-docs-home --json notify setup --non-interactive --replace --webhook-url http://127.0.0.1:18765/hook
{
  "updated": true,
  "channels": [
    {
      "type": "webhook",
      "url": "http://127.0.0.1:18765/hook"
    }
  ]
}
```

## `notify test`

JSON:

```json
$ python -m cronctl --home /tmp/cronctl-docs-home --json notify test
{
  "delivered": 1,
  "failed": 0,
  "errors": []
}
```

Human-readable:

```text
$ python -m cronctl --home /tmp/cronctl-docs-home notify test
Delivered=1 failed=0
```

Captured webhook payload:

```json
$ cat /tmp/cronctl-docs-webhook.log
{"event":"job_test","job_id":"cronctl-test","job_description":"cronctl notification test","status":"success","exit_code":0,"duration_ms":5,"attempt":1,"stderr_tail":"","timestamp":"2026-03-09T12:03:11.430276+00:00"}
```

## `sync`

```json
$ python -m cronctl --home /tmp/cronctl-docs-home --json sync
{
  "synced": true,
  "job_count": 1
}
```

Managed crontab output:

```cron
$ cat /tmp/cronctl-docs-crontab.txt
# --- CRONCTL MANAGED START ---
* * * * * cronctl --home /tmp/cronctl-docs-home exec hello 2>&1
# --- CRONCTL MANAGED END ---
```

## `mcp`

`cronctl mcp` is a long-running stdio server, so the most useful human-facing example is its help output:

```text
$ python -m cronctl mcp --help
Usage: python -m cronctl mcp [OPTIONS]

  Start the MCP server.

Options:
  -h, --help  Show this message and exit.
```

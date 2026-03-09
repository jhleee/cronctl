# cronctl

AI-agent-friendly local cron job manager built around system `cron`.

`cronctl` keeps job definitions in YAML, records executions in SQLite, and exposes one core through three interfaces:

- CLI with `--json`
- MCP server over stdio
- SKILL manifest for agent context injection

## Features

- YAML-based jobs under `~/.cronctl/jobs/`
- SQLite run log under `~/.cronctl/logs/cronctl.db`
- Retry and timeout handling through `cronctl exec`
- Managed crontab fence that preserves non-cronctl entries
- Optional Discord, Slack, and webhook notifications
- Interactive `cronctl init`
- Import/export and inline job editing

## Quick Start

```bash
uv tool install cronctl
cronctl init
cronctl add --id backup-db --schedule "0 3 * * *" --command "$HOME/.cronctl/scripts/backup-db.sh"
cronctl exec backup-db
cronctl logs backup-db --last 5
cronctl status
```

Project documentation lives in [`docs/`](./docs).

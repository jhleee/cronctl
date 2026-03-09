# cronctl

AI-agent-friendly local cron job manager built on top of system `cron`.

`cronctl` stores jobs as YAML, records runs in SQLite, and exposes the same core through a CLI, an MCP server, and a skill manifest. The repository now includes execution-tested examples, command-by-command I/O samples, and a wiki-style guide under [`docs/`](./docs).

## What is implemented

- YAML job definitions under `~/.cronctl/jobs/`
- SQLite run log under `~/.cronctl/logs/cronctl.db`
- Retry, timeout, and failure hook handling through `cronctl exec`
- Managed crontab fence that preserves non-cronctl entries
- `init`, `add`, `edit`, `list`, `enable`, `disable`, `sync`, `exec`, `logs`, `status`
- `notify setup`, `notify test`, `export`, `import`, `gc`, `doctor`
- MCP server over stdio and skill template copying via `cronctl init --skill-path`

## Quick Start

```bash
git clone https://github.com/jhleee/cronctl.git
cd cronctl
./scripts/bootstrap.sh
uv run python -m cronctl doctor --json
uv run python -m cronctl init --non-interactive
uv run python -m cronctl add --id hello --schedule "* * * * *" --command "printf hello"
uv run python -m cronctl exec hello
uv run python -m cronctl logs hello --last 1
```

## Agent Bootstrap Assets

- `.python-version` pins the intended interpreter line for local tooling.
- `uv.lock` gives agents a reproducible dependency graph.
- `scripts/bootstrap.sh` installs Python 3.11 via `uv`, syncs all extras, and prints the next commands.
- `Makefile` adds `make setup`, `make lint`, `make test`, and `make doctor`.
- `.mcp.json.example` and `.claude/settings.cronctl.json.example` are copyable MCP templates for repo-local use.

## Documentation

- Overview and current feature map: [`docs/README.md`](./docs/README.md)
- Wiki index: [`docs/wiki/README.md`](./docs/wiki/README.md)
- Step-by-step walkthrough: [`docs/wiki/QUICKSTART.md`](./docs/wiki/QUICKSTART.md)
- Command I/O examples: [`docs/wiki/CLI-IO.md`](./docs/wiki/CLI-IO.md)
- MCP integration details: [`docs/MCP.md`](./docs/MCP.md)

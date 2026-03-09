# Agent Instructions

Start here if you are an LLM or coding agent operating on this repository.

## Primary Entry Point

Read [`AGENT-BOOTSTRAP.md`](./AGENT-BOOTSTRAP.md) first and follow it exactly.

## Expected Bootstrap Path

If you only have the public repository URL and no local checkout yet:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/jhleee/cronctl/main/install.sh)
cd "${XDG_DATA_HOME:-$HOME/.local/share}/cronctl/repo"
```

If the repository is already checked out locally:

```bash
./scripts/bootstrap.sh
uv run python -m cronctl --json doctor
uv run python -m cronctl init --non-interactive
```

## Decision Rules

- If `--json doctor` reports `ready == false`, stop guessing and follow `next_steps`.
- If you need an isolated test run, use `--home /tmp/...`.
- If you must avoid the real crontab, set `CRONCTL_CRONTAB_BIN` to a fake backend.
- Treat `.mcp.json.example` and `.claude/settings.cronctl.json.example` as templates, not live config.

## Canonical Docs

- [`AGENT-BOOTSTRAP.md`](./AGENT-BOOTSTRAP.md)
- [`README.md`](./README.md)
- [`docs/wiki/QUICKSTART.md`](./docs/wiki/QUICKSTART.md)
- [`docs/wiki/CLI-IO.md`](./docs/wiki/CLI-IO.md)

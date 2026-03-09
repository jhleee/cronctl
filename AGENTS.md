# Agent Instructions

Start here if you are an LLM or coding agent operating on this repository.

## Primary Entry Point

Read [`AGENT-BOOTSTRAP.md`](./AGENT-BOOTSTRAP.md) first and follow it exactly.

## Expected Bootstrap Path

Run from the repository root:

```bash
./scripts/bootstrap.sh
uv run python -m cronctl doctor --json
uv run python -m cronctl init --non-interactive
```

## Decision Rules

- If `doctor --json` reports `ready == false`, stop guessing and follow `next_steps`.
- If you need an isolated test run, use `--home /tmp/...`.
- If you must avoid the real crontab, set `CRONCTL_CRONTAB_BIN` to a fake backend.
- Treat `.mcp.json.example` and `.claude/settings.cronctl.json.example` as templates, not live config.

## Canonical Docs

- [`AGENT-BOOTSTRAP.md`](./AGENT-BOOTSTRAP.md)
- [`README.md`](./README.md)
- [`docs/wiki/QUICKSTART.md`](./docs/wiki/QUICKSTART.md)
- [`docs/wiki/CLI-IO.md`](./docs/wiki/CLI-IO.md)

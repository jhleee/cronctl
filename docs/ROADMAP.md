# Roadmap

## Current Snapshot

The repository now has a working core package, CLI, MCP server, skill template, and execution-tested documentation. The checklist below reflects the current implementation status on `main`.

## v0.1.0 — MVP

The minimum viable release: define → schedule → execute → log → query → notify.

- [x] `core/models.py` — Job, RunResult, RetryPolicy, NotifyChannel dataclasses
- [x] `core/db.py` — SQLite schema, insert/query/gc operations
- [x] `core/job_manager.py` — YAML load/save/delete, validation, crontab sync
- [x] `core/executor.py` — subprocess execution, timeout, retry, log capture
- [x] `core/notifier.py` — Discord, Slack, generic webhook notification dispatch
- [x] `cli/` — click-based CLI
  - [x] `main.py` — top-level group, global `--json` and `--home` options
  - [x] `system.py` — interactive `init` with cron detection, sync, export/import, gc, doctor
  - [x] `jobs.py` — add, remove, edit, list, enable, disable
  - [x] `run.py` — exec, logs, status
  - [x] `notify.py` — `notify setup`, `notify test`
- [x] `__main__.py` — entry point
- [x] Non-interactive mode for implemented interactive commands
- [x] Test suite for core modules + CLI (using `click.testing.CliRunner`)
- [x] README, architecture, MCP, contributing, and wiki-style docs
- [x] `pyproject.toml` with local `uv` workflow support

## v0.2.0 — MCP Server

- [x] `mcp/server.py` — stdio transport, 7 tools
- [x] MCP resource endpoints (`cronctl://jobs`, `cronctl://jobs/{job_id}`, `cronctl://config`)
- [x] Optional dependency handling for `mcp`
- [x] `cronctl init` option to register MCP server in Claude Code settings
- [ ] MCP integration tests
- [x] MCP documentation

## v0.3.0 — Skill & Agent Polish

- [x] `skill/SKILL.md` — AgentSkills-compatible skill template
- [x] `cronctl init --skill-path` — copy `cronctl/SKILL.md` into a skills root
- [x] `cronctl export` / `cronctl import` — bulk job management
- [x] `cronctl edit --set key=value` — inline property updates
- [ ] Shell completion generation (bash, zsh, fish) via click
- [ ] `cronctl watch <job_id>` — tail logs in real time

## Next Up

- [ ] MCP integration tests and CI coverage expansion
- [ ] More complete `doctor` diagnostics for PATH and permission mismatches
- [ ] Atomic rollback behavior when job save succeeds but crontab sync fails
- [ ] Additional notification channels — Telegram, email, PagerDuty
- [ ] Import from raw crontab entries
- [ ] `singleton: true` job option (auto-flock)

## Future

- Job dependency chains (`depends_on: [job-a]`)
- Read-only web status viewer (single HTML file, no server)
- XDG base directory compliance
- Plugin system for custom executors (Docker, SSH, etc.)
- `cronctl replay <run_id>` — re-run with the same env/args as a past run

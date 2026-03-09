# Roadmap

## v0.1.0 — MVP

The minimum viable release: define → schedule → execute → log → query → notify.

- [ ] `core/models.py` — Job, RunResult, RetryPolicy, NotifyChannel dataclasses
- [ ] `core/db.py` — SQLite schema, insert/query/gc operations
- [ ] `core/job_manager.py` — YAML load/save/delete, validation, crontab sync
- [ ] `core/executor.py` — subprocess execution, timeout, retry, log capture
- [ ] `core/notifier.py` — Discord, Slack, generic webhook notification dispatch
- [ ] `cli/` — click-based CLI
  - [ ] `main.py` — top-level group, global `--json` and `--home` options
  - [ ] `system.py` — interactive `init` with cron detection + notification setup, sync, gc, doctor
  - [ ] `jobs.py` — add, remove, edit, list, enable, disable
  - [ ] `run.py` — exec, logs, status
  - [ ] `notify.py` — `notify setup` (interactive), `notify test`
- [ ] `__main__.py` — entry point
- [ ] Non-interactive mode (`--non-interactive`) for all interactive commands
- [ ] Test suite for core modules + CLI (using click.testing.CliRunner)
- [ ] README, ARCHITECTURE, CONTRIBUTING docs
- [ ] pyproject.toml with uv tool install support

**Goal:** `uv tool install cronctl && cronctl init` — fully working in under a minute.

## v0.2.0 — MCP Server

- [ ] `mcp/server.py` — stdio transport, 7 tools
- [ ] MCP resource endpoints (jobs, config)
- [ ] Optional dependency handling (graceful error if `mcp` not installed)
- [ ] `cronctl init` step to register MCP server in Claude Code / Cursor settings
- [ ] MCP integration tests
- [ ] MCP.md documentation

**Goal:** Claude Code / Cursor can discover and use cronctl as MCP tools.

## v0.3.0 — Skill & Agent Polish

- [ ] `skill/SKILL.md` — skill manifest template
- [ ] `cronctl init --skill-path` — copy skill to agent project
- [ ] `cronctl export` / `cronctl import` — bulk job management
- [ ] `cronctl edit --set key=value` — inline property updates
- [ ] Shell completion generation (bash, zsh, fish) via click
- [ ] `cronctl watch <job_id>` — tail logs in real time

**Goal:** Full AI agent workflow — agent discovers skill, uses MCP or CLI, manages jobs autonomously.

## v0.4.0 — Robustness

- [ ] `singleton: true` job option (auto-flock)
- [ ] Import from raw crontab — parse existing crontab entries into job YAMLs
- [ ] Additional notification channels — Telegram, email, PagerDuty
- [ ] Notification rate limiting (max N alerts per hour per job)
- [ ] Log rotation / size limits beyond line truncation

## Future (no timeline)

- Job dependency chains (`depends_on: [job-a]`)
- Read-only web status viewer (single HTML file, no server)
- XDG base directory compliance
- Plugin system for custom executors (Docker, SSH, etc.)
- `cronctl replay <run_id>` — re-run with same env/args as a past run

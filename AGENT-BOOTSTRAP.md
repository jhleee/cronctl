# Agent Bootstrap

This file is the shortest safe path for an LLM or coding agent to bootstrap `cronctl` from a fresh checkout.

## Goal

Get the repository into a runnable state, verify the environment, then initialize `cronctl` without guessing.

## Happy Path

For a public, no-clone-required entry point:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/jhleee/cronctl/main/install.sh)
cd "${XDG_DATA_HOME:-$HOME/.local/share}/cronctl/repo"
```

For an already cloned checkout, run:

```bash
./scripts/bootstrap.sh
uv run python -m cronctl --json doctor
uv run python -m cronctl init --non-interactive
```

Optional install flags for the remote script:

- `CRONCTL_INSTALL_INIT=0` to skip `init`
- `CRONCTL_INSTALL_COPY_MCP=1` to materialize `.mcp.json`
- `CRONCTL_INSTALL_REGISTER_CLAUDE_MCP=1` to register `cronctl mcp` in `~/.claude/settings.json`
- `CRONCTL_INSTALL_ROOT=/custom/path` to change the managed checkout location

If MCP integration is needed inside the repository:

```bash
cp .mcp.json.example .mcp.json
```

If Claude Code settings should be prepared manually instead:

```bash
mkdir -p ~/.claude
cp .claude/settings.cronctl.json.example ~/.claude/settings.json
```

## Decision Contract

Always inspect `uv run python -m cronctl --json doctor` before continuing.

- If `ready == true`, the runtime prerequisites are satisfied.
- If `repo_bootstrap_ready == true`, the repository contains the bootstrap assets an agent should expect.
- If `ready == false`, read `next_steps` and follow them in order.
- If `python.compatible == false`, do not keep using the wrong interpreter; re-enter through `./scripts/bootstrap.sh`.
- If `crontab.readable == false`, do not assume cron works; treat scheduling as blocked.
- If `paths.home_writable == false`, set a different `--home` or `CRONCTL_HOME`.

## Safe Mode

If you must test commands without touching the real user crontab, set a fake backend first:

```bash
export CRONCTL_CRONTAB_BIN=/path/to/fake-crontab
uv run python -m cronctl --home /tmp/cronctl-demo init --non-interactive
```

Use `--home /tmp/...` for tests, CI, and documentation runs. Use the default `~/.cronctl` only for real local setup.

## First Real Commands

After `init`, this is the expected minimal flow:

```bash
uv run python -m cronctl add --id hello --schedule "* * * * *" --command "printf hello"
uv run python -m cronctl exec hello
uv run python -m cronctl --json logs hello --last 1
uv run python -m cronctl --json status
```

## Files an Agent May Edit

- `~/.cronctl/config.yaml`
- `~/.cronctl/jobs/*.yaml`
- `.mcp.json`
- `~/.claude/settings.json`

## Files an Agent Should Treat as Templates

- `.mcp.json.example`
- `.claude/settings.cronctl.json.example`

## Do Not Guess

- Do not assume Python 3.11 is already active; verify via `doctor`.
- Do not assume `crontab` is present just because `cronctl` imports.
- Do not write directly into the user crontab; use `cronctl add`, `edit`, `enable`, `disable`, or `sync`.
- Do not mutate global Claude settings if repository-local MCP config is enough.

## Canonical References

- `README.md`
- `docs/README.md`
- `docs/wiki/QUICKSTART.md`
- `docs/wiki/CLI-IO.md`
- `docs/MCP.md`

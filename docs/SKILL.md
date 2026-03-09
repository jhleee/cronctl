---
name: cronctl
description: Manage local cron-backed jobs with cronctl. Use for scheduling, running, debugging, syncing, importing, exporting, and inspecting jobs and logs.
license: MIT
---

# cronctl

Use this skill when the user needs local cron automation managed through `cronctl`.

Do not use this skill for remote schedulers, workflow orchestrators like Airflow or Prefect, or one-shot delayed commands better handled by `at`.

## Preferred interfaces

1. If `cronctl` is connected as an MCP server, prefer:
   - `cronctl_list_jobs`
   - `cronctl_create_job`
   - `cronctl_delete_job`
   - `cronctl_update_job`
   - `cronctl_run_job`
   - `cronctl_get_logs`
   - `cronctl_system_status`
2. If `cronctl` is installed as a CLI, prefer `cronctl --json ...` for structured output.
3. If working from a source checkout, prefer `uv run python -m cronctl --json ...`.

## Preflight

- If this repository is present but `cronctl` is not installed, run `./scripts/bootstrap.sh`, then `uv run python -m cronctl --json doctor`, then `uv run python -m cronctl init --non-interactive`.
- Before relying on scheduling, run `cronctl --json doctor` or the source-checkout equivalent and confirm `ready == true`.
- For tests, CI, or documentation runs, use `CRONCTL_CRONTAB_BIN` with a fake backend and a temporary `--home /tmp/...`.

## Core workflows

### Create or update a job

1. Put helper scripts under `~/.cronctl/scripts/` when that convention is useful.
2. Create jobs with descriptive kebab-case ids.
3. Add or edit the job with `cronctl add` or `cronctl edit`.
4. Run `cronctl exec <job_id>` before trusting the schedule.
5. Inspect `cronctl --json logs <job_id> --last=1` after changes.

### Diagnose a failure

1. Check `cronctl --json status`.
2. Read `cronctl --json logs <job_id> --last=5`.
3. Look for `status`, `exit_code`, `stderr`, and timeout patterns.
4. Fix the script or job config, then run `cronctl exec <job_id>` again.

### Backup or migrate jobs

- Export with `cronctl export`.
- Import with `cronctl import jobs.yaml`.
- Use `cronctl sync` after manual cleanup if the crontab fence needs regeneration.

## Guardrails

- Do not edit the managed crontab block directly; use `add`, `edit`, `enable`, `disable`, `remove`, or `sync`.
- Use absolute paths inside cron-managed commands and scripts.
- Quote `--set key=value` assignments when values contain spaces.
- Use `cronctl exec` instead of manually re-running the raw command when you need the same timeout, retry, logging, and notification path cron uses.

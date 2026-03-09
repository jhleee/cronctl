# cronctl — Local Cron Job Manager

## When to use this skill

Use cronctl when:
- The user wants to schedule a script or command to run periodically on their local machine
- The user asks to check why a scheduled task failed or inspect execution history
- The user wants to automate a recurring local task with cron-backed scheduling
- The user mentions "cron", "crontab", "schedule", "periodic", "batch job", or "scheduled task"
- The user wants to manage, list, enable, disable, export, or import local scheduled jobs

Do not use cronctl when:
- The task should run on a remote server or in the cloud
- The user needs a workflow orchestrator such as Airflow or Prefect
- The user wants a one-shot delayed command; prefer `at`

## Interfaces

### CLI

```bash
cronctl init
cronctl add --id ID --schedule CRON --command CMD
cronctl remove <job_id>
cronctl edit <job_id> --set key=value
cronctl list [--tag=TAG] [--json]
cronctl enable <job_id>
cronctl disable <job_id>
cronctl sync
cronctl exec <job_id>
cronctl logs <job_id> [--last=N] [--json]
cronctl status [--json]
cronctl export
cronctl import jobs.yaml
cronctl gc [--days=30]
```

All output-producing commands support `--json`.

### MCP

If connected as an MCP server, prefer these tools:
- `cronctl_list_jobs`
- `cronctl_create_job`
- `cronctl_delete_job`
- `cronctl_update_job`
- `cronctl_run_job`
- `cronctl_get_logs`
- `cronctl_system_status`

## Workflow

1. Put scripts under `~/.cronctl/scripts/` when that convention is useful.
2. Create jobs with descriptive kebab-case ids.
3. Run `cronctl exec <job_id>` before trusting a schedule.
4. Inspect `cronctl logs <job_id>` after changes.
5. Keep raw commands out of crontab; route execution through `cronctl exec`.

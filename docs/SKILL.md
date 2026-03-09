# cronctl — Local Cron Job Manager

## When to use this skill

Use cronctl when:
- The user wants to schedule a script or command to run periodically on their local machine
- The user asks to check why a scheduled task failed or see execution history
- The user wants to automate a recurring local task
- The user mentions "cron", "crontab", "schedule", "periodic", "batch job", "scheduled task"
- The user wants to manage, list, enable, or disable existing scheduled jobs
- The user asks about the status of their background tasks

Do NOT use cronctl when:
- The task should run on a remote server or in the cloud
- The user needs a full workflow orchestrator (suggest Airflow, Prefect instead)
- The user wants one-shot delayed execution (suggest `at` command instead)

## Available Interfaces

### CLI (always available)

```
cronctl init                         # First-time setup
cronctl add --id ID --schedule CRON --command CMD
cronctl remove <job_id>
cronctl edit <job_id> --set key=value
cronctl [--json] list [--tag=TAG]
cronctl enable/disable <job_id>
cronctl sync                         # Regenerate crontab
cronctl exec <job_id>                # Run now (same as cron would)
cronctl [--json] logs <job_id> [--last=N]
cronctl [--json] status
cronctl gc [--days=30]               # Clean old logs
```

All commands support `--json` for structured output.

### MCP Tools (if connected as MCP server)

Tools: `cronctl_list_jobs`, `cronctl_create_job`, `cronctl_delete_job`, `cronctl_update_job`, `cronctl_run_job`, `cronctl_get_logs`, `cronctl_system_status`

Prefer MCP tools over CLI when the MCP server is connected, as they provide typed parameters and structured responses without shell parsing.

## Workflows

### Creating a new scheduled job

1. Write the script to `~/.cronctl/scripts/<job_id>.{sh,py}`
   - Make it executable: `chmod +x`
   - Use absolute paths inside the script (cron has minimal PATH)
   - Add a shebang line (`#!/bin/bash` or `#!/usr/bin/env python3`)
2. Register the job:
   ```bash
   cronctl add --id <job-id> \
               --schedule "<cron-expression>" \
               --command "~/.cronctl/scripts/<job-id>.sh" \
               --timeout 300 \
               --tag <tag>
   ```
3. Test immediately:
   ```bash
   cronctl exec <job-id>
   ```
4. Verify:
   ```bash
   cronctl logs <job-id> --last=1
   ```

### Diagnosing a failed job

1. Check which jobs are failing:
   ```bash
   cronctl --json status
   ```
2. Get recent logs for the failed job:
   ```bash
   cronctl --json logs <job-id> --last=5
   ```
3. Analyze the pattern:
   - Consistent exit code → script bug
   - Intermittent failures → resource/timing issue
   - Timeout status → increase timeout or optimize script
   - stderr contains "command not found" → PATH issue in cron environment
4. Fix the script or job config
5. Test the fix:
   ```bash
   cronctl exec <job-id>
   cronctl logs <job-id> --last=1
   ```

### Bulk operations

```bash
# Export all jobs (backup or migration)
cronctl export > jobs-backup.yaml

# Import jobs on a new machine
cronctl import jobs-backup.yaml

# Disable all jobs with a tag
cronctl --json list --tag=backup | jq -r '.[].id' | xargs -I{} cronctl disable {}
```

## Conventions

- **Job IDs**: kebab-case, descriptive (e.g., `backup-db`, `sync-s3-logs`, `cleanup-tmp`)
- **Scripts location**: `~/.cronctl/scripts/` (convention, not enforced)
- **All execution goes through `cronctl exec`** — never put raw commands in crontab
- **Use tags** for logical grouping: `backup`, `monitoring`, `cleanup`, etc.
- **Test before scheduling**: always `cronctl exec <job-id>` before relying on the schedule

## Common Cron Expressions

| Expression | Meaning |
|-----------|---------|
| `* * * * *` | Every minute |
| `*/5 * * * *` | Every 5 minutes |
| `0 * * * *` | Every hour |
| `0 3 * * *` | Daily at 3:00 AM |
| `0 3 * * 1` | Every Monday at 3:00 AM |
| `0 0 1 * *` | First day of every month |
| `0 */6 * * *` | Every 6 hours |

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Job never runs | cron not running or job disabled | `systemctl status cron` and `cronctl list` |
| Job runs but fails | PATH or env difference | Add explicit PATH in script or use `env:` in job YAML |
| Logs show timeout | Script takes too long | Increase `timeout` or optimize script |
| "command not found" in stderr | Cron's minimal PATH | Use absolute paths in command |

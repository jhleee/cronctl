# MCP Integration

cronctl exposes a Model Context Protocol (MCP) server for direct integration with AI agents.

## Overview

The MCP server uses **stdio transport** — no HTTP, no ports, no daemon. The MCP client launches `cronctl mcp` as a child process and communicates via stdin/stdout.

This means:
- Zero configuration for networking
- No port conflicts
- Same permissions as the calling user
- Process dies when the client disconnects (no orphan daemons)

`cronctl mcp` is intentionally a long-running stdio service. It does not print a human-friendly banner; the caller is expected to speak MCP on stdin/stdout.

## Setup

### Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "cronctl": {
      "command": "cronctl",
      "args": ["mcp"]
    }
  }
}
```

Or per-project in `.mcp.json`:

```json
{
  "mcpServers": {
    "cronctl": {
      "command": "cronctl",
      "args": ["mcp"]
    }
  }
}
```

### Cursor

Add to Cursor MCP settings:

```json
{
  "mcpServers": {
    "cronctl": {
      "command": "cronctl",
      "args": ["mcp"]
    }
  }
}
```

### Custom Agent (Python)

```python
import subprocess
import json

proc = subprocess.Popen(
    ["cronctl", "mcp"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True
)
# Communicate via MCP protocol on stdin/stdout
```

## Tools

### cronctl_list_jobs

List all registered cron jobs.

**Input:**
```json
{
  "tag": "backup",        // optional: filter by tag
  "status": "enabled"     // optional: "enabled" | "disabled" | "all"
}
```

**Output:**
```json
{
  "jobs": [
    {
      "id": "backup-db",
      "schedule": "0 3 * * *",
      "description": "PostgreSQL daily backup",
      "enabled": true,
      "tags": ["db", "backup"],
      "last_run": {
        "status": "success",
        "at": "2025-01-15T03:00:12Z",
        "duration_ms": 45230
      }
    }
  ]
}
```

### cronctl_create_job

Create and register a new cron job.

**Input:**
```json
{
  "job_id": "backup-db",                // required
  "schedule": "0 3 * * *",              // required
  "command": "/path/to/script.sh",      // required
  "description": "Daily DB backup",     // optional
  "timeout": 300,                        // optional
  "retry_max": 3,                        // optional
  "retry_delay": 60,                     // optional
  "tags": ["db", "backup"],             // optional
  "env": {"DB_HOST": "localhost"}        // optional
}
```

**Output:**
```json
{
  "created": true,
  "job_id": "backup-db",
  "crontab_synced": true,
  "yaml_path": "~/.cronctl/jobs/backup-db.yaml"
}
```

### cronctl_delete_job

Remove a job and its crontab entry.

**Input:**
```json
{
  "job_id": "backup-db"
}
```

**Output:**
```json
{
  "deleted": true,
  "job_id": "backup-db",
  "crontab_synced": true
}
```

### cronctl_update_job

Update properties of an existing job.

**Input:**
```json
{
  "job_id": "backup-db",
  "schedule": "0 4 * * *",   // any job field is optional
  "enabled": false,
  "timeout": 600
}
```

**Output:**
```json
{
  "updated": true,
  "job_id": "backup-db",
  "changes": ["schedule", "enabled", "timeout"],
  "crontab_synced": true
}
```

### cronctl_run_job

Execute a job immediately and return the result.

**Input:**
```json
{
  "job_id": "backup-db"
}
```

**Output:**
```json
{
  "run_id": "01HZ3ABCDEF",
  "job_id": "backup-db",
  "status": "success",
  "exit_code": 0,
  "duration_ms": 45230,
  "stdout": "Backup completed: 2.3GB written",
  "stderr": ""
}
```

### cronctl_get_logs

Get execution history for a job.

**Input:**
```json
{
  "job_id": "backup-db",
  "last": 10,                    // optional, default 10
  "status_filter": "failed"      // optional: "all" | "success" | "failed" | "timeout"
}
```

**Output:**
```json
{
  "job_id": "backup-db",
  "runs": [
    {
      "run_id": "01HZ3ABCDEF",
      "started_at": "2025-01-15T03:00:12Z",
      "finished_at": "2025-01-15T03:00:57Z",
      "duration_ms": 45230,
      "exit_code": 0,
      "status": "success",
      "attempt": 1,
      "stdout": "Backup completed: 2.3GB written",
      "stderr": ""
    }
  ]
}
```

### cronctl_system_status

Overview of all jobs and recent activity.

**Input:**
```json
{}
```

**Output:**
```json
{
  "total_jobs": 5,
  "enabled": 4,
  "disabled": 1,
  "recent_runs": {
    "last_24h": 12,
    "success": 10,
    "failed": 2
  },
  "failed_jobs": [
    {
      "job_id": "sync-s3",
      "last_failure": "2025-01-15T14:30:00Z",
      "exit_code": 1,
      "consecutive_failures": 3
    }
  ],
  "next_runs": [
    {
      "job_id": "backup-db",
      "next_at": "2025-01-16T03:00:00Z"
    }
  ]
}
```

## Resources

The MCP server also exposes read-only resources:

| URI | Description |
|-----|-------------|
| `cronctl://jobs` | JSON list of all job definitions |
| `cronctl://jobs/{job_id}` | Single job definition (YAML content) |
| `cronctl://config` | Global config (YAML content) |

## Implementation Notes

### Dependencies

The MCP server uses the official `mcp` Python SDK (pip: `mcp`). This is the only additional dependency beyond the core cronctl requirements.

The SDK is an optional dependency — cronctl CLI works without it. If `cronctl mcp` is invoked without the SDK installed, it prints an installation hint and exits.

```toml
# pyproject.toml
[project.optional-dependencies]
mcp = ["mcp>=1.0"]
```

### Handler Structure

Each MCP tool maps to a thin handler that:
1. Validates input parameters
2. Calls the corresponding core function
3. Returns structured output directly from the same core objects the CLI uses

```python
# Pseudocode
@server.tool("cronctl_list_jobs")
async def handle_list_jobs(tag: str = None, status: str = "all"):
    jobs = job_manager.list(tag=tag, enabled_filter=status)
    return [TextContent(type="text", text=json.dumps(format_jobs(jobs)))]
```

### Error Responses

- **Tool errors** (invalid job_id, validation failure): Return MCP error with descriptive message
- **Execution results** (job failed): Return success response with failure details in content — the MCP tool worked correctly; it's the user's job that failed

### Testing

The MCP server can be tested with `mcp dev`:

```bash
uv run mcp dev src/cronctl/mcp/server.py
```

Or programmatically:

```python
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

async with stdio_client(["cronctl", "mcp"]) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("cronctl_system_status", {})
        print(result)
```

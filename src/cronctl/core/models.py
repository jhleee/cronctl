from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from cronctl.core.utils import from_iso8601, to_iso8601

JOB_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,63}$")


class RunStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRYING = "retrying"

    @property
    def terminal(self) -> bool:
        return self in {self.SUCCESS, self.FAILED, self.TIMEOUT}


@dataclass
class RetryPolicy:
    max_attempts: int = 1
    delay: int = 30

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> RetryPolicy | None:
        if data is None:
            return None
        return cls(
            max_attempts=int(data.get("max_attempts", 1)),
            delay=int(data.get("delay", 30)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NotifyChannel:
    type: str
    webhook_url: str = ""
    url: str = ""
    method: str = "POST"
    headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotifyChannel:
        return cls(
            type=str(data.get("type", "")).strip(),
            webhook_url=str(data.get("webhook_url", "")).strip(),
            url=str(data.get("url", "")).strip(),
            method=str(data.get("method", "POST")).upper(),
            headers={str(key): str(value) for key, value in dict(data.get("headers", {})).items()},
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not self.headers:
            data.pop("headers")
        if not self.webhook_url:
            data.pop("webhook_url")
        if not self.url:
            data.pop("url")
        if self.method == "POST" and "method" in data:
            data.pop("method")
        return data


@dataclass
class NotificationsConfig:
    on_failure: bool = True
    on_timeout: bool = True
    on_recovery: bool = False
    channels: list[NotifyChannel] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> NotificationsConfig:
        if data is None:
            return cls()
        channels = [NotifyChannel.from_dict(item) for item in list(data.get("channels", []))]
        return cls(
            on_failure=bool(data.get("on_failure", True)),
            on_timeout=bool(data.get("on_timeout", True)),
            on_recovery=bool(data.get("on_recovery", False)),
            channels=channels,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "on_failure": self.on_failure,
            "on_timeout": self.on_timeout,
            "on_recovery": self.on_recovery,
            "channels": [channel.to_dict() for channel in self.channels],
        }


@dataclass
class AppConfig:
    log_retention_days: int = 30
    max_log_lines: int = 200
    default_timeout: int = 600
    default_retry: RetryPolicy = field(default_factory=RetryPolicy)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)
    hooks: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> AppConfig:
        if data is None:
            return cls()
        return cls(
            log_retention_days=int(data.get("log_retention_days", 30)),
            max_log_lines=int(data.get("max_log_lines", 200)),
            default_timeout=int(data.get("default_timeout", 600)),
            default_retry=RetryPolicy.from_dict(data.get("default_retry")) or RetryPolicy(),
            notifications=NotificationsConfig.from_dict(data.get("notifications")),
            hooks={str(key): str(value) for key, value in dict(data.get("hooks", {})).items()},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "log_retention_days": self.log_retention_days,
            "max_log_lines": self.max_log_lines,
            "default_timeout": self.default_timeout,
            "default_retry": self.default_retry.to_dict(),
            "notifications": self.notifications.to_dict(),
            "hooks": self.hooks,
        }


@dataclass
class Job:
    id: str
    schedule: str
    command: str
    description: str = ""
    timeout: int | None = None
    retry: RetryPolicy | None = None
    env: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    enabled: bool = True
    notify: bool | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Job:
        env = {str(key): str(value) for key, value in dict(data.get("env", {})).items()}
        tags = [str(tag) for tag in list(data.get("tags", []))]
        return cls(
            id=str(data["id"]),
            schedule=str(data["schedule"]),
            command=str(data["command"]),
            description=str(data.get("description", "")),
            timeout=int(data["timeout"]) if data.get("timeout") is not None else None,
            retry=RetryPolicy.from_dict(data.get("retry")),
            env=env,
            tags=tags,
            enabled=bool(data.get("enabled", True)),
            notify=data.get("notify"),
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "description": self.description,
            "schedule": self.schedule,
            "command": self.command,
            "timeout": self.timeout,
            "retry": self.retry.to_dict() if self.retry else None,
            "env": self.env,
            "tags": self.tags,
            "enabled": self.enabled,
            "notify": self.notify,
        }
        return {
            key: value
            for key, value in data.items()
            if value not in ({}, [], None, "") or key in {"enabled"}
        }


@dataclass
class RunResult:
    run_id: str
    job_id: str
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int | None = None
    exit_code: int | None = None
    status: RunStatus = RunStatus.RUNNING
    attempt: int = 1
    stdout: str = ""
    stderr: str = ""
    error_msg: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "job_id": self.job_id,
            "started_at": to_iso8601(self.started_at),
            "finished_at": to_iso8601(self.finished_at),
            "duration_ms": self.duration_ms,
            "exit_code": self.exit_code,
            "status": self.status.value,
            "attempt": self.attempt,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error_msg": self.error_msg,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunResult:
        return cls(
            run_id=str(data["run_id"]),
            job_id=str(data["job_id"]),
            started_at=from_iso8601(str(data["started_at"])) or datetime.now(),
            finished_at=from_iso8601(data.get("finished_at")),
            duration_ms=int(data["duration_ms"]) if data.get("duration_ms") is not None else None,
            exit_code=int(data["exit_code"]) if data.get("exit_code") is not None else None,
            status=RunStatus(str(data.get("status", RunStatus.RUNNING.value))),
            attempt=int(data.get("attempt", 1)),
            stdout=str(data.get("stdout", "")),
            stderr=str(data.get("stderr", "")),
            error_msg=str(data.get("error_msg", "")),
        )

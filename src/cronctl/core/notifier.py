from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cronctl.core.models import AppConfig, Job, NotifyChannel, RunResult, RunStatus

logger = logging.getLogger(__name__)

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None


@dataclass
class NotificationResult:
    delivered: int = 0
    failed: int = 0
    errors: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "delivered": self.delivered,
            "failed": self.failed,
            "errors": self.errors or [],
        }


class Notifier:
    def available(self) -> bool:
        return httpx is not None

    def send(
        self,
        config: AppConfig,
        job: Job,
        result: RunResult,
        event: str,
    ) -> NotificationResult:
        output = NotificationResult(errors=[])
        if httpx is None:
            output.failed += len(config.notifications.channels)
            output.errors.append("httpx is not installed; notification delivery skipped")
            return output
        for channel in config.notifications.channels:
            try:
                self._send_channel(channel, job, result, event)
                output.delivered += 1
            except Exception as exc:  # pragma: no cover
                logger.warning("Notification delivery failed: %s", exc)
                output.failed += 1
                output.errors.append(str(exc))
        return output

    def send_test(self, config: AppConfig) -> NotificationResult:
        fake_job = Job(
            id="cronctl-test",
            schedule="* * * * *",
            command="echo test",
            description="cronctl notification test",
        )
        finished = datetime.now(timezone.utc)
        fake_result = RunResult(
            run_id="test-run",
            job_id=fake_job.id,
            started_at=finished,
            finished_at=finished,
            duration_ms=5,
            exit_code=0,
            status=RunStatus.SUCCESS,
            stdout="cronctl notification test",
            stderr="",
        )
        return self.send(config, fake_job, fake_result, "test")

    def _send_channel(
        self,
        channel: NotifyChannel,
        job: Job,
        result: RunResult,
        event: str,
    ) -> None:
        assert httpx is not None
        payload = self._build_payload(channel, job, result, event)
        headers = {"Content-Type": "application/json"}
        headers.update(channel.headers)
        url = channel.webhook_url or channel.url
        if not url:
            raise ValueError(f"Notification channel {channel.type} is missing a target URL")
        with httpx.Client(timeout=10.0) as client:
            response = client.request(channel.method, url, headers=headers, json=payload)
            response.raise_for_status()

    def _build_payload(
        self,
        channel: NotifyChannel,
        job: Job,
        result: RunResult,
        event: str,
    ) -> dict[str, Any]:
        title = f"cronctl - {event}"
        status_text = result.status.value
        stderr_tail = result.stderr[-500:]
        if channel.type == "discord":
            return {
                "embeds": [
                    {
                        "title": title,
                        "description": f"Job `{job.id}` {status_text}",
                        "color": 0xE74C3C if result.status != RunStatus.SUCCESS else 0x2ECC71,
                        "fields": [
                            {"name": "Exit Code", "value": str(result.exit_code), "inline": True},
                            {
                                "name": "Duration",
                                "value": f"{result.duration_ms}ms",
                                "inline": True,
                            },
                            {"name": "Attempt", "value": str(result.attempt), "inline": True},
                            {"name": "stderr (tail)", "value": f"```{stderr_tail or ' '}```"},
                        ],
                        "timestamp": result.finished_at.isoformat() if result.finished_at else None,
                    }
                ]
            }
        if channel.type == "slack":
            return {
                "blocks": [
                    {"type": "header", "text": {"type": "plain_text", "text": title}},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"*Job:* `{job.id}`\n"
                                f"*Status:* {status_text}\n"
                                f"*Exit:* {result.exit_code}"
                            ),
                        },
                    },
                    {"type": "section", "text": {"type": "mrkdwn", "text": f"```{stderr_tail}```"}},
                ]
            }
        return {
            "event": f"job_{event}",
            "job_id": job.id,
            "job_description": job.description,
            "status": status_text,
            "exit_code": result.exit_code,
            "duration_ms": result.duration_ms,
            "attempt": result.attempt,
            "stderr_tail": stderr_tail,
            "timestamp": result.finished_at.isoformat() if result.finished_at else None,
        }


def should_notify(config: AppConfig, job: Job, event: str) -> bool:
    if job.notify is False:
        return False
    if job.notify is True:
        return True
    if event == "failure":
        return config.notifications.on_failure
    if event == "timeout":
        return config.notifications.on_timeout
    if event == "recovery":
        return config.notifications.on_recovery
    return event == "test"

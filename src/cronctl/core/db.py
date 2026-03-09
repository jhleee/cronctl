from __future__ import annotations

import os
import sqlite3
import time
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import Any

from cronctl.core.models import RunResult, RunStatus
from cronctl.core.utils import from_iso8601, to_iso8601, utc_now

SCHEMA = """
CREATE TABLE IF NOT EXISTS job_runs (
    run_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    duration_ms INTEGER,
    exit_code INTEGER,
    status TEXT NOT NULL,
    attempt INTEGER DEFAULT 1,
    stdout TEXT,
    stderr TEXT,
    error_msg TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_job_runs_job_id ON job_runs(job_id);
CREATE INDEX IF NOT EXISTS idx_job_runs_started ON job_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_job_runs_status ON job_runs(status);
"""


class RunLogDB:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        attempts = 0
        while True:
            try:
                conn = sqlite3.connect(self.path)
                conn.row_factory = sqlite3.Row
                yield conn
                conn.close()
                break
            except sqlite3.OperationalError as exc:
                attempts += 1
                if "locked" not in str(exc).lower() or attempts >= 3:
                    raise
                time.sleep(0.1 * attempts)

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            conn.commit()
        if self.path.exists():
            os.chmod(self.path, 0o600)

    def insert_run(self, result: RunResult) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO job_runs (
                    run_id, job_id, started_at, finished_at, duration_ms, exit_code,
                    status, attempt, stdout, stderr, error_msg
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.run_id,
                    result.job_id,
                    to_iso8601(result.started_at),
                    to_iso8601(result.finished_at),
                    result.duration_ms,
                    result.exit_code,
                    result.status.value,
                    result.attempt,
                    result.stdout,
                    result.stderr,
                    result.error_msg,
                ),
            )
            conn.commit()

    def update_run(self, result: RunResult) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE job_runs
                SET finished_at = ?, duration_ms = ?, exit_code = ?, status = ?,
                    attempt = ?, stdout = ?, stderr = ?, error_msg = ?
                WHERE run_id = ?
                """,
                (
                    to_iso8601(result.finished_at),
                    result.duration_ms,
                    result.exit_code,
                    result.status.value,
                    result.attempt,
                    result.stdout,
                    result.stderr,
                    result.error_msg,
                    result.run_id,
                ),
            )
            conn.commit()

    def get_runs(
        self,
        job_id: str,
        last: int = 10,
        status_filter: str = "all",
    ) -> list[RunResult]:
        query = """
            SELECT run_id, job_id, started_at, finished_at, duration_ms, exit_code, status,
                   attempt, stdout, stderr, error_msg
            FROM job_runs
            WHERE job_id = ?
        """
        params: list[Any] = [job_id]
        if status_filter != "all":
            if status_filter == "failed":
                query += " AND status IN ('failed', 'retrying')"
            else:
                query += " AND status = ?"
                params.append(status_filter)
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(last)
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_run(row) for row in rows]

    def get_last_run(self, job_id: str) -> RunResult | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT run_id, job_id, started_at, finished_at, duration_ms, exit_code, status,
                       attempt, stdout, stderr, error_msg
                FROM job_runs
                WHERE job_id = ?
                ORDER BY started_at DESC
                LIMIT 1
                """,
                (job_id,),
            ).fetchone()
        return self._row_to_run(row) if row else None

    def latest_terminal_status(self, job_id: str) -> RunStatus | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT status
                FROM job_runs
                WHERE job_id = ? AND status IN ('success', 'failed', 'timeout')
                ORDER BY started_at DESC
                LIMIT 1
                """,
                (job_id,),
            ).fetchone()
        return RunStatus(row["status"]) if row else None

    def recent_summary(self, hours: int = 24) -> dict[str, int]:
        cutoff = to_iso8601(utc_now() - timedelta(hours=hours))
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM job_runs
                WHERE started_at >= ?
                GROUP BY status
                """,
                (cutoff,),
            ).fetchall()
        summary = {"last_24h": 0, "success": 0, "failed": 0, "timeout": 0}
        for row in rows:
            status = str(row["status"])
            count = int(row["count"])
            summary["last_24h"] += count
            if status in {"failed", "retrying"}:
                summary["failed"] += count
            elif status in summary:
                summary[status] += count
        return summary

    def failed_jobs(self, job_ids: list[str]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for job_id in job_ids:
            last = self.get_last_run(job_id)
            if not last or last.status not in {RunStatus.FAILED, RunStatus.TIMEOUT}:
                continue
            consecutive = 0
            for run in self.get_runs(job_id, last=50):
                if run.status in {RunStatus.FAILED, RunStatus.TIMEOUT}:
                    consecutive += 1
                elif run.status == RunStatus.SUCCESS:
                    break
            results.append(
                {
                    "job_id": job_id,
                    "last_failure": to_iso8601(last.finished_at or last.started_at),
                    "exit_code": last.exit_code,
                    "consecutive_failures": consecutive,
                    "status": last.status.value,
                }
            )
        return sorted(results, key=lambda item: item["last_failure"] or "", reverse=True)

    def gc(self, days: int) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                "DELETE FROM job_runs WHERE created_at < datetime('now', ?)",
                (f"-{days} days",),
            )
            deleted = int(cursor.rowcount)
            conn.commit()
            conn.execute("VACUUM")
            conn.commit()
        return deleted

    def runs_by_job(self, hours: int = 24) -> dict[str, list[RunResult]]:
        cutoff = to_iso8601(utc_now() - timedelta(hours=hours))
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT run_id, job_id, started_at, finished_at, duration_ms, exit_code, status,
                       attempt, stdout, stderr, error_msg
                FROM job_runs
                WHERE started_at >= ?
                ORDER BY started_at DESC
                """,
                (cutoff,),
            ).fetchall()
        grouped: dict[str, list[RunResult]] = defaultdict(list)
        for row in rows:
            run = self._row_to_run(row)
            grouped[run.job_id].append(run)
        return dict(grouped)

    def _row_to_run(self, row: sqlite3.Row) -> RunResult:
        return RunResult(
            run_id=str(row["run_id"]),
            job_id=str(row["job_id"]),
            started_at=from_iso8601(str(row["started_at"])) or utc_now(),
            finished_at=from_iso8601(row["finished_at"]),
            duration_ms=int(row["duration_ms"]) if row["duration_ms"] is not None else None,
            exit_code=int(row["exit_code"]) if row["exit_code"] is not None else None,
            status=RunStatus(str(row["status"])),
            attempt=int(row["attempt"] or 1),
            stdout=str(row["stdout"] or ""),
            stderr=str(row["stderr"] or ""),
            error_msg=str(row["error_msg"] or ""),
        )

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import List

from chaos_negotiator.models.outcome import DeploymentOutcome


class DeploymentHistoryStore:
    """Simple SQLite-backed store for deployment outcomes.

    This implementation uses the stdlib ``sqlite3`` module in order to avoid
    extra dependencies; the database file path can be controlled via an
    environment variable or passed explicitly.  Only a tiny subset of SQL
    is used, so it would be straightforward to replace with a different
    backend (MySQL, PostgreSQL, etc.) in the future.
    """

    def __init__(self, db_path: str | None = None) -> None:
        import os

        db_path = db_path or os.getenv("CN_HISTORY_DB", "deployment_history.db")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._ensure_table()

    def _ensure_table(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS outcomes (
                deployment_id TEXT PRIMARY KEY,
                heuristic_score REAL,
                ml_score REAL,
                final_score REAL,
                actual_error_rate_percent REAL,
                actual_latency_change_percent REAL,
                rollback_triggered INTEGER,
                timestamp TEXT
            )
            """)
        self.conn.commit()

    def save(self, outcome: DeploymentOutcome) -> None:
        """Persist a deployment outcome to the database."""
        self.conn.execute(
            """
            INSERT OR REPLACE INTO outcomes (
                deployment_id,
                heuristic_score,
                ml_score,
                final_score,
                actual_error_rate_percent,
                actual_latency_change_percent,
                rollback_triggered,
                timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                outcome.deployment_id,
                outcome.heuristic_score,
                outcome.ml_score,
                outcome.final_score,
                outcome.actual_error_rate_percent,
                outcome.actual_latency_change_percent,
                1 if outcome.rollback_triggered else 0,
                outcome.timestamp.isoformat(),
            ),
        )
        self.conn.commit()

    def recent(self, limit: int = 100) -> List[DeploymentOutcome]:
        """Return the most recent outcomes up to ``limit`` items."""
        cursor = self.conn.execute(
            """
            SELECT deployment_id, heuristic_score, ml_score, final_score,
                   actual_error_rate_percent, actual_latency_change_percent,
                   rollback_triggered, timestamp
            FROM outcomes
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        results: List[DeploymentOutcome] = []
        for r in rows:
            results.append(
                DeploymentOutcome(
                    deployment_id=r[0],
                    heuristic_score=r[1],
                    ml_score=r[2],
                    final_score=r[3],
                    actual_error_rate_percent=r[4],
                    actual_latency_change_percent=r[5],
                    rollback_triggered=bool(r[6]),
                    timestamp=datetime.fromisoformat(r[7]),
                )
            )
        return results

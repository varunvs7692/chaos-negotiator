from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Any


class DeploymentApprovalStore:
    """SQLite-backed store for deployment approval decisions."""

    def __init__(self, db_path: str | None = None) -> None:
        resolved_db_path = db_path or os.getenv("CN_APPROVAL_DB") or "deployment_approvals.db"
        try:
            self.conn = sqlite3.connect(resolved_db_path, check_same_thread=False)
            self._ensure_table()
        except sqlite3.Error:
            self.conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._ensure_table()

    def _ensure_table(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS deployment_approvals (
                deployment_id TEXT PRIMARY KEY,
                service_name TEXT NOT NULL,
                environment TEXT NOT NULL,
                version TEXT NOT NULL,
                risk_score REAL NOT NULL,
                risk_level TEXT NOT NULL,
                confidence_percent REAL NOT NULL,
                approval_status TEXT NOT NULL,
                decision_reason TEXT NOT NULL,
                contract_json TEXT NOT NULL,
                canary_strategy_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)
        self.conn.commit()

    def save_evaluation(
        self,
        deployment_id: str,
        service_name: str,
        environment: str,
        version: str,
        risk_score: float,
        risk_level: str,
        confidence_percent: float,
        contract: dict[str, Any],
        canary_strategy: dict[str, Any],
    ) -> None:
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO deployment_approvals (
                deployment_id,
                service_name,
                environment,
                version,
                risk_score,
                risk_level,
                confidence_percent,
                approval_status,
                decision_reason,
                contract_json,
                canary_strategy_json,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                deployment_id,
                service_name,
                environment,
                version,
                risk_score,
                risk_level,
                confidence_percent,
                "pending",
                "",
                json.dumps(contract),
                json.dumps(canary_strategy),
                now,
                now,
            ),
        )
        self.conn.commit()

    def list_pending(self, limit: int = 50) -> list[dict[str, Any]]:
        cursor = self.conn.execute(
            """
            SELECT deployment_id, service_name, environment, version, risk_score,
                   risk_level, confidence_percent, approval_status, decision_reason,
                   contract_json, canary_strategy_json, created_at, updated_at
            FROM deployment_approvals
            WHERE approval_status = 'pending'
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the most recently updated approval records regardless of status."""
        cursor = self.conn.execute(
            """
            SELECT deployment_id, service_name, environment, version, risk_score,
                   risk_level, confidence_percent, approval_status, decision_reason,
                   contract_json, canary_strategy_json, created_at, updated_at
            FROM deployment_approvals
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get(self, deployment_id: str) -> dict[str, Any] | None:
        cursor = self.conn.execute(
            """
            SELECT deployment_id, service_name, environment, version, risk_score,
                   risk_level, confidence_percent, approval_status, decision_reason,
                   contract_json, canary_strategy_json, created_at, updated_at
            FROM deployment_approvals
            WHERE deployment_id = ?
            """,
            (deployment_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def update_status(
        self, deployment_id: str, approval_status: str, decision_reason: str
    ) -> dict[str, Any] | None:
        """Update the approval status for a deployment."""
        existing = self.get(deployment_id)
        if existing is None:
            return None

        updated_at = datetime.utcnow().isoformat()
        self.conn.execute(
            """
            UPDATE deployment_approvals
            SET approval_status = ?, decision_reason = ?, updated_at = ?
            WHERE deployment_id = ?
            """,
            (approval_status, decision_reason, updated_at, deployment_id),
        )
        self.conn.commit()
        return self.get(deployment_id)

    def _row_to_dict(self, row: tuple[Any, ...]) -> dict[str, Any]:
        return {
            "deployment_id": row[0],
            "service_name": row[1],
            "environment": row[2],
            "version": row[3],
            "risk_score": row[4],
            "risk_level": row[5],
            "confidence_percent": row[6],
            "approval_status": row[7],
            "decision_reason": row[8],
            "contract": json.loads(row[9]),
            "canary_strategy": json.loads(row[10]),
            "created_at": row[11],
            "updated_at": row[12],
        }

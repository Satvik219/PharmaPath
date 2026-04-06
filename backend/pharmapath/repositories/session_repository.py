from __future__ import annotations

import json

from pharmapath.db.connection import get_connection


class SessionRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path

    def create_session(self, payload: dict) -> None:
        with get_connection(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO sessions (id, patient_id, user_id, medications_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload.get("patient_id"),
                    payload["user_id"],
                    json.dumps(payload["medications"]),
                    payload["created_at"],
                ),
            )
            connection.commit()

    def create_result(self, payload: dict) -> None:
        with get_connection(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO interaction_results (
                    id, session_id, overall_risk, risk_pairs_json, alternatives_json,
                    graph_json, bayesian_flags_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["session_id"],
                    payload["overall_risk"],
                    json.dumps(payload["risk_pairs"]),
                    json.dumps(payload["alternatives"]),
                    json.dumps(payload["graph_json"]),
                    json.dumps(payload["bayesian_flags"]),
                    payload["created_at"],
                ),
            )
            connection.commit()

    def history_for_patient(self, patient_id: str) -> list[dict]:
        with get_connection(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT s.id AS session_id, s.created_at AS timestamp, s.medications_json,
                       ir.overall_risk
                FROM sessions s
                LEFT JOIN interaction_results ir ON ir.session_id = s.id
                WHERE s.patient_id = ?
                ORDER BY s.created_at DESC
                """,
                (patient_id,),
            ).fetchall()
            history = []
            for row in rows:
                item = dict(row)
                item["medications"] = json.loads(item.pop("medications_json") or "[]")
                history.append(item)
            return history


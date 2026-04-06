from __future__ import annotations

import json

from pharmapath.db.connection import get_connection


class ReportRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path

    def create(self, payload: dict) -> None:
        with get_connection(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO reports (id, session_id, patient_id, format, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["session_id"],
                    payload.get("patient_id"),
                    payload["format"],
                    json.dumps(payload["payload"]),
                    payload["created_at"],
                ),
            )
            connection.commit()

    def get(self, report_id: str):
        with get_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM reports WHERE id = ?",
                (report_id,),
            ).fetchone()
            if not row:
                return None
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            return item

    def list(self, patient_id: str | None = None) -> list[dict]:
        query = "SELECT * FROM reports"
        params: tuple = ()
        if patient_id:
            query += " WHERE patient_id = ?"
            params = (patient_id,)
        query += " ORDER BY created_at DESC"
        with get_connection(self.database_path) as connection:
            rows = connection.execute(query, params).fetchall()
            items = []
            for row in rows:
                item = dict(row)
                item["payload"] = json.loads(item.pop("payload_json"))
                items.append(item)
            return items

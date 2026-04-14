from __future__ import annotations

import json

from pharmapath.db.connection import get_connection


class PatientRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path

    def create(self, payload: dict) -> None:
        with get_connection(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO patients (
                    id, tenant_id, name, dob, weight_kg, conditions, allergies,
                    deleted_at, current_medications, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["tenant_id"],
                    payload["name"],
                    payload.get("dob"),
                    payload.get("weight_kg"),
                    json.dumps(payload.get("conditions", [])),
                    json.dumps(payload.get("allergies", [])),
                    payload.get("deleted_at"),
                    json.dumps(payload.get("current_medications", [])),
                    payload["created_at"],
                    payload["updated_at"],
                ),
            )
            connection.commit()

    def get(self, patient_id: str):
        with get_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM patients WHERE id = ?",
                (patient_id,),
            ).fetchone()
            return self._deserialize(row)

    def update(self, patient_id: str, updates: dict) -> None:
        medications = updates.get("current_medications", updates.get("medications", []))
        with get_connection(self.database_path) as connection:
            connection.execute(
                """
                UPDATE patients
                SET dob = ?, weight_kg = ?, conditions = ?, allergies = ?, current_medications = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    updates.get("dob"),
                    updates.get("weight_kg"),
                    json.dumps(updates.get("conditions", [])),
                    json.dumps(updates.get("allergies", [])),
                    json.dumps(medications),
                    updates["updated_at"],
                    patient_id,
                ),
            )
            connection.commit()

    def soft_delete(self, patient_id: str, deleted_at: str) -> None:
        with get_connection(self.database_path) as connection:
            connection.execute(
                "UPDATE patients SET deleted_at = ? WHERE id = ?",
                (deleted_at, patient_id),
            )
            connection.commit()

    def _deserialize(self, row):
        if row is None:
            return None
        item = dict(row)
        item["conditions"] = json.loads(item["conditions"] or "[]")
        item["allergies"] = json.loads(item["allergies"] or "[]")
        item["current_medications"] = json.loads(item["current_medications"] or "[]")
        return item

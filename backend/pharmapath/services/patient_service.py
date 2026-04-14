from __future__ import annotations

from flask import current_app

from pharmapath.repositories.patient_repository import PatientRepository
from pharmapath.repositories.session_repository import SessionRepository
from pharmapath.utils.ids import new_id
from pharmapath.utils.time import utc_now_iso


class PatientService:
    def __init__(self) -> None:
        db_path = current_app.config["DATABASE_PATH"]
        self.repo = PatientRepository(db_path)
        self.session_repo = SessionRepository(db_path)

    def create(self, payload: dict, tenant_id: str) -> dict:
        patient_id = new_id()
        now = utc_now_iso()
        record = {
            "id": patient_id,
            "tenant_id": tenant_id,
            "name": payload["name"],
            "dob": payload.get("dob"),
            "weight_kg": payload.get("weight_kg"),
            "conditions": payload.get("conditions", []),
            "allergies": payload.get("allergies", []),
            "deleted_at": None,
            "current_medications": payload.get("current_medications", []),
            "created_at": now,
            "updated_at": now,
        }
        self.repo.create(record)
        return {"patient_id": patient_id, "created_at": now}

    def get(self, patient_id: str) -> dict | None:
        return self.repo.get(patient_id)

    def update(self, patient_id: str, payload: dict) -> dict:
        now = utc_now_iso()
        existing = self.repo.get(patient_id) or {}
        merged = {
            "dob": payload.get("dob", existing.get("dob")),
            "weight_kg": payload.get("weight_kg", existing.get("weight_kg")),
            "conditions": payload.get("conditions", existing.get("conditions", [])),
            "allergies": payload.get("allergies", existing.get("allergies", [])),
            "current_medications": payload.get(
                "current_medications",
                payload.get("medications", existing.get("current_medications", [])),
            ),
            "updated_at": now,
        }
        self.repo.update(patient_id, merged)
        return {"patient_id": patient_id, "updated_at": now}

    def history(self, patient_id: str) -> dict:
        return {"sessions": self.session_repo.history_for_patient(patient_id)}

    def delete(self, patient_id: str) -> dict:
        deleted_at = utc_now_iso()
        self.repo.soft_delete(patient_id, deleted_at)
        return {"success": True, "deleted_at": deleted_at}

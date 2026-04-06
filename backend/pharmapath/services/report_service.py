from __future__ import annotations

from flask import current_app

from pharmapath.repositories.report_repository import ReportRepository
from pharmapath.utils.ids import new_id
from pharmapath.utils.time import utc_now_iso


class ReportService:
    def __init__(self) -> None:
        self.repo = ReportRepository(current_app.config["DATABASE_PATH"])

    def generate(self, payload: dict) -> dict:
        report_id = new_id()
        now = utc_now_iso()
        report_payload = {
            "session_id": payload["session_id"],
            "format": payload["format"],
            "include_alternatives": payload.get("include_alternatives", True),
            "note": "PDF generation can be plugged in later; JSON payload is available now.",
        }
        self.repo.create(
            {
                "id": report_id,
                "session_id": payload["session_id"],
                "patient_id": payload.get("patient_id"),
                "format": payload["format"],
                "payload": report_payload,
                "created_at": now,
            }
        )
        return {"report_id": report_id, "download_url": f"/api/reports/{report_id}", "expires_at": None}

    def get(self, report_id: str) -> dict | None:
        return self.repo.get(report_id)

    def list(self, patient_id: str | None) -> dict:
        reports = self.repo.list(patient_id)
        return {
            "reports": [
                {
                    "report_id": item["id"],
                    "patient_id": item["patient_id"],
                    "created_at": item["created_at"],
                    "risk_level": item["payload"].get("risk_level", "UNKNOWN"),
                }
                for item in reports
            ],
            "total": len(reports),
        }

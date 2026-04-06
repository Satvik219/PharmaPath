from __future__ import annotations

from flask import current_app

from pharmapath.integrations.drugbank import DrugBankClient


class DrugService:
    def __init__(self) -> None:
        self.client = DrugBankClient(
            current_app.config["DRUG_FIXTURE_PATH"],
            current_app.config["OPENFDA_API_KEY"],
            current_app.config["INDIA_MEDICINE_CATALOG_PATH"],
        )

    def search(self, query: str, limit: int) -> list[dict]:
        return self.client.search(query, limit)

    def get(self, drug_id: str) -> dict | None:
        return self.client.get(drug_id)

    def interactions_for(self, drug_id: str) -> dict:
        return {"drug_id": drug_id, "interactions": self.client.interactions_for(drug_id)}

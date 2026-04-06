from __future__ import annotations

import json
from pathlib import Path

from pharmapath.integrations.openfda import OpenFDAClient


class DrugBankClient:
    def __init__(self, fixture_path: str, openfda_api_key: str = "", india_catalog_path: str = "") -> None:
        self.fixture_path = Path(fixture_path)
        self.catalog = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        self.openfda = OpenFDAClient(openfda_api_key)
        self._remote_cache: dict[str, dict] = {}
        self.aliases = self._load_india_aliases(india_catalog_path)

    def search(self, query: str, limit: int = 10) -> list[dict]:
        lowered = query.lower()
        lowered = self.aliases.get(lowered, lowered)
        results = [
            drug
            for drug in self.catalog["drugs"]
            if lowered in drug["name"].lower() or lowered in drug["generic_name"].lower()
        ]
        if results:
            return results[:limit]

        remote = self.openfda.lookup_by_name(lowered)
        if remote:
            self._remote_cache[remote["drug_id"]] = remote
            return [remote]
        synthetic = self._build_synthetic_record(lowered)
        if synthetic:
            self._remote_cache[synthetic["drug_id"]] = synthetic
            return [synthetic]
        return results[:limit]

    def get(self, drug_id: str) -> dict | None:
        local = next((drug for drug in self.catalog["drugs"] if drug["drug_id"] == drug_id), None)
        if local:
            return local
        return self._remote_cache.get(drug_id)

    def resolve(self, identifier: str) -> dict | None:
        normalized = identifier.strip().lower()
        normalized = self.aliases.get(normalized, normalized)
        for drug in self.catalog["drugs"]:
            candidates = {
                drug["drug_id"].lower(),
                drug["name"].lower(),
                drug["generic_name"].lower(),
            }
            if normalized in candidates:
                return drug

        remote = self.openfda.lookup_by_name(normalized)
        if remote:
            self._remote_cache[remote["drug_id"]] = remote
            return remote
        synthetic = self._build_synthetic_record(normalized)
        if synthetic:
            self._remote_cache[synthetic["drug_id"]] = synthetic
            return synthetic
        return None

    def interactions_for(self, drug_id: str) -> list[dict]:
        return [edge for edge in self.catalog["interactions"] if edge["source"] == drug_id]

    def all_drugs(self) -> list[dict]:
        return self.catalog["drugs"]

    def all_interactions(self) -> list[dict]:
        return self.catalog["interactions"]

    def _load_india_aliases(self, india_catalog_path: str) -> dict[str, str]:
        if not india_catalog_path:
            return {}
        path = Path(india_catalog_path)
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {key.lower(): value.lower() for key, value in payload.get("aliases", {}).items()}

    def _build_synthetic_record(self, normalized_name: str) -> dict | None:
        if not normalized_name:
            return None

        title_name = " ".join(part.capitalize() for part in normalized_name.split())
        return {
            "drug_id": f"INDIA:{normalized_name.replace(' ', '_')}",
            "name": title_name,
            "generic_name": title_name,
            "drug_class": "India catalog lookup",
            "form": "Unknown",
            "half_life": "",
            "metabolism": "",
            "max_dose": "",
            "contraindications": [],
            "alternatives": [],
            "source": "india-catalog",
            "warnings": [],
        }

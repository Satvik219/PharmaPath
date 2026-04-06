from __future__ import annotations

from urllib.parse import quote

import requests


class OpenFDAClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "https://api.fda.gov/drug/label.json"

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def lookup_by_name(self, name: str) -> dict | None:
        if not self.is_configured():
            return None

        normalized = name.strip()
        if not normalized:
            return None

        search = (
            f'openfda.generic_name:"{normalized}"'
            f'+openfda.brand_name:"{normalized}"'
            f'+openfda.substance_name:"{normalized}"'
        )
        params = f"api_key={self.api_key}&search={quote(search, safe=':+\"')}&limit=1"

        try:
            response = requests.get(f"{self.base_url}?{params}", timeout=10)
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return None

        results = payload.get("results", [])
        if not results:
            return None
        return self._to_drug_record(results[0], normalized)

    def _to_drug_record(self, record: dict, fallback_name: str) -> dict:
        openfda = record.get("openfda", {})
        generic_name = self._first(openfda.get("generic_name")) or fallback_name
        brand_name = self._first(openfda.get("brand_name")) or generic_name
        product_type = self._first(openfda.get("product_type")) or "Drug"
        route = self._first(openfda.get("route")) or ""
        warnings = record.get("warnings") or record.get("warnings_and_cautions") or []
        contraindications = record.get("contraindications") or []

        return {
            "drug_id": f"OPENFDA:{generic_name.lower().replace(' ', '_')}",
            "name": brand_name,
            "generic_name": generic_name,
            "drug_class": product_type,
            "form": route or "Unknown",
            "half_life": "",
            "metabolism": "",
            "max_dose": "",
            "contraindications": contraindications[:5],
            "alternatives": [],
            "source": "openfda",
            "warnings": warnings[:3],
        }

    def _first(self, values: list[str] | None) -> str:
        return values[0] if values else ""

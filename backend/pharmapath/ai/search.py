from __future__ import annotations

import heapq
from collections.abc import Callable

import networkx as nx

from pharmapath.integrations.drugbank import DrugBankClient


class AlternativeSearchService:
    def __init__(self, client: DrugBankClient) -> None:
        self.client = client

    def find_alternatives(
        self,
        graph: nx.DiGraph,
        medications: list[str],
        scorer: Callable[[list[str]], dict],
    ) -> list[dict]:
        baseline = scorer(medications)
        if baseline["risk_score"] < 35:
            return []

        proposals = []
        for drug_id in medications:
            drug = self.client.get(drug_id)
            if not drug:
                continue
            for candidate in drug.get("alternatives", []):
                if candidate in medications or not graph.has_node(candidate):
                    continue
                proposed = [candidate if current == drug_id else current for current in medications]
                assessment = scorer(proposed)
                improvement = round(baseline["risk_score"] - assessment["risk_score"], 1)
                if improvement <= 0:
                    continue
                heapq.heappush(
                    proposals,
                    (
                        assessment["risk_score"],
                        {
                            "medications": proposed,
                            "total_risk_score": assessment["risk_score"],
                            "severity": assessment["severity"],
                            "risk_reduction": improvement,
                            "path_explanation": (
                                f"Replacing {self._drug_name(drug_id)} with {self._drug_name(candidate)} "
                                f"reduces the regimen risk by {improvement} points."
                            ),
                        },
                    ),
                )

        ranked = []
        while proposals and len(ranked) < 3:
            _, item = heapq.heappop(proposals)
            if item not in ranked:
                ranked.append(item)
        return ranked

    def _drug_name(self, drug_id: str) -> str:
        drug = self.client.get(drug_id)
        return drug["name"] if drug else drug_id

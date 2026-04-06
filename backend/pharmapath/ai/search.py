from __future__ import annotations

import heapq

import networkx as nx

from pharmapath.integrations.drugbank import DrugBankClient


class AlternativeSearchService:
    def __init__(self, client: DrugBankClient) -> None:
        self.client = client

    def find_alternatives(self, graph: nx.DiGraph, medications: list[str]) -> list[dict]:
        severe = any(
            graph.has_edge(a, b) and graph[a][b]["weight"] > 0.8
            for a in medications
            for b in medications
            if a != b
        )
        if not severe:
            return []

        proposals = []
        for drug_id in medications:
            drug = self.client.get(drug_id)
            if not drug:
                continue
            alternatives = drug.get("alternatives", [])
            for candidate in alternatives:
                proposed = [candidate if current == drug_id else current for current in medications]
                score = self._regimen_risk(graph, proposed)
                heapq.heappush(
                    proposals,
                    (
                        score,
                        {
                            "medications": proposed,
                            "total_risk_score": round(score, 3),
                            "path_explanation": f"Replaced {drug_id} with {candidate} to reduce cumulative interaction risk.",
                        },
                    ),
                )

        ranked = []
        while proposals and len(ranked) < 3:
            _, item = heapq.heappop(proposals)
            if item not in ranked:
                ranked.append(item)
        return ranked

    def _regimen_risk(self, graph: nx.DiGraph, medications: list[str]) -> float:
        total = 0.0
        for source in medications:
            for target in medications:
                if source == target:
                    continue
                if graph.has_edge(source, target):
                    total += graph[source][target]["weight"]
        return total


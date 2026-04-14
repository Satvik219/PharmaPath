from __future__ import annotations

from collections import defaultdict
from itertools import combinations

import networkx as nx

from pharmapath.integrations.drugbank import DrugBankClient


class GraphEngine:
    def __init__(self, client: DrugBankClient) -> None:
        self.client = client
        self._graph: nx.DiGraph | None = None

    def load_graph(self) -> nx.DiGraph:
        if self._graph is not None:
            return self._graph

        graph = nx.DiGraph()
        for drug in self.client.all_drugs():
            graph.add_node(
                drug["drug_id"],
                name=drug["name"],
                generic_name=drug.get("generic_name", drug["name"]),
                drug_class=drug.get("drug_class", "Unknown"),
                half_life=drug.get("half_life", ""),
                metabolism=drug.get("metabolism", ""),
                contraindications=drug.get("contraindications", []),
                alternatives=drug.get("alternatives", []),
            )

        for edge in self.client.all_interactions():
            self._add_edge(graph, edge["source"], edge["target"], edge)
            if edge.get("bidirectional"):
                self._add_edge(graph, edge["target"], edge["source"], {**edge, "bidirectional": True})

        self._graph = graph
        return graph

    def analyze_regimen(self, medications: list[str], max_hops: int = 3) -> dict:
        graph = self.load_graph()
        unique_medications = list(dict.fromkeys(medications))
        direct_interactions = self._direct_interactions(graph, unique_medications)
        chains = self._interaction_chains(graph, unique_medications, max_hops=max_hops)
        amplification = self._amplification_profile(graph, unique_medications, direct_interactions, chains)
        return {
            "medications": unique_medications,
            "direct_interactions": direct_interactions,
            "interaction_chains": chains,
            "amplification": amplification,
        }

    def build_subgraph(self, medications: list[str]) -> dict:
        analysis = self.analyze_regimen(medications)
        graph = self.load_graph()
        nodes = []
        edges = []

        for drug_id in analysis["medications"]:
            if not graph.has_node(drug_id):
                continue
            attrs = graph.nodes[drug_id]
            nodes.append(
                {
                    "id": drug_id,
                    "label": attrs["name"],
                    "risk": "watch",
                    "drug_class": attrs.get("drug_class", "Unknown"),
                }
            )

        for interaction in analysis["direct_interactions"]:
            edges.append(
                {
                    "source": interaction["source"],
                    "target": interaction["target"],
                    "weight": round(interaction["score"] / 100, 3),
                    "type": interaction["type"],
                    "severity": interaction["severity"],
                }
            )

        return {
            "nodes": nodes,
            "edges": edges,
            "chains": analysis["interaction_chains"],
            "amplification": analysis["amplification"],
        }

    def _add_edge(self, graph: nx.DiGraph, source: str, target: str, edge: dict) -> None:
        graph.add_edge(
            source,
            target,
            weight=edge["weight"],
            severity_label=edge["severity_label"],
            interaction_type=edge["interaction_type"],
            description=edge["description"],
            bidirectional=edge.get("bidirectional", False),
        )

    def _direct_interactions(self, graph: nx.DiGraph, medications: list[str]) -> list[dict]:
        interactions = []
        for source, target in combinations(medications, 2):
            if not graph.has_edge(source, target) and not graph.has_edge(target, source):
                continue
            edge = graph[source][target] if graph.has_edge(source, target) else graph[target][source]
            source_drug = self.client.get(source)
            target_drug = self.client.get(target)
            interactions.append(
                {
                    "source": source,
                    "target": target,
                    "source_name": source_drug["name"] if source_drug else source,
                    "target_name": target_drug["name"] if target_drug else target,
                    "score": round(edge["weight"] * 100, 1),
                    "score_normalized": round(edge["weight"], 3),
                    "severity": edge["severity_label"].upper(),
                    "type": edge["interaction_type"],
                    "description": edge["description"],
                }
            )
        return sorted(interactions, key=lambda item: item["score"], reverse=True)

    def _interaction_chains(self, graph: nx.DiGraph, medications: list[str], max_hops: int) -> list[dict]:
        chains: list[dict] = []
        seen_paths: set[tuple[str, ...]] = set()

        for source, target in combinations(medications, 2):
            if not graph.has_node(source) or not graph.has_node(target):
                continue
            for path in nx.all_simple_paths(graph, source=source, target=target, cutoff=max_hops):
                if len(path) < 3:
                    continue
                key = tuple(path)
                if key in seen_paths:
                    continue
                seen_paths.add(key)

                cumulative = 0.0
                steps = []
                for start, end in zip(path, path[1:]):
                    edge = graph[start][end]
                    cumulative += edge["weight"]
                    steps.append(
                        {
                            "source": start,
                            "target": end,
                            "type": edge["interaction_type"],
                            "severity": edge["severity_label"].upper(),
                            "description": edge["description"],
                        }
                    )

                chains.append(
                    {
                        "path": path,
                        "path_names": [self._drug_name(node) for node in path],
                        "hop_count": len(path) - 1,
                        "combined_score": round(min(100.0, cumulative * 30), 1),
                        "mechanism": " -> ".join(step["type"] for step in steps),
                        "steps": steps,
                    }
                )

        return sorted(chains, key=lambda item: (item["combined_score"], item["hop_count"]), reverse=True)[:5]

    def _amplification_profile(
        self,
        graph: nx.DiGraph,
        medications: list[str],
        direct_interactions: list[dict],
        chains: list[dict],
    ) -> dict:
        triggers: list[dict] = []
        per_drug_count = defaultdict(int)

        for interaction in direct_interactions:
            per_drug_count[interaction["source"]] += 1
            per_drug_count[interaction["target"]] += 1

        score = max(0, len(medications) - 2) * 4

        for drug_id, interaction_count in per_drug_count.items():
            if interaction_count >= 2:
                score += 6
                triggers.append(
                    {
                        "kind": "shared-driver",
                        "drug_id": drug_id,
                        "drug_name": self._drug_name(drug_id),
                        "detail": f"{self._drug_name(drug_id)} participates in {interaction_count} separate interaction links.",
                    }
                )

        metabolism_buckets = defaultdict(list)
        for drug_id in medications:
            if not graph.has_node(drug_id):
                continue
            metabolism = (graph.nodes[drug_id].get("metabolism") or "").strip()
            if metabolism:
                metabolism_buckets[metabolism.lower()].append(drug_id)

        for metabolism, members in metabolism_buckets.items():
            if len(members) >= 2:
                score += 5
                triggers.append(
                    {
                        "kind": "shared-metabolism",
                        "drug_ids": members,
                        "detail": f"Multiple drugs share the metabolism pathway: {metabolism}.",
                    }
                )

        if chains:
            score += min(12, len(chains) * 4)
            triggers.append(
                {
                    "kind": "multi-hop-chain",
                    "detail": f"{len(chains)} interaction chain(s) were detected across the regimen.",
                }
            )

        return {
            "score": round(min(30.0, float(score)), 1),
            "triggers": triggers,
        }

    def _drug_name(self, drug_id: str) -> str:
        drug = self.client.get(drug_id)
        return drug["name"] if drug else drug_id

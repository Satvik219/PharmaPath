from __future__ import annotations

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
                drug_class=drug["drug_class"],
                half_life=drug.get("half_life", ""),
                metabolism=drug.get("metabolism", ""),
            )

        for edge in self.client.all_interactions():
            graph.add_edge(
                edge["source"],
                edge["target"],
                weight=edge["weight"],
                severity_label=edge["severity_label"],
                interaction_type=edge["interaction_type"],
                description=edge["description"],
                bidirectional=edge.get("bidirectional", False),
            )
            if edge.get("bidirectional"):
                graph.add_edge(
                    edge["target"],
                    edge["source"],
                    weight=edge["weight"],
                    severity_label=edge["severity_label"],
                    interaction_type=edge["interaction_type"],
                    description=edge["description"],
                    bidirectional=True,
                )

        self._graph = graph
        return graph

    def build_subgraph(self, medications: list[str]) -> dict:
        graph = self.load_graph()
        nodes = []
        edges = []
        for drug_id in medications:
            if graph.has_node(drug_id):
                attrs = graph.nodes[drug_id]
                nodes.append({"id": drug_id, "label": attrs["name"], "risk": "watch"})

        for source in medications:
            for target in medications:
                if source == target or not graph.has_edge(source, target):
                    continue
                attrs = graph[source][target]
                edges.append(
                    {
                        "source": source,
                        "target": target,
                        "weight": attrs["weight"],
                        "type": attrs["interaction_type"],
                        "severity": attrs["severity_label"],
                    }
                )

        return {"nodes": nodes, "edges": edges}


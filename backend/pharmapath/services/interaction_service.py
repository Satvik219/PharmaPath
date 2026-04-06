from __future__ import annotations

from flask import current_app

from pharmapath.ai.bayes import BayesianRiskService
from pharmapath.ai.graph_engine import GraphEngine
from pharmapath.ai.search import AlternativeSearchService
from pharmapath.integrations.drugbank import DrugBankClient
from pharmapath.repositories.session_repository import SessionRepository
from pharmapath.utils.ids import new_id
from pharmapath.utils.time import utc_now_iso


class InteractionService:
    def __init__(self) -> None:
        self.client = DrugBankClient(
            current_app.config["DRUG_FIXTURE_PATH"],
            current_app.config["OPENFDA_API_KEY"],
            current_app.config["INDIA_MEDICINE_CATALOG_PATH"],
        )
        self.graph_engine = GraphEngine(self.client)
        self.search_service = AlternativeSearchService(self.client)
        self.bayes_service = BayesianRiskService()
        self.session_repo = SessionRepository(current_app.config["DATABASE_PATH"])

    def check_interactions(self, payload: dict, user_id: str) -> dict:
        medications = payload.get("medications", [])
        patient = payload.get("patient", {})
        patient_id = payload.get("patient_id")
        resolved = self._resolve_medications(medications)
        resolved_ids = [item["drug_id"] for item in resolved["resolved_medications"]]

        graph = self.graph_engine.load_graph()
        self._ensure_graph_nodes(graph, resolved["resolved_medications"])
        risk_pairs = self._pairwise_scan(graph, resolved_ids)
        adjusted_pairs, flags = self.bayes_service.adjust_scores(risk_pairs, patient)
        alternatives = self.search_service.find_alternatives(graph, resolved_ids)
        decorated_alternatives = self._decorate_alternatives(alternatives)
        graph_json = self.graph_engine.build_subgraph(resolved_ids)
        comparison_graph = self._build_comparison_graph(graph, resolved_ids, decorated_alternatives)

        overall_risk = self._overall_risk(adjusted_pairs)
        result = {
            "submitted_medications": medications,
            "resolved_medications": resolved["resolved_medications"],
            "unmatched_medications": resolved["unmatched_medications"],
            "risk_pairs": adjusted_pairs,
            "overall_risk": overall_risk,
            "bayesian_flags": flags,
            "safe_alternatives": decorated_alternatives,
            "astar_summary": self._build_astar_summary(resolved_ids, decorated_alternatives, overall_risk),
            "graph_path": graph_json,
            "comparison_graph": comparison_graph,
            "user_summary": self._build_user_summary(overall_risk, adjusted_pairs, flags, resolved["unmatched_medications"]),
        }

        session_id = new_id()
        self.session_repo.create_session(
            {
                "id": session_id,
                "patient_id": patient_id,
                "user_id": user_id,
                "medications": resolved_ids,
                "created_at": utc_now_iso(),
            }
        )
        self.session_repo.create_result(
            {
                "id": new_id(),
                "session_id": session_id,
                "overall_risk": overall_risk,
                "risk_pairs": adjusted_pairs,
                "alternatives": alternatives,
                "graph_json": graph_json,
                "bayesian_flags": flags,
                "created_at": utc_now_iso(),
            }
        )
        result["session_id"] = session_id
        return result

    def alternatives(self, payload: dict) -> dict:
        graph = self.graph_engine.load_graph()
        medications = payload.get("current_medications", [])
        return {"alternatives": self.search_service.find_alternatives(graph, medications)}

    def graph(self, drugs: list[str]) -> dict:
        return self.graph_engine.build_subgraph(drugs)

    def severity_levels(self) -> dict:
        return {
            "levels": [
                {"code": "LOW", "label": "Low", "color": "#6c8a5c", "description": "Low clinical concern"},
                {"code": "MODERATE", "label": "Moderate", "color": "#c8952d", "description": "Requires review"},
                {"code": "HIGH", "label": "High", "color": "#c24d3f", "description": "Prompt intervention recommended"},
            ]
        }

    def _pairwise_scan(self, graph, medications: list[str]) -> list[dict]:
        pairs = []
        for source in medications:
            for target in medications:
                if source == target or not graph.has_edge(source, target):
                    continue
                edge = graph[source][target]
                source_drug = self.client.get(source)
                target_drug = self.client.get(target)
                pairs.append(
                    {
                        "source": source,
                        "target": target,
                        "source_name": source_drug["name"] if source_drug else source,
                        "target_name": target_drug["name"] if target_drug else target,
                        "score": round(edge["weight"], 3),
                        "severity": edge["severity_label"].upper(),
                        "type": edge["interaction_type"],
                        "description": edge["description"],
                    }
                )
        return sorted(pairs, key=lambda item: item["score"], reverse=True)

    def _overall_risk(self, risk_pairs: list[dict]) -> str:
        if not risk_pairs:
            return "LOW"
        top_score = max(pair.get("adjusted_score", pair["score"]) for pair in risk_pairs)
        if top_score > 0.8:
            return "HIGH"
        if top_score > 0.45:
            return "MODERATE"
        return "LOW"

    def _resolve_medications(self, medications: list[str]) -> dict:
        resolved_medications = []
        unmatched_medications = []
        seen_ids = set()

        for item in medications:
            drug = self.client.resolve(item)
            if drug is None:
                unmatched_medications.append(item)
                continue
            if drug["drug_id"] in seen_ids:
                continue
            seen_ids.add(drug["drug_id"])
            resolved_medications.append(
                {
                    "input": item,
                    "drug_id": drug["drug_id"],
                    "name": drug["name"],
                    "generic_name": drug["generic_name"],
                }
            )

        return {
            "resolved_medications": resolved_medications,
            "unmatched_medications": unmatched_medications,
        }

    def _decorate_alternatives(self, alternatives: list[dict]) -> list[dict]:
        decorated = []
        for item in alternatives:
            medication_names = []
            for drug_id in item["medications"]:
                drug = self.client.get(drug_id)
                medication_names.append(drug["name"] if drug else drug_id)
            decorated.append({**item, "medication_names": medication_names})
        return decorated

    def _build_user_summary(
        self,
        overall_risk: str,
        risk_pairs: list[dict],
        bayesian_flags: list[dict],
        unmatched_medications: list[str],
    ) -> dict:
        if overall_risk == "HIGH":
            title = "Please talk to your doctor or pharmacist before taking this combination."
            action = "At least one medicine pair looks high risk, so professional review is strongly recommended before continuing."
        elif overall_risk == "MODERATE":
            title = "This combination should be reviewed by a healthcare professional."
            action = "The medicines are not the highest risk, but they may still need dose changes, monitoring, or timing adjustments."
        else:
            title = "No major interaction was found in this quick check."
            action = "Even with a low-risk result, continue only as prescribed and confirm changes with a healthcare professional."

        if bayesian_flags:
            action += " Your age or health conditions may increase the chance of side effects."

        if unmatched_medications:
            action += " Some medicine names could not be matched, so the result may be incomplete."

        top_pair = risk_pairs[0] if risk_pairs else None
        if top_pair:
            why = (
                f"The main concern is {top_pair['source_name']} with {top_pair['target_name']}, "
                f"which may cause {top_pair['type'].lower()}."
            )
        elif unmatched_medications:
            why = "No final interaction check could be completed for every medicine because some names were not recognized."
        else:
            why = "No direct interaction was found among the medicines that were recognized."

        return {
            "title": title,
            "action": action,
            "why": why,
        }

    def _build_astar_summary(self, current_medications: list[str], alternatives: list[dict], overall_risk: str) -> dict:
        if not alternatives:
            if overall_risk == "HIGH":
                summary = "A* search was checked, but no better medicine combination was found in the current sample dataset."
            else:
                summary = "A* search did not need to replace any medicine because the current set did not trigger a severe enough interaction in this dataset."
            return {
                "triggered": overall_risk == "HIGH",
                "summary": summary,
                "result": None,
            }

        best_option = alternatives[0]
        current_names = [self.client.get(drug_id)["name"] if self.client.get(drug_id) else drug_id for drug_id in current_medications]
        return {
            "triggered": True,
            "summary": "A* search tested alternative medicine paths and picked the lowest-risk option it found.",
            "result": {
                "current_medications": current_names,
                "suggested_medications": best_option["medication_names"],
                "estimated_risk_score": best_option["total_risk_score"],
                "explanation": best_option["path_explanation"],
            },
        }

    def _build_comparison_graph(self, graph, current_medications: list[str], alternatives: list[dict]) -> dict:
        nodes = []
        edges = []
        current_set = set(current_medications)

        for drug_id in current_medications:
            drug = self.client.get(drug_id)
            nodes.append(
                {
                    "id": f"current:{drug_id}",
                    "drug_id": drug_id,
                    "label": drug["name"] if drug else drug_id,
                    "group": "current",
                }
            )

        for source in current_medications:
            for target in current_medications:
                if source == target or not graph.has_edge(source, target):
                    continue
                edge = graph[source][target]
                edges.append(
                    {
                        "source": f"current:{source}",
                        "target": f"current:{target}",
                        "kind": "interaction",
                        "severity": edge["severity_label"],
                        "weight": edge["weight"],
                        "label": edge["interaction_type"],
                    }
                )

        if alternatives:
            best_option = alternatives[0]
            for drug_id in best_option["medications"]:
                drug = self.client.get(drug_id)
                nodes.append(
                    {
                        "id": f"suggested:{drug_id}",
                        "drug_id": drug_id,
                        "label": drug["name"] if drug else drug_id,
                        "group": "suggested",
                    }
                )

            for source in best_option["medications"]:
                for target in best_option["medications"]:
                    if source == target or not graph.has_edge(source, target):
                        continue
                    edge = graph[source][target]
                    edges.append(
                        {
                            "source": f"suggested:{source}",
                            "target": f"suggested:{target}",
                            "kind": "interaction",
                            "severity": edge["severity_label"],
                            "weight": edge["weight"],
                            "label": edge["interaction_type"],
                        }
                    )

            for index, drug_id in enumerate(best_option["medications"]):
                if drug_id in current_set:
                    edges.append(
                        {
                            "source": f"current:{drug_id}",
                            "target": f"suggested:{drug_id}",
                            "kind": "same-medicine",
                            "severity": "info",
                            "weight": 0,
                            "label": "kept",
                        }
                    )
                    continue

                if index < len(current_medications):
                    edges.append(
                        {
                            "source": f"current:{current_medications[index]}",
                            "target": f"suggested:{drug_id}",
                            "kind": "replacement",
                            "severity": "info",
                            "weight": 0,
                            "label": "A* suggestion",
                        }
                    )

        return {"nodes": nodes, "edges": edges}

    def _ensure_graph_nodes(self, graph, resolved_medications: list[dict]) -> None:
        for item in resolved_medications:
            if graph.has_node(item["drug_id"]):
                continue
            graph.add_node(
                item["drug_id"],
                name=item["name"],
                drug_class="External lookup",
                half_life="",
                metabolism="",
            )

from __future__ import annotations

from datetime import date, datetime

from flask import current_app

from pharmapath.ai.bayes import BayesianRiskService
from pharmapath.ai.graph_engine import GraphEngine
from pharmapath.ai.search import AlternativeSearchService
from pharmapath.integrations.drugbank import DrugBankClient
from pharmapath.repositories.patient_repository import PatientRepository
from pharmapath.repositories.session_repository import SessionRepository
from pharmapath.services.gemini_service import GeminiService
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
        self.gemini_service = GeminiService()
        db_path = current_app.config["DATABASE_PATH"]
        self.session_repo = SessionRepository(db_path)
        self.patient_repo = PatientRepository(db_path)

    def check_interactions(self, payload: dict, user_id: str) -> dict:
        response = self._analyze_payload(payload, user_id=user_id, persist=True)
        return response

    def analyze_context(self, payload: dict, user_id: str) -> dict:
        return self._analyze_payload(payload, user_id=user_id, persist=False)

    def simulate(self, payload: dict, user_id: str) -> dict:
        patient = payload.get("patient", {})
        current_drugs = payload.get("current_drugs", [])
        add_drug = payload.get("add")
        remove_drug = payload.get("remove")

        before_payload = {
            "medications": current_drugs,
            "patient": patient,
            "patient_id": payload.get("patient_id"),
        }
        after_drugs = [drug for drug in current_drugs if not remove_drug or drug.lower() != remove_drug.lower()]
        if add_drug:
            after_drugs.append(add_drug)

        before = self._analyze_payload(before_payload, user_id=user_id, persist=False)
        after = self._analyze_payload(
            {
                "medications": after_drugs,
                "patient": patient,
                "patient_id": payload.get("patient_id"),
            },
            user_id=user_id,
            persist=False,
        )

        simulation = {
            "before_score": before["risk_score"],
            "after_score": after["risk_score"],
            "delta": round(after["risk_score"] - before["risk_score"], 1),
            "change_summary": {
                "added": add_drug,
                "removed": remove_drug,
                "before_drugs": before["drugs"],
                "after_drugs": after["drugs"],
            },
            "comparison": self.gemini_service.explain_simulation({"before": before, "after": after}),
        }

        return {
            **after,
            "simulation": simulation,
            "explanation": simulation["comparison"],
            "chat_response": None,
            "suggested_questions": self._suggested_questions(after["interactions"]),
        }

    def alternatives(self, payload: dict) -> dict:
        graph = self.graph_engine.load_graph()
        medications = payload.get("current_medications", [])
        patient = self._resolve_patient(payload.get("patient", {}), payload.get("patient_id"), medications)
        resolved = self._resolve_medications(medications)
        alternatives = self.search_service.find_alternatives(
            graph,
            [item["drug_id"] for item in resolved["resolved_medications"]],
            lambda regimen: self._quick_score(regimen, patient),
        )
        return {"alternatives": self._decorate_alternatives(alternatives)}

    def graph(self, drugs: list[str]) -> dict:
        return self.graph_engine.build_subgraph(drugs)

    def severity_levels(self) -> dict:
        return {
            "levels": [
                {"code": "low", "label": "Safe", "color": "#6c8a5c", "description": "Low clinical concern"},
                {"code": "moderate", "label": "Moderate", "color": "#c8952d", "description": "Requires review"},
                {"code": "high", "label": "Dangerous", "color": "#c24d3f", "description": "Prompt intervention recommended"},
            ]
        }

    def _analyze_payload(self, payload: dict, user_id: str, persist: bool) -> dict:
        medications = payload.get("medications", [])
        patient = self._resolve_patient(payload.get("patient", {}), payload.get("patient_id"), medications)
        resolved = self._resolve_medications(medications)
        resolved_ids = [item["drug_id"] for item in resolved["resolved_medications"]]
        graph = self.graph_engine.load_graph()
        self._ensure_graph_nodes(graph, resolved["resolved_medications"])

        scored = self._score_regimen(resolved_ids, patient)
        decorated_alternatives = self._decorate_alternatives(scored["alternatives"])
        explanation = self.gemini_service.explain_interaction(
            {
                "patient": patient,
                "drugs": scored["drug_names"],
                "interactions": scored["summary"]["interactions"],
                "patient_factors": scored["summary"]["patient_factors"],
                "risk_score": scored["summary"]["risk_score"],
            }
        )
        recommendations = self.gemini_service.recommend(
            {
                "patient": patient,
                "drugs": scored["drug_names"],
                "interactions": scored["summary"]["interactions"],
                "risk_score": scored["summary"]["risk_score"],
                "safe_alternatives": decorated_alternatives,
            }
        )
        graph_json = self.graph_engine.build_subgraph(resolved_ids)
        comparison_graph = self._build_comparison_graph(graph, resolved_ids, decorated_alternatives)

        result = {
            "patient": patient,
            "drugs": scored["drug_names"],
            "risk_score": scored["summary"]["risk_score"],
            "label": scored["summary"]["risk_label"],
            "severity": scored["summary"]["severity"],
            "interactions": scored["summary"]["interactions"],
            "interactions_overview": {
                "multi_hop_chains": scored["analysis"]["interaction_chains"],
                "amplification": scored["analysis"]["amplification"],
                "components": scored["summary"]["components"],
                "bayesian_flags": scored["summary"]["bayesian_flags"],
            },
            "explanation": explanation,
            "recommendations": recommendations,
            "simulation": None,
            "chat_response": None,
            "suggested_questions": self._suggested_questions(scored["summary"]["interactions"]),
            "submitted_medications": medications,
            "resolved_medications": resolved["resolved_medications"],
            "unmatched_medications": resolved["unmatched_medications"],
            "safe_alternatives": decorated_alternatives,
            "graph_path": graph_json,
            "comparison_graph": comparison_graph,
            "ai_meta": self.gemini_service.status(),
        }

        if persist:
            session_id = new_id()
            self.session_repo.create_session(
                {
                    "id": session_id,
                    "patient_id": payload.get("patient_id"),
                    "user_id": user_id,
                    "medications": resolved_ids,
                    "created_at": utc_now_iso(),
                }
            )
            self.session_repo.create_result(
                {
                    "id": new_id(),
                    "session_id": session_id,
                    "overall_risk": result["severity"],
                    "risk_pairs": result["interactions"],
                    "alternatives": decorated_alternatives,
                    "graph_json": graph_json,
                    "bayesian_flags": result["interactions_overview"]["bayesian_flags"],
                    "created_at": utc_now_iso(),
                }
            )
            result["session_id"] = session_id

        return result

    def _score_regimen(self, regimen: list[str], patient: dict) -> dict:
        analysis = self.graph_engine.analyze_regimen(regimen)
        resolved_medications = [self._drug_summary(drug_id) for drug_id in regimen]
        summary = self.bayes_service.assess_regimen(
            analysis["direct_interactions"],
            patient,
            resolved_medications,
            analysis,
        )
        alternatives = self.search_service.find_alternatives(
            self.graph_engine.load_graph(),
            regimen,
            lambda candidate: self._quick_score(candidate, patient),
        )
        return {
            "analysis": analysis,
            "summary": summary,
            "alternatives": alternatives,
            "drug_names": [item["name"] for item in resolved_medications if item],
        }

    def _quick_score(self, regimen: list[str], patient: dict) -> dict:
        analysis = self.graph_engine.analyze_regimen(regimen)
        resolved_medications = [self._drug_summary(drug_id) for drug_id in regimen]
        summary = self.bayes_service.assess_regimen(
            analysis["direct_interactions"],
            patient,
            resolved_medications,
            analysis,
        )
        return summary

    def _resolve_patient(self, incoming_patient: dict, patient_id: str | None, medications: list[str]) -> dict:
        stored = self.patient_repo.get(patient_id) if patient_id else None
        conditions = incoming_patient.get("diseases", incoming_patient.get("conditions"))
        current_medications = incoming_patient.get("current_medications", incoming_patient.get("medications"))
        patient = {
            "patient_id": patient_id,
            "age": incoming_patient.get("age") or self._age_from_dob(incoming_patient.get("dob")),
            "diseases": conditions or [],
            "conditions": conditions or [],
            "allergies": incoming_patient.get("allergies", []),
            "current_medications": current_medications or medications,
        }

        if stored:
            stored_conditions = stored.get("conditions", [])
            stored_age = self._age_from_dob(stored.get("dob"))
            patient["age"] = patient["age"] or stored_age
            patient["conditions"] = patient["conditions"] or stored_conditions
            patient["diseases"] = patient["diseases"] or stored_conditions
            patient["allergies"] = patient["allergies"] or stored.get("allergies", [])
            patient["current_medications"] = patient["current_medications"] or stored.get("current_medications", [])

        return patient

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
                    "drug_class": drug.get("drug_class", "Unknown"),
                    "contraindications": drug.get("contraindications", []),
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

    def _build_comparison_graph(self, graph, current_medications: list[str], alternatives: list[dict]) -> dict:
        nodes = []
        edges = []
        current_set = set(current_medications)

        for drug_id in current_medications:
            nodes.append({"id": f"current:{drug_id}", "drug_id": drug_id, "label": self._drug_name(drug_id), "group": "current"})

        for interaction in self.graph_engine.analyze_regimen(current_medications)["direct_interactions"]:
            edges.append(
                {
                    "source": f"current:{interaction['source']}",
                    "target": f"current:{interaction['target']}",
                    "kind": "interaction",
                    "severity": interaction["severity"],
                    "weight": round(interaction["score"] / 100, 3),
                    "label": interaction["type"],
                }
            )

        if alternatives:
            best_option = alternatives[0]
            for drug_id in best_option["medications"]:
                nodes.append(
                    {
                        "id": f"suggested:{drug_id}",
                        "drug_id": drug_id,
                        "label": self._drug_name(drug_id),
                        "group": "suggested",
                    }
                )

            for interaction in self.graph_engine.analyze_regimen(best_option["medications"])["direct_interactions"]:
                edges.append(
                    {
                        "source": f"suggested:{interaction['source']}",
                        "target": f"suggested:{interaction['target']}",
                        "kind": "interaction",
                        "severity": interaction["severity"],
                        "weight": round(interaction["score"] / 100, 3),
                        "label": interaction["type"],
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
                elif index < len(current_medications):
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

    def _suggested_questions(self, interactions: list[dict]) -> list[str]:
        if interactions:
            top = interactions[0]
            return [
                f"What happens if I remove {top['source_name']}?",
                "Is there a safer alternative?",
                "Why is this interaction dangerous?",
            ]
        return [
            "What happens if I add another medication?",
            "Is there a safer alternative?",
            "Why is this interaction dangerous?",
        ]

    def _age_from_dob(self, dob: str | None) -> int | None:
        if not dob:
            return None
        try:
            dob_date = datetime.strptime(dob, "%Y-%m-%d").date()
        except ValueError:
            return None
        today = date.today()
        return today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))

    def _drug_summary(self, drug_id: str) -> dict:
        drug = self.client.get(drug_id)
        if not drug:
            return {
                "drug_id": drug_id,
                "name": drug_id,
                "generic_name": drug_id,
                "drug_class": "Unknown",
                "contraindications": [],
            }
        return {
            "drug_id": drug_id,
            "name": drug["name"],
            "generic_name": drug.get("generic_name", drug["name"]),
            "drug_class": drug.get("drug_class", "Unknown"),
            "contraindications": drug.get("contraindications", []),
        }

    def _drug_name(self, drug_id: str) -> str:
        return self._drug_summary(drug_id)["name"]

    def _ensure_graph_nodes(self, graph, resolved_medications: list[dict]) -> None:
        for item in resolved_medications:
            if graph.has_node(item["drug_id"]):
                continue
            graph.add_node(
                item["drug_id"],
                name=item["name"],
                drug_class=item.get("drug_class", "External lookup"),
                half_life="",
                metabolism="",
                contraindications=item.get("contraindications", []),
                alternatives=[],
            )

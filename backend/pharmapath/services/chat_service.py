from __future__ import annotations

from pharmapath.services.gemini_service import GeminiService
from pharmapath.services.interaction_service import InteractionService
from pharmapath.utils.ids import new_id


class ChatService:
    _sessions: dict[str, list[dict]] = {}

    def __init__(self) -> None:
        self.gemini_service = GeminiService()
        self.interaction_service = InteractionService()

    def chat(self, payload: dict, user_id: str) -> dict:
        session_id = payload.get("session_id") or new_id()
        history = self._sessions.setdefault(session_id, [])
        message = (payload.get("message") or "").strip()
        history.append({"role": "user", "message": message})

        intent = self._route_intent(message, payload)
        patient = payload.get("patient", {})
        medications = payload.get("drugs", payload.get("medications", payload.get("current_drugs", [])))
        patient_id = payload.get("patient_id")

        analysis = None
        simulation = None
        fallback_response = "I can help answer follow-up questions about the current medication safety profile."

        if intent == "simulation":
            simulation = self.interaction_service.simulate(
                {
                    "current_drugs": payload.get("current_drugs", medications),
                    "add": payload.get("add"),
                    "remove": payload.get("remove"),
                    "patient": patient,
                    "patient_id": patient_id,
                },
                user_id=user_id,
            )
            fallback_response = simulation["explanation"]
        elif medications:
            analysis = self.interaction_service.analyze_context(
                {"medications": medications, "patient": patient, "patient_id": patient_id},
                user_id=user_id,
            )
            fallback_response = analysis["explanation"] if intent == "explanation" else "\n".join(analysis["recommendations"])

        context = {
            "intent": intent,
            "patient": patient,
            "drugs": medications,
            "analysis": analysis,
            "simulation": simulation,
            "fallback_response": fallback_response,
        }
        response_text = self.gemini_service.chat(history, context)
        history.append({"role": "assistant", "message": response_text})

        base = analysis or self._empty_response(patient, medications)
        if simulation:
            base = {**simulation}

        return {
            **base,
            "simulation": simulation["simulation"] if simulation else base.get("simulation"),
            "chat_response": response_text,
            "session_id": session_id,
            "ai_meta": self.gemini_service.status(),
            "suggested_questions": base.get("suggested_questions")
            or [
                "What happens if I remove Drug X?",
                "Is there a safer alternative?",
                "Why is this interaction dangerous?",
            ],
        }

    def _route_intent(self, message: str, payload: dict) -> str:
        lower = message.lower()
        if payload.get("add") or payload.get("remove") or payload.get("current_drugs"):
            return "simulation"
        if any(keyword in lower for keyword in ["what if", "remove", "stop", "add", "replace", "swap"]):
            return "simulation"
        if any(keyword in lower for keyword in ["alternative", "safer", "substitute", "recommend"]):
            return "recommendation"
        if any(keyword in lower for keyword in ["why", "dangerous", "causing", "explain", "problem"]):
            return "explanation"
        return "general"

    def _empty_response(self, patient: dict, medications: list[str]) -> dict:
        return {
            "patient": patient,
            "drugs": medications,
            "risk_score": 0,
            "label": "safe",
            "severity": "low",
            "interactions": [],
            "explanation": "No structured regimen context was provided for a deeper interaction analysis.",
            "recommendations": [],
            "simulation": None,
            "chat_response": None,
            "suggested_questions": [
                "What happens if I remove Drug X?",
                "Is there a safer alternative?",
                "Why is this interaction dangerous?",
            ],
        }

from __future__ import annotations

import json

import requests
from flask import current_app


class GeminiService:
    SYSTEM_PROMPT = (
        "You are a clinical AI assistant. Answer drug-related queries safely using provided data. "
        "Do not hallucinate. Be clear about uncertainty and never override the structured backend risk score."
    )

    def __init__(self) -> None:
        self.api_key = current_app.config.get("GEMINI_API_KEY", "")
        preferred_model = current_app.config.get("GEMINI_MODEL", "gemini-2.5-flash")
        self.model_candidates = self._build_model_candidates(preferred_model)
        self.last_status = {"used_model": None, "source": "fallback", "error": None}

    def explain_interaction(self, payload: dict) -> str:
        prompt = (
            "Explain why the following regimen is risky for this patient. Include biological reasoning, "
            "patient-specific factors, and the main drug drivers.\n"
            f"{json.dumps(payload, indent=2)}"
        )
        fallback = self._fallback_interaction_explanation(payload)
        return self._generate_text(prompt, fallback)

    def recommend(self, payload: dict) -> list[str]:
        prompt = (
            "Suggest safer alternatives or mitigation steps for this drug regimen. Keep it practical and grounded "
            "in the provided analysis. Return each recommendation on a new line.\n"
            f"{json.dumps(payload, indent=2)}"
        )
        fallback_items = self._fallback_recommendations(payload)
        text = self._generate_text(prompt, "\n".join(f"- {item}" for item in fallback_items))
        parsed = [line.strip("- ").strip() for line in text.splitlines() if line.strip()]
        return parsed[:5] or fallback_items

    def explain_simulation(self, payload: dict) -> str:
        prompt = (
            "Compare the before and after drug regimen analyses. Explain what changed, why the risk moved, "
            "and which medication change mattered most.\n"
            f"{json.dumps(payload, indent=2)}"
        )
        fallback = self._fallback_simulation_explanation(payload)
        return self._generate_text(prompt, fallback)

    def chat(self, session_history: list[dict], context: dict) -> str:
        prompt = (
            f"{self.SYSTEM_PROMPT}\n\nConversation history:\n"
            f"{json.dumps(session_history, indent=2)}\n\nContext:\n{json.dumps(context, indent=2)}"
        )
        fallback = context.get("fallback_response") or "I can help explain the current drug safety assessment."
        return self._generate_text(prompt, fallback)

    def status(self) -> dict:
        return dict(self.last_status)

    def _generate_text(self, prompt: str, fallback: str) -> str:
        if not self.api_key:
            self.last_status = {"used_model": None, "source": "fallback", "error": "Missing Gemini API key"}
            return fallback

        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{self.SYSTEM_PROMPT}\n\n{prompt}"}],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.8,
                "maxOutputTokens": 500,
            },
        }

        last_error = None
        for model_name in self.model_candidates:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            try:
                response = requests.post(
                    url,
                    json=body,
                    headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                    timeout=20,
                )
                if response.status_code >= 400:
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    continue

                payload = response.json()
                candidates = payload.get("candidates", [])
                if not candidates:
                    last_error = "No candidates returned from Gemini."
                    continue
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(part.get("text", "") for part in parts).strip()
                if text:
                    self.last_status = {"used_model": model_name, "source": "gemini", "error": None}
                    return text
                last_error = "Gemini returned an empty text response."
            except requests.RequestException as exc:
                last_error = str(exc)

        self.last_status = {"used_model": None, "source": "fallback", "error": last_error}
        return fallback

    def _build_model_candidates(self, preferred_model: str) -> list[str]:
        candidates = [
            preferred_model,
            "gemini-2.5-flash",
            "gemini-flash-latest",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
        ]
        ordered = []
        for candidate in candidates:
            if candidate and candidate not in ordered:
                ordered.append(candidate)
        return ordered

    def _fallback_interaction_explanation(self, payload: dict) -> str:
        interactions = payload.get("interactions", [])
        patient_factors = payload.get("patient_factors", [])
        if not interactions:
            return "No direct interaction was detected in the submitted regimen, although routine clinical review is still recommended."

        top = interactions[0]
        explanation = (
            f"The main risk comes from {top['source_name']} with {top['target_name']}, which is linked to "
            f"{top['type'].lower()}. The regimen score is driven by a direct interaction score of {top['base_score']:.1f}"
        )
        if patient_factors:
            explanation += f" and rises further because of patient-specific factors such as {patient_factors[0].lower()}"
        explanation += "."
        return explanation

    def _fallback_recommendations(self, payload: dict) -> list[str]:
        alternatives = payload.get("safe_alternatives", [])
        recommendations = []
        if alternatives:
            best = alternatives[0]
            recommendations.append(
                f"Consider the lower-risk regimen: {', '.join(best.get('medication_names', best.get('medications', [])))}."
            )
        recommendations.append("Review the highest-risk pair with a clinician before making changes.")
        recommendations.append("Increase monitoring for symptoms tied to the detected interaction mechanism.")
        return recommendations[:3]

    def _fallback_simulation_explanation(self, payload: dict) -> str:
        before = payload.get("before", {})
        after = payload.get("after", {})
        delta = round(after.get("risk_score", 0) - before.get("risk_score", 0), 1)
        if delta > 0:
            return f"The simulated change increases the regimen risk by {delta} points, mainly by adding new interaction pressure or amplification."
        if delta < 0:
            return f"The simulated change lowers the regimen risk by {abs(delta)} points by removing one of the stronger interaction drivers."
        return "The simulation does not materially change the overall risk score in the current knowledge graph."

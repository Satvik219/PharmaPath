from __future__ import annotations


class BayesianRiskService:
    def adjust_scores(self, risk_pairs: list[dict], patient: dict) -> tuple[list[dict], list[dict]]:
        flags: list[dict] = []
        age = patient.get("age") or 0
        conditions = {condition.lower() for condition in patient.get("conditions", [])}
        liver_function = (patient.get("liver_function") or "").lower()
        renal_function = (patient.get("renal_function") or "").lower()
        weight_kg = patient.get("weight_kg") or 0

        for pair in risk_pairs:
            adjustment = 0.0
            reason_parts = []

            if age >= 70:
                adjustment += 0.15
                reason_parts.append("age > 70")
            if liver_function in {"reduced", "impaired"}:
                adjustment += 0.1
                reason_parts.append("reduced liver function")
            if renal_function in {"reduced", "impaired"}:
                adjustment += 0.1
                reason_parts.append("renal impairment")
            if "diabetes" in conditions:
                adjustment += 0.05
                reason_parts.append("diabetes")
            if weight_kg and weight_kg < 50:
                adjustment += 0.05
                reason_parts.append("low body weight")

            pair["adjusted_score"] = min(1.0, round(pair["score"] + adjustment, 3))
            pair["bayesian_reasoning"] = reason_parts

            if reason_parts:
                flags.append(
                    {
                        "pair": [pair["source"], pair["target"]],
                        "delta": round(adjustment, 3),
                        "reasons": reason_parts,
                    }
                )

        return risk_pairs, flags


from __future__ import annotations


class BayesianRiskService:
    CONDITION_WEIGHTS = {
        "kidney": 12,
        "renal": 12,
        "liver": 12,
        "hepatic": 12,
        "bleeding": 12,
        "ulcer": 9,
        "diabetes": 6,
        "heart": 8,
        "cardiac": 8,
        "hypertension": 5,
        "pregnan": 10,
        "asthma": 5,
    }

    def assess_regimen(
        self,
        interactions: list[dict],
        patient: dict,
        resolved_medications: list[dict],
        multi_drug_analysis: dict,
    ) -> dict:
        patient_factors = self._patient_factors(patient, resolved_medications)
        scored_interactions = []
        base_score = 0.0
        flags = []

        for interaction in interactions:
            pair_adjustment, pair_reasons = self._pair_adjustment(interaction, patient_factors)
            pair_total = min(100.0, interaction["score"] + pair_adjustment)
            base_score = max(base_score, interaction["score"])

            scored_interactions.append(
                {
                    **interaction,
                    "base_score": interaction["score"],
                    "patient_adjustment": round(pair_adjustment, 1),
                    "final_score": round(pair_total, 1),
                    "label": self._label(pair_total),
                    "reasoning": pair_reasons,
                }
            )

            if pair_reasons:
                flags.append(
                    {
                        "pair": [interaction["source"], interaction["target"]],
                        "delta": round(pair_adjustment, 1),
                        "reasons": pair_reasons,
                    }
                )

        patient_weight = patient_factors["weight"]
        amplification = multi_drug_analysis.get("amplification", {}).get("score", 0.0)
        final_score = min(100.0, base_score + patient_weight + amplification)

        return {
            "risk_score": round(final_score, 1),
            "risk_label": self._label(final_score),
            "severity": self._severity(final_score),
            "components": {
                "base_interaction_severity": round(base_score, 1),
                "patient_condition_weight": round(patient_weight, 1),
                "multi_drug_amplification": round(amplification, 1),
            },
            "interactions": sorted(scored_interactions, key=lambda item: item["final_score"], reverse=True),
            "bayesian_flags": flags,
            "patient_factors": patient_factors["reasons"],
        }

    def _patient_factors(self, patient: dict, resolved_medications: list[dict]) -> dict:
        reasons: list[str] = []
        weight = 0.0
        age = patient.get("age") or 0
        conditions = [item.lower() for item in patient.get("conditions", [])]
        allergies = [item.lower() for item in patient.get("allergies", [])]
        current_medications = patient.get("current_medications", [])

        if age >= 75:
            weight += 15
            reasons.append("Advanced age increases sensitivity to adverse effects.")
        elif age >= 65:
            weight += 10
            reasons.append("Older age increases monitoring requirements.")

        for condition in conditions:
            for keyword, condition_weight in self.CONDITION_WEIGHTS.items():
                if keyword in condition:
                    weight += condition_weight
                    reasons.append(f"Condition risk escalator: {condition}.")
                    break

        if len(current_medications) >= 5:
            weight += 8
            reasons.append("Polypharmacy adds background regimen complexity.")

        for medication in resolved_medications:
            contraindications = [item.lower() for item in medication.get("contraindications", [])]
            for contraindication in contraindications:
                if any(condition in contraindication or contraindication in condition for condition in conditions):
                    weight += 12
                    reasons.append(
                        f"{medication['name']} has a contraindication overlap with the patient's conditions."
                    )
                    break

            med_tokens = {
                medication["name"].lower(),
                medication["generic_name"].lower(),
                medication.get("drug_class", "").lower(),
            }
            if any(allergy for allergy in allergies if any(allergy in token or token in allergy for token in med_tokens)):
                weight += 15
                reasons.append(f"Allergy history overlaps with {medication['name']}.")

        return {"weight": min(30.0, round(weight, 1)), "reasons": reasons}

    def _pair_adjustment(self, interaction: dict, patient_factors: dict) -> tuple[float, list[str]]:
        reasons = []
        adjustment = 0.0
        text = " ".join(
            [
                interaction.get("type", ""),
                interaction.get("description", ""),
                " ".join(patient_factors["reasons"]),
            ]
        ).lower()

        if "bleed" in text:
            adjustment += 8
            reasons.append("Bleeding-related factors amplify this interaction.")
        if "renal" in text or "kidney" in text:
            adjustment += 6
            reasons.append("Kidney-related factors increase the clinical concern.")
        if "liver" in text or "hepatic" in text or "metabolism" in text:
            adjustment += 6
            reasons.append("Metabolic or hepatic burden raises uncertainty.")
        if patient_factors["reasons"]:
            adjustment += min(10.0, len(patient_factors["reasons"]) * 2.0)
            reasons.append("Patient-specific vulnerabilities increase pairwise risk.")

        return min(25.0, round(adjustment, 1)), reasons

    def _label(self, score: float) -> str:
        if score >= 70:
            return "dangerous"
        if score >= 35:
            return "moderate"
        return "safe"

    def _severity(self, score: float) -> str:
        if score >= 70:
            return "high"
        if score >= 35:
            return "moderate"
        return "low"

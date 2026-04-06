import { useEffect, useState } from "react";

import { InteractionGraph } from "../components/InteractionGraph";
import { MedicationForm } from "../components/MedicationForm";
import { RiskSummary } from "../components/RiskSummary";
import { api, applyDemoToken } from "../lib/api";
import { InteractionResponse } from "../types";

export function InteractionWorkbench() {
  const [result, setResult] = useState<InteractionResponse | null>(null);
  const [status, setStatus] = useState("Bootstrapping demo session...");

  useEffect(() => {
    async function bootstrap() {
      const registration = await api.post("/auth/register", {
        name: "Demo Pharmacist",
        email: `demo-${Date.now()}@pharmapath.local`,
        password: "demo1234",
        role: "pharmacist"
      });
      applyDemoToken(registration.data.jwt_token);
      setStatus("Ready for interaction analysis.");
    }

    bootstrap().catch(() => {
      setStatus("Backend connection failed. Start the Flask API to enable checks.");
    });
  }, []);

  async function handleSubmit(payload: {
    medications: string[];
    patient: {
      age?: number;
      weight_kg?: number;
      liver_function?: string;
      renal_function?: string;
      conditions: string[];
    };
  }) {
    setStatus("Running graph scan and Bayesian adjustment...");
    const response = await api.post<InteractionResponse>("/interactions/check", payload);
    setResult(response.data);
    setStatus("Analysis complete.");
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">Medication Interaction Navigator</p>
        <h1>PharmaPath</h1>
        <p className="hero-copy">
          A four-layer architecture for clinical interaction screening with graph reasoning, A* alternatives,
          and patient-aware Bayesian scoring.
        </p>
        <p className="status-banner">{status}</p>
      </section>

      <section className="workspace-grid">
        <MedicationForm onSubmit={handleSubmit} />
        <RiskSummary result={result} />
      </section>

      <InteractionGraph result={result} />
    </main>
  );
}


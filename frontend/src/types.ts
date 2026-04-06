export type RiskPair = {
  source: string;
  target: string;
  source_name: string;
  target_name: string;
  score: number;
  adjusted_score?: number;
  severity: string;
  type: string;
  description: string;
  bayesian_reasoning?: string[];
};

export type InteractionResponse = {
  session_id: string;
  overall_risk: "LOW" | "MODERATE" | "HIGH";
  submitted_medications: string[];
  resolved_medications: Array<{
    input: string;
    drug_id: string;
    name: string;
    generic_name: string;
  }>;
  unmatched_medications: string[];
  risk_pairs: RiskPair[];
  bayesian_flags: Array<{
    pair: [string, string];
    delta: number;
    reasons: string[];
  }>;
  safe_alternatives: Array<{
    medications: string[];
    medication_names: string[];
    total_risk_score: number;
    path_explanation: string;
  }>;
  astar_summary: {
    triggered: boolean;
    summary: string;
    result: null | {
      current_medications: string[];
      suggested_medications: string[];
      estimated_risk_score: number;
      explanation: string;
    };
  };
  user_summary: {
    title: string;
    action: string;
    why: string;
  };
  graph_path: {
    nodes: Array<{ id: string; label: string; risk: string }>;
    edges: Array<{ source: string; target: string; weight: number; type: string; severity: string }>;
  };
  comparison_graph: {
    nodes: Array<{ id: string; drug_id: string; label: string; group: string }>;
    edges: Array<{
      source: string;
      target: string;
      kind: string;
      severity: string;
      weight: number;
      label: string;
    }>;
  };
};

import { InteractionResponse } from "../types";

type Props = {
  result: InteractionResponse | null;
};

export function RiskSummary({ result }: Props) {
  if (!result) {
    return (
      <section className="panel">
        <div className="panel-header">
          <p className="eyebrow">Results</p>
          <h2>Waiting for your medicines</h2>
        </div>
        <p>Press Check Interactions and the app will tell you what to do next and why.</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <p className="eyebrow">Final Result</p>
        <h2>{result.user_summary.title}</h2>
      </div>

      <div className="panel-subsection">
        <h3>What you should do now</h3>
        <p>{result.user_summary.action}</p>
        <h3>Why</h3>
        <p>{result.user_summary.why}</p>
        <p>Overall risk: {result.overall_risk}</p>
        {result.unmatched_medications.length > 0 ? <p>Not recognized: {result.unmatched_medications.join(", ")}</p> : null}
      </div>

      <div className="panel-subsection">
        <h3>What A* search did</h3>
        <p>{result.astar_summary.summary}</p>
        {result.astar_summary.result ? (
          <>
            <p>Current medicines: {result.astar_summary.result.current_medications.join(", ")}</p>
            <p>Suggested lower-risk option: {result.astar_summary.result.suggested_medications.join(", ")}</p>
            <p>Estimated risk score of suggestion: {result.astar_summary.result.estimated_risk_score}</p>
            <p>{result.astar_summary.result.explanation}</p>
          </>
        ) : null}
      </div>

      <div className="panel-subsection">
        <h3>Medicines recognized by the system</h3>
        {result.resolved_medications.map((item) => (
          <article key={item.drug_id} className="pill-card">
            <strong>{item.input}</strong>
            <span>
              matched to {item.name} ({item.drug_id})
            </span>
          </article>
        ))}
      </div>

      <div className="risk-pills">
        {result.risk_pairs.map((pair) => (
          <article key={`${pair.source}-${pair.target}`} className="pill-card">
            <strong>
              {pair.source_name} + {pair.target_name}
            </strong>
            <span>{pair.type}</span>
            <span>Risk score: {pair.adjusted_score ?? pair.score}</span>
            <p>{pair.description}</p>
          </article>
        ))}
      </div>

      <div className="panel-subsection">
        <h3>Personal factors that changed the result</h3>
        {result.bayesian_flags.length === 0 ? (
          <p>No patient-specific escalations were applied.</p>
        ) : (
          result.bayesian_flags.map((flag, index) => <p key={index}>Your personal risk was increased by {flag.delta} because of {flag.reasons.join(", ")}.</p>)
        )}
      </div>

      <div className="panel-subsection">
        <h3>Possible lower-risk options to ask about</h3>
        {result.safe_alternatives.length === 0 ? (
          <p>No severe pair triggered an alternative search.</p>
        ) : (
          result.safe_alternatives.map((option, index) => (
            <article key={index} className="alternative-card">
              <strong>{option.medication_names.join(", ")}</strong>
              <span>Risk score: {option.total_risk_score}</span>
              <p>{option.path_explanation}</p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}

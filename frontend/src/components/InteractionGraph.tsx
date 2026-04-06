import { InteractionResponse } from "../types";

type Props = {
  result: InteractionResponse | null;
};

export function InteractionGraph({ result }: Props) {
  if (!result) {
    return (
      <section className="panel graph-panel">
        <div className="panel-header">
          <p className="eyebrow">Graph View</p>
          <h2>Medicine Relationship Map</h2>
        </div>
        <p>The API will compare the medicines entered by the user with the lower-risk set suggested by A* search.</p>
      </section>
    );
  }

  const currentNodes = result.comparison_graph.nodes.filter((node) => node.group === "current");
  const suggestedNodes = result.comparison_graph.nodes.filter((node) => node.group === "suggested");

  return (
    <section className="panel graph-panel">
      <div className="panel-header">
        <p className="eyebrow">Graph View</p>
        <h2>Medicine Relationship Map</h2>
      </div>
      <p>This compares the medicines given now with the alternative set suggested by A* search.</p>
      <div className="graph-grid">
        {currentNodes.map((node) => (
          <div key={node.id} className="node-card">
            <strong>{node.label}</strong>
            <span>Current medicine</span>
          </div>
        ))}
        {suggestedNodes.map((node) => (
          <div key={node.id} className="edge-card">
            <strong>{node.label}</strong>
            <span>Suggested medicine</span>
          </div>
        ))}
        {result.comparison_graph.edges.map((edge, index) => (
          <div key={index} className="pill-card">
            <strong>
              {edge.source} -&gt; {edge.target}
            </strong>
            <span>{edge.label}</span>
            <span>{edge.kind}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

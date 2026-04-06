# Request Lifecycle

## `POST /api/interactions/check`

1. Browser sends medications plus patient profile.
2. `interaction_bp.check_interactions` validates the request body.
3. `InteractionService.check_interactions` resolves drugs and loads the interaction graph.
4. Pairwise severity scores are computed from graph edges.
5. If a high-risk combination appears, the A* search service proposes lower-risk substitutes.
6. Bayesian adjustments raise or lower pair scores based on age, organ function, weight, and conditions.
7. Session and interaction result rows are saved to SQLite.
8. The API responds with `risk_pairs`, `overall_risk`, `bayesian_flags`, `safe_alternatives`, and `graph_path`.


# PharmaPath Architecture Mapping

## Four-layer design

### 1. Client

- React app under `frontend/src`
- `pages/InteractionWorkbench.tsx` is the main workflow screen
- `components/MedicationForm.tsx` collects medications and patient priors
- `components/RiskSummary.tsx` renders the result payload
- `components/InteractionGraph.tsx` accepts D3-compatible graph data

### 2. API

- Flask app factory in `backend/pharmapath/app.py`
- Route blueprints in `backend/pharmapath/routes`
- Request orchestration lives in `backend/pharmapath/services`
- Token helpers and auth guards live in `backend/pharmapath/core`

### 3. AI Engine

- Graph loading and subgraph extraction: `backend/pharmapath/ai/graph_engine.py`
- A* regimen search: `backend/pharmapath/ai/search.py`
- Bayesian-style risk adjustment: `backend/pharmapath/ai/bayes.py`
- End-to-end interaction evaluation: `backend/pharmapath/services/interaction_service.py`

### 4. Data

- SQLite schema bootstrap: `backend/pharmapath/db/schema.py`
- Repository layer: `backend/pharmapath/repositories`
- External drug lookup abstraction: `backend/pharmapath/integrations/drugbank.py`
- Cached graph and sample drugs: `backend/data/cache` and `backend/data/seed`

## Request lifecycle implemented

1. Frontend submits medications and patient profile to `POST /api/interactions/check`
2. Flask validates payload and delegates to the interaction service
3. Drug lookup resolves requested drugs from seed data or repository cache
4. Graph service loads the weighted drug graph
5. Pairwise scan detects risky edges
6. A* search suggests alternatives for severe combinations
7. Bayesian scoring adjusts risk using patient priors
8. Results persist to SQLite session tables
9. Frontend renders summary cards and graph data

## Current implementation notes

- JWT and refresh-token flows are scaffolded, with lightweight local token handling for development
- Redis rate limiting is documented but not wired yet
- DrugBank is represented by a local adapter and sample fixture file
- Report generation currently supports JSON payloads; PDF is left as an extension point


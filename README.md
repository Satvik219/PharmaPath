# PharmaPath

PharmaPath is a scaffolded medication interaction navigator built from the provided architecture document. The repository follows the four-layer design from the PDF:

- `frontend/`: React client for medication entry, reports, and graph rendering
- `backend/`: Flask API, AI engine orchestration, auth, data access, and reporting
- `backend/data/`: SQLite database, graph cache, and sample drug fixtures
- `docs/`: architecture notes, request lifecycle, and API mapping

## Architecture used

1. Client layer: React + Axios + D3-ready graph view
2. API layer: Flask + JWT-ready auth modules + route blueprints
3. AI engine layer: NetworkX graph service, A* alternative search, Bayesian risk adjustment
4. Data layer: SQLite repositories, DrugBank client abstraction, graph cache

## Quick start

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pharmapath.app
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

### VS Code Go Live

If you want to use VS Code Live Server, open [frontend/live/index.html](c:/Users/satvi/OneDrive%20-%20Manipal%20Academy%20of%20Higher%20Education/Desktop/PharmaPath/frontend/live/index.html) with Go Live. That page is plain HTML/JS and calls the Flask backend at `http://localhost:5000/api`.

You still need to run the backend separately:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pharmapath.app
```

## Project status

This is a starter implementation: the architecture, routes, models, and data flow are in place, with local sample data and placeholder integrations where live DrugBank, Redis, PDF generation, and production auth hardening would be connected next.

# AEGIS Coral

AEGIS Coral is a satellite situational-awareness app with:

- `backend/`: FastAPI service for TLE ingestion, SGP4 propagation, conjunction detection, proximity pairs, and optional OpenRouter AI analysis.
- `frontend/`: Next.js 16 app with a full-screen 3D globe powered by `react-globe.gl`.
- `coral/`: repo-local Coral workspace for the operational intelligence pivot.

## Prerequisites

- Python 3.12
- Node.js 20+
- npm

## Backend

```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

The API runs at `http://127.0.0.1:8000`.

`OPENROUTER_API_KEY` is optional for the core app. Without it, the AI endpoint returns a fallback analysis while satellite tracking and conjunction detection still work.

Useful endpoints:

- `GET /status`
- `POST /fetch`
- `POST /detect`
- `GET /positions/all`
- `GET /conjunctions`
- `GET /proximity`
- `GET /intelligence/queries`
- `GET /intelligence/queries/{query_id}`
- `GET /intelligence/benchmark`
- `POST /intelligence/ask`
- `POST /intelligence/investigations`
- `GET /intelligence/investigations/{investigation_id}`
- `GET /intelligence/alerts`

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:3000` and expects the backend at `http://127.0.0.1:8000`.
Override the backend URL with `NEXT_PUBLIC_API_BASE_URL` if needed.

## Coral

Install Coral on macOS:

```bash
brew install withcoral/tap/coral
coral --version
coral source discover
coral sql --format json "SELECT schema_name, table_name FROM coral.tables ORDER BY 1, 2 LIMIT 10"
```

Coral MCP can be started with:

```bash
coral mcp-stdio
```

Optional Codex MCP client configuration:

```toml
[mcp_servers.coral]
command = "coral"
args = ["mcp-stdio"]
```

See `coral/README.md` for Phase 1 validation, future environment variables, and rollback notes.

## Operational Intelligence Queries

The backend exposes predefined Coral-backed investigations:

```bash
curl http://127.0.0.1:8000/intelligence/queries
curl http://127.0.0.1:8000/intelligence/queries/risk_weather_context
curl http://127.0.0.1:8000/intelligence/benchmark
curl -X POST http://127.0.0.1:8000/intelligence/ask \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Summarize operational threats for the next 48 hours across conjunctions, weather, and launches."}'
curl -X POST http://127.0.0.1:8000/intelligence/investigations \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Why are conjunction risks elevated today?"}'
curl http://127.0.0.1:8000/intelligence/alerts
```

Current query IDs:

- `risk_weather_context`
- `closest_spacetrack_enrichment`
- `starlink_launch_context`
- `launch_weather_window`

The frontend includes an Intel console that calls the same Coral-backed
planner on demand. The console now runs multi-step investigations with a
polling timeline, approved query trace, passive alerts, recommendations, and a
small source-to-query relationship map.

## Demo Guide

See `docs/demo.md` for the hackathon demo script, architecture diagram,
sample prompts, benchmark snapshot, and sponsor-feature showcase.

## Verification

```bash
cd backend
source venv/bin/activate
python -m compileall -q .
python - <<'PY'
from fastapi.testclient import TestClient
from main import app
client = TestClient(app)
print(client.get("/").json())
PY
```

```bash
cd frontend
npm run lint
npm run build
```

# HELIX Coral Workspace

This folder contains HELIX project assets for Coral. It is intentionally
repo-local and should not contain API keys, tokens, account passwords, or MCP
client secrets.

## Current Phase

Phase 1 established Coral as the foundation for the HELIX operational
intelligence pivot. Phase 2 exposes the existing SQLite conjunction and
satellite data as a Coral-queryable source named `helix_core`. Phase 3 adds
NOAA SWPC, Launch Library 2, and Space-Track snapshots. Phases 4-6 add a
FastAPI query layer, a structured natural-language planner, and a frontend
intelligence console.

## Installed Coral Version

Verified locally:

```bash
coral 0.4.1+43d8309
```

## Local Setup

Install Coral on macOS with Homebrew:

```bash
brew install withcoral/tap/coral
coral --version
```

Verify the source catalog and SQL interface:

```bash
coral source discover
coral source list
coral sql --format json "SELECT schema_name, table_name FROM coral.tables ORDER BY 1, 2 LIMIT 10"
```

Expected base state:

- `coral source discover` lists available built-in sources.
- `coral source list` includes `helix_core` after Phase 2.
- The catalog SQL query succeeds.

## HELIX Core Source

The current Coral build does not expose local SQLite directly, so HELIX uses a
file-backed Coral source generated from `backend/helix.db`.

Regenerate the source snapshot and manifest:

```bash
python3 tools/export_coral_helix_core.py
coral source lint coral/sources/helix_core.yaml
coral source add --file coral/sources/helix_core.yaml
```

The source exposes:

- `helix_core.satellites`
- `helix_core.conjunctions`

Sample operational SQL:

```sql
SELECT risk,
       COUNT(*) AS events,
       ROUND(MIN(miss_distance_km), 3) AS closest_km
  FROM helix_core.conjunctions
 GROUP BY risk
 ORDER BY events DESC;
```

```sql
SELECT c.risk,
       c.miss_distance_km,
       c.relative_velocity_km_s,
       s1.name AS sat1_name,
       s2.name AS sat2_name
  FROM helix_core.conjunctions c
  JOIN helix_core.satellites s1 ON c.sat1_norad_id = s1.norad_id
  JOIN helix_core.satellites s2 ON c.sat2_norad_id = s2.norad_id
 ORDER BY c.miss_distance_km ASC
 LIMIT 5;
```

## MCP Verification

Start the Coral MCP server over stdio:

```bash
coral mcp-stdio
```

The process is expected to remain running while an MCP client is connected.

Optional Codex MCP client configuration:

```toml
[mcp_servers.coral]
command = "coral"
args = ["mcp-stdio"]
```

Do not edit global MCP client config automatically. Add this only when a user
explicitly wants Codex to connect to Coral as an MCP server.

## Environment Variables

Phase 1 does not require new environment variables.

Known variables:

- `GEMINI_API_KEY`: optional AI synthesis for the Coral intelligence planner.
- `HELIX_GEMINI_MODEL`: optional Gemini model override. Defaults to
  `gemini-2.5-flash`.
- `OPENROUTER_API_KEY`: optional legacy conjunction analysis and optional
  fallback synthesis when `HELIX_OPENROUTER_MODEL` is also set.
- `HELIX_OPENROUTER_MODEL`: OpenRouter model ID for fallback synthesis.
- `SPACE_TRACK_USERNAME`: Space-Track source account username.
- `SPACE_TRACK_PASSWORD`: Space-Track source account password.
- `NEXT_PUBLIC_API_BASE_URL`: optional frontend backend URL override.

Keep secrets in `.env`, shell environment, or Coral's local credential flow. Do
not commit secrets.

## NOAA Space Weather Source

Phase 3 adds NOAA SWPC public JSON products as a Coral source named
`noaa_space_weather`. No API key is required.

Regenerate and register:

```bash
python3 tools/fetch_noaa_space_weather.py
coral source lint coral/sources/noaa_space_weather.yaml
coral source add --file coral/sources/noaa_space_weather.yaml
```

The source exposes:

- `noaa_space_weather.kp_observed`
- `noaa_space_weather.kp_forecast`
- `noaa_space_weather.noaa_scales`
- `noaa_space_weather.alerts`

NOAA responses currently send `Cache-Control: max-age=60`, so refresh no more
than once per minute for live demos unless a specific product requires it.

## Launch Library Source

Phase 3 also adds upcoming launch activity from The Space Devs Launch Library 2
as a Coral source named `launch_library`. No API key is required for the current
snapshot path, but unauthenticated API usage is rate-limited; keep refreshes
manual and low-frequency.

Regenerate and register:

```bash
python3 tools/fetch_launch_library.py --limit 50
coral source lint coral/sources/launch_library.yaml
coral source add --file coral/sources/launch_library.yaml
```

The source exposes:

- `launch_library.upcoming_launches`

## Space-Track Source

Phase 3 adds bounded Space-Track snapshots as a Coral source named
`space_track`. This source requires credentials in `backend/.env` or the shell:

```bash
SPACE_TRACK_USERNAME=...
SPACE_TRACK_PASSWORD=...
```

Regenerate and register:

```bash
python3 tools/fetch_spacetrack.py --limit 1000
coral source lint coral/sources/space_track.yaml
coral source add --file coral/sources/space_track.yaml
```

The source exposes:

- `space_track.gp_current`
- `space_track.satcat_recent`

The fetch is deliberately bounded to avoid excessive Space-Track API usage.
Increase `--limit` only for a specific demo or benchmark need.

## Backend Query API

HELIX exposes reusable Coral-backed intelligence queries through FastAPI:

```bash
curl http://127.0.0.1:8000/intelligence/queries
curl http://127.0.0.1:8000/intelligence/queries/risk_weather_context
curl http://127.0.0.1:8000/intelligence/benchmark
curl -X POST http://127.0.0.1:8000/intelligence/ask \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Summarize operational threats for the next 48 hours across conjunctions, weather, and launches."}'
```

The current query layer lives in `backend/coral_queries.py` and executes
through the local `coral sql --format json` CLI wrapper in
`backend/coral_service.py`.

The structured prompt planner lives in `backend/intelligence_agent.py`. It
maps natural-language prompts to approved query IDs and never executes
arbitrary model-generated SQL.

## Folder Layout

```text
coral/
  README.md
  queries/
  sources/
```

- `sources/`: future Coral source manifests or source-specific notes.
- `queries/`: reusable operational SQL queries and demo queries.

## Validation Commands

Run after Coral setup changes:

```bash
coral --version
coral source discover
python3 tools/export_coral_helix_core.py
coral source lint coral/sources/helix_core.yaml
coral source add --file coral/sources/helix_core.yaml
python3 tools/fetch_noaa_space_weather.py
coral source lint coral/sources/noaa_space_weather.yaml
coral source add --file coral/sources/noaa_space_weather.yaml
python3 tools/fetch_launch_library.py --limit 50
coral source lint coral/sources/launch_library.yaml
coral source add --file coral/sources/launch_library.yaml
python3 tools/fetch_spacetrack.py --limit 1000
coral source lint coral/sources/space_track.yaml
coral source add --file coral/sources/space_track.yaml
coral sql --format json "SELECT schema_name, table_name FROM coral.tables ORDER BY 1, 2 LIMIT 10"
cd backend && ./venv/bin/python -m compileall -q .
cd frontend && npm run lint
cd frontend && npm run build
```

## Rollback

Remove this repo-local workspace:

```bash
rm -rf coral
```

Remove the configured source:

```bash
coral source remove helix_core
coral source remove noaa_space_weather
coral source remove launch_library
coral source remove space_track
```

Uninstall Coral if needed:

```bash
brew uninstall coral
```

Remove any manually added MCP client config entries.

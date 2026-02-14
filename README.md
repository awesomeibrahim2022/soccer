# Soccer Match Result Predictor (Automated)

This project now runs as an **automated ingestion + retraining system** for:

- Turkish Super Lig
- Premier League
- La Liga
- Primeira Liga
- Bundesliga
- Serie A
- Scottish Premiership
- UEFA Champions League

No manual CSV upload is required.

## What is now automated

- Pull latest finished matches from online APIs (t or t-1 window).
- Refresh local history cache.
- Retrain model after ingestion.
- Track ingestion timestamp and freshness metadata.
- Expose freshness via API and dashboard.

## Features used by the model (automated)

- Form trend / momentum (rolling points + xG + goals).
- H2H and bogey dynamics (pair residual from prior meetings).
- Home advantage.
- Injury impact (when API-Football key is provided).
- Fan confidence proxy (computed from recent points-per-game trend).
- Rest-day and motivation deltas.

## Providers

### 1) football-data.org (`source=football_data`)
- Good match coverage for EPL, La Liga, Bundesliga, Serie A, Primeira Liga, Scottish Premiership, UCL.
- Requires: `FOOTBALL_DATA_API_TOKEN`.

### 2) TheSportsDB (`source=sportsdb`)
- Includes Turkish Super Lig and broad competition coverage.
- No key required in this implementation.

### Optional injury enrichment
- Set `API_FOOTBALL_KEY` (+ optional `API_FOOTBALL_HOST`) to auto-pull injury feeds and populate injury impact columns.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```


## Zero-manual auto ingestion on service start

When `SOCCER_DATA_SOURCE=online_api` (default), the API now attempts automatic ingestion on startup when cache is missing/stale.

Environment controls:

- `SOCCER_AUTO_INGEST=true|false` (default: `true`)
- `SOCCER_MAX_INGEST_AGE_HOURS` (default: `30`)
- `SOCCER_INGEST_SOURCE=football_data|sportsdb` (default: `sportsdb`)
- `SOCCER_INGEST_SEASON` (default: current year)
- `SOCCER_INGEST_WINDOW_DAYS` (default: `1`, for t-1/t window)

If online ingest fails but an existing cache exists, startup falls back to cache and reports a warning in `/health` under `auto_ingest`.

## Trigger online ingestion + retrain (HTTP)

```bash
curl -X POST http://127.0.0.1:8000/ingest/online \
  -H "Content-Type: application/json" \
  -d '{"source":"sportsdb","season":"2024-2025","window_days":1}'
```

## Trigger ingestion (CLI)

```bash
python -m backend.scripts.ingest_online_data --source sportsdb --season 2024-2025 --window-days 1
```

## Full automation scheduling (recommended)

Run daily at 03:00 UTC (t-1 / t refresh):

```bash
0 3 * * * cd /workspace/soccer && /usr/bin/python3 -m backend.scripts.auto_refresh --source sportsdb --season 2024-2025 --window-days 1 >> /workspace/soccer/data/cron.log 2>&1
```


## Web portal auto-deploy (Render)

This repo now includes a Render Blueprint file: `render.yaml`.

### One-time setup
1. Push this repository to GitHub.
2. In Render: **New +** -> **Blueprint** -> select the repo.
3. Render will create:
   - `soccer-predictor-api` (web service)
   - `soccer-predictor-refresh` (daily cron refresh at 03:00 UTC)
4. Add secret env vars in Render dashboard:
   - `FOOTBALL_DATA_API_TOKEN` (optional unless using football-data source)
   - `API_FOOTBALL_KEY` (optional injury enrichment)

### What is automated by the portal
- Build + deploy on each git push (`autoDeploy: true`).
- API startup with auto-ingest checks.
- Daily scheduled ingestion/retraining run.

For local parity, copy `.env.example` to `.env` and set values.

## API

- `GET /health`
- `GET /meta/leagues`
- `GET /meta/data-source`
- `POST /predict`
- `POST /learn`
- `POST /ingest/online`
- `GET /model/metrics`

`/health`, `/meta/data-source`, and `/model/metrics` include ingestion freshness info.

## Notes

- “Fan confidence” is modeled as an automated proxy from recent on-pitch results (no manual sentiment uploads).
- Injury impact is automatically enriched when injury provider credentials are configured.
- In this execution environment, direct outbound API validation may be blocked by proxy policy.

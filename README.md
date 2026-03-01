# Soccer Match Result Predictor

Starter implementation of a continual-learning ML system for predicting match outcomes (Home/Draw/Away) for:

- Turkish Super Lig
- Premier League
- La Liga
- Primeira Liga
- Bundesliga
- Serie A
- Scottish Premiership
- UEFA Champions League

## Architecture

- **Backend:** FastAPI service + scikit-learn pipeline with feature engineering for form, H2H/bogey indicators, home advantage, injuries, motivation and rest.
- **Continual learning:** `/learn` endpoint appends completed matches and retrains the model.
- **Frontend:** React dashboard (CDN build) showing predictions, filter by league, and model-health cards.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/scripts/generate_sample_data.py
uvicorn backend.app.main:app --reload
```

In another shell:

```bash
python -m http.server 4173 -d frontend
```

Open `http://127.0.0.1:4173`.


## Current status (important)

This repository is a **starter implementation** and currently uses a **synthetic local CSV** as the data source by default.
It is useful for validating pipeline wiring and UI flow, but it is **not yet production-grade forecasting** until connected to real provider feeds and validated with full backtesting.

### Data source configuration

- Default mode: `SOCCER_DATA_SOURCE=synthetic_csv`
- Default file: `SOCCER_HISTORICAL_CSV=data/historical_matches.csv`
- Generate synthetic data: `python backend/scripts/generate_sample_data.py`
- API introspection endpoint: `GET /meta/data-source`

To switch to real historical data, provide your own CSV in the same schema and set:

```bash
export SOCCER_DATA_SOURCE=custom_csv
export SOCCER_HISTORICAL_CSV=/path/to/your/historical_matches.csv
```

## API

- `GET /health`
- `GET /meta/leagues`
- `GET /meta/data-source`
- `POST /predict`
- `POST /learn`
- `GET /model/metrics`

### Example prediction payload

```json
[
  {
    "league": "Premier League",
    "home_team": "Arsenal",
    "away_team": "Liverpool",
    "home_injury_impact": 0.3,
    "away_injury_impact": 0.6,
    "home_motivation": 0.8,
    "away_motivation": 0.9,
    "home_rest_days": 6,
    "away_rest_days": 4
  }
]
```

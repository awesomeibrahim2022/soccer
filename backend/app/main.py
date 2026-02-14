from __future__ import annotations

from datetime import datetime
from typing import List

import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field

from .data_source import auto_refresh_online_data, get_data_source_config
from .leagues import SUPPORTED_LEAGUES
from .model import MatchModelService
from .online_ingest import ingest_online, read_ingestion_status

DATA_SOURCE = get_data_source_config()
AUTO_INGEST_STATUS = auto_refresh_online_data(DATA_SOURCE)


def _load_history() -> pd.DataFrame:
    if not DATA_SOURCE.historical_csv.exists():
        raise FileNotFoundError(
            f"Missing {DATA_SOURCE.historical_csv}. "
            "Run online ingestion first via `/ingest/online` or scheduler job."
        )
    history = pd.read_csv(DATA_SOURCE.historical_csv)
    return history.sort_values("match_date")


history_df = _load_history()
model_service = MatchModelService.load_or_train(history_df)
app = FastAPI(title="Soccer Predictor API", version="0.3.0")


class OnlineIngestPayload(BaseModel):
    source: str = Field(pattern="^(football_data|sportsdb)$")
    season: str = str(datetime.utcnow().year)
    window_days: int = Field(default=1, ge=0, le=7)


class FixturePayload(BaseModel):
    league: str
    home_team: str
    away_team: str
    home_injury_impact: float = 0.0
    away_injury_impact: float = 0.0
    home_motivation: float = 0.0
    away_motivation: float = 0.0
    home_rest_days: float = 3.0
    away_rest_days: float = 3.0


class ResultPayload(FixturePayload):
    home_goals: int
    away_goals: int
    home_xg: float = Field(ge=0)
    away_xg: float = Field(ge=0)
    result: str = Field(pattern="^[HDA]$")
    match_date: str


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "records": int(len(model_service.history)),
        "data_source_mode": DATA_SOURCE.mode,
        "ingestion": read_ingestion_status(),
        "auto_ingest": AUTO_INGEST_STATUS,
    }


@app.get("/meta/leagues")
def leagues() -> dict:
    return {"leagues": SUPPORTED_LEAGUES}


@app.get("/meta/data-source")
def data_source() -> dict:
    return {
        "mode": DATA_SOURCE.mode,
        "csv_path": str(DATA_SOURCE.historical_csv),
        "description": DATA_SOURCE.description,
        "ingestion": read_ingestion_status(),
        "auto_ingest": AUTO_INGEST_STATUS,
    }


@app.post("/predict")
def predict(fixtures: List[FixturePayload]) -> dict:
    fixture_df = pd.DataFrame([f.model_dump() for f in fixtures])
    preds = model_service.predict(fixture_df)
    return {"predictions": preds.to_dict(orient="records")}


@app.post("/learn")
def learn(new_results: List[ResultPayload]) -> dict:
    results_df = pd.DataFrame([r.model_dump() for r in new_results])
    model_service.update_with_results(results_df)
    model_service.save()
    return {"status": "updated", "records": int(len(model_service.history))}


@app.post("/ingest/online")
def ingest_online_data(payload: OnlineIngestPayload) -> dict:
    result = ingest_online(payload.source, payload.season, payload.window_days)
    fresh_history = _load_history()
    model_service.retrain_from_history(fresh_history)
    model_service.save()
    return {
        "status": "ingested",
        "source": result.source,
        "rows": result.rows,
        "leagues_covered": result.leagues_covered,
        "ingested_at": result.ingested_at,
        "freshness_window": result.freshness_window,
    }


@app.get("/model/metrics")
def model_metrics() -> dict:
    sample = model_service.history.tail(180)
    return {
        "sample_size": int(len(sample)),
        "baseline_rates": {
            "home_win": float((sample["result"] == "H").mean()),
            "draw": float((sample["result"] == "D").mean()),
            "away_win": float((sample["result"] == "A").mean()),
        },
        "last_retrain_matches": int(len(model_service.history)),
        "ingestion": read_ingestion_status(),
        "auto_ingest": AUTO_INGEST_STATUS,
    }

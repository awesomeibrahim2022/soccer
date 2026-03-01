from __future__ import annotations

from typing import List

import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field

from .data_source import get_data_source_config
from .leagues import SUPPORTED_LEAGUES
from .model import MatchModelService

DATA_SOURCE = get_data_source_config()


def _load_history() -> pd.DataFrame:
    if not DATA_SOURCE.historical_csv.exists():
        raise FileNotFoundError(
            f"Missing {DATA_SOURCE.historical_csv}. "
            "Generate data with `python backend/scripts/generate_sample_data.py` "
            "or set SOCCER_HISTORICAL_CSV to your dataset path."
        )
    history = pd.read_csv(DATA_SOURCE.historical_csv)
    return history.sort_values("match_date")


history_df = _load_history()
model_service = MatchModelService.load_or_train(history_df)
app = FastAPI(title="Soccer Predictor API", version="0.1.0")


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


@app.get("/model/metrics")
def model_metrics() -> dict:
    sample = model_service.history.tail(180)
    baseline_home_win_rate = float((sample["result"] == "H").mean())
    baseline_draw_rate = float((sample["result"] == "D").mean())
    baseline_away_rate = float((sample["result"] == "A").mean())
    return {
        "sample_size": int(len(sample)),
        "baseline_rates": {
            "home_win": baseline_home_win_rate,
            "draw": baseline_draw_rate,
            "away_win": baseline_away_rate,
        },
        "last_retrain_matches": int(len(model_service.history)),
    }

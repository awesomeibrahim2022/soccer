from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .features import build_feature_frame, label_results

MODEL_PATH = Path("data/model.joblib")


@dataclass
class TrainingArtifacts:
    model: Pipeline
    history: pd.DataFrame


class MatchModelService:
    def __init__(self, history: pd.DataFrame):
        self.history = history.copy()
        self.model = self._train(self.history)

    def _train(self, history: pd.DataFrame) -> Pipeline:
        fixtures = history[[
            "league",
            "home_team",
            "away_team",
            "home_injury_impact",
            "away_injury_impact",
            "home_motivation",
            "away_motivation",
            "home_rest_days",
            "away_rest_days",
        ]]
        features = build_feature_frame(fixtures, history)
        labels = label_results(history["result"].tolist())

        categorical = ["league", "home_team", "away_team"]
        numeric = [c for c in features.columns if c not in categorical]

        preprocessor = ColumnTransformer(
            transformers=[
                ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
                ("num", StandardScaler(), numeric),
            ]
        )
        base = RandomForestClassifier(
            n_estimators=250,
            max_depth=8,
            random_state=42,
            class_weight="balanced_subsample",
        )
        calibrated = CalibratedClassifierCV(base, cv=3, method="sigmoid")
        pipeline = Pipeline(
            steps=[("preprocessor", preprocessor), ("model", calibrated)]
        )
        pipeline.fit(features, labels)
        return pipeline

    def predict(self, fixtures: pd.DataFrame) -> pd.DataFrame:
        x = build_feature_frame(fixtures, self.history)
        probs = self.model.predict_proba(x)
        out = fixtures[["league", "home_team", "away_team"]].copy()
        out["home_win"] = probs[:, 0]
        out["draw"] = probs[:, 1]
        out["away_win"] = probs[:, 2]
        out["confidence"] = probs.max(axis=1)
        return out

    def update_with_results(self, completed_matches: pd.DataFrame) -> None:
        self.history = pd.concat([self.history, completed_matches], ignore_index=True)
        self.model = self._train(self.history)

    def save(self) -> None:
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"history": self.history, "model": self.model}, MODEL_PATH)

    @classmethod
    def load_or_train(cls, history: pd.DataFrame) -> "MatchModelService":
        if MODEL_PATH.exists():
            obj = joblib.load(MODEL_PATH)
            svc = cls.__new__(cls)
            svc.history = obj["history"]
            svc.model = obj["model"]
            return svc
        svc = cls(history)
        svc.save()
        return svc

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

import pandas as pd


@dataclass
class TeamWindowStats:
    points_last5: float
    goal_diff_last5: float
    xg_diff_last5: float


def _points(home_goals: int, away_goals: int, is_home_team: bool) -> int:
    if home_goals == away_goals:
        return 1
    if is_home_team:
        return 3 if home_goals > away_goals else 0
    return 3 if away_goals > home_goals else 0


def _rolling_team_stats(history: pd.DataFrame) -> Dict[str, TeamWindowStats]:
    stats: Dict[str, TeamWindowStats] = {}
    for team in pd.unique(pd.concat([history["home_team"], history["away_team"]])):
        team_rows = history[(history["home_team"] == team) | (history["away_team"] == team)].tail(5)
        if team_rows.empty:
            stats[team] = TeamWindowStats(0.0, 0.0, 0.0)
            continue
        points = []
        goal_diff = []
        xg_diff = []
        for _, row in team_rows.iterrows():
            is_home = row["home_team"] == team
            points.append(_points(row["home_goals"], row["away_goals"], is_home))
            if is_home:
                goal_diff.append(row["home_goals"] - row["away_goals"])
                xg_diff.append(row["home_xg"] - row["away_xg"])
            else:
                goal_diff.append(row["away_goals"] - row["home_goals"])
                xg_diff.append(row["away_xg"] - row["home_xg"])
        stats[team] = TeamWindowStats(
            points_last5=float(sum(points)),
            goal_diff_last5=float(sum(goal_diff)),
            xg_diff_last5=float(sum(xg_diff)),
        )
    return stats


def _h2h_features(history: pd.DataFrame, home_team: str, away_team: str) -> tuple[float, float]:
    h2h = history[
        ((history["home_team"] == home_team) & (history["away_team"] == away_team))
        | ((history["home_team"] == away_team) & (history["away_team"] == home_team))
    ].tail(6)
    if h2h.empty:
        return 0.0, 0.0

    home_points = 0
    home_xg_diff = 0.0
    for _, row in h2h.iterrows():
        if row["home_team"] == home_team:
            home_points += _points(row["home_goals"], row["away_goals"], True)
            home_xg_diff += row["home_xg"] - row["away_xg"]
        else:
            home_points += _points(row["home_goals"], row["away_goals"], False)
            home_xg_diff += row["away_xg"] - row["home_xg"]
    return float(home_points), float(home_xg_diff)


def build_feature_frame(fixtures: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    rows = []
    stats = _rolling_team_stats(history)

    for _, fixture in fixtures.iterrows():
        home_team = fixture["home_team"]
        away_team = fixture["away_team"]
        home = stats.get(home_team, TeamWindowStats(0.0, 0.0, 0.0))
        away = stats.get(away_team, TeamWindowStats(0.0, 0.0, 0.0))
        h2h_points, h2h_xg = _h2h_features(history, home_team, away_team)

        rows.append(
            {
                "league": fixture["league"],
                "home_team": home_team,
                "away_team": away_team,
                "home_advantage": 1.0,
                "form_points_delta": home.points_last5 - away.points_last5,
                "goal_diff_delta": home.goal_diff_last5 - away.goal_diff_last5,
                "xg_diff_delta": home.xg_diff_last5 - away.xg_diff_last5,
                "h2h_points_home": h2h_points,
                "h2h_xg_home": h2h_xg,
                "home_injury_impact": float(fixture.get("home_injury_impact", 0.0)),
                "away_injury_impact": float(fixture.get("away_injury_impact", 0.0)),
                "motivation_delta": float(fixture.get("home_motivation", 0.0))
                - float(fixture.get("away_motivation", 0.0)),
                "rest_days_delta": float(fixture.get("home_rest_days", 3.0))
                - float(fixture.get("away_rest_days", 3.0)),
            }
        )
    return pd.DataFrame(rows)


def label_results(results: Iterable[str]) -> pd.Series:
    mapping = {"H": 0, "D": 1, "A": 2}
    return pd.Series([mapping[r] for r in results])


def decode_label(label: int) -> str:
    inverse = {0: "Home Win", 1: "Draw", 2: "Away Win"}
    return inverse[label]

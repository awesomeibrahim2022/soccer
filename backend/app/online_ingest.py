from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from .leagues import SUPPORTED_LEAGUES

HISTORY_PATH = Path("data/historical_matches.csv")
STATUS_PATH = Path("data/ingestion_status.json")

FOOTBALL_DATA_COMPETITIONS = {
    "Premier League": "PL",
    "La Liga": "PD",
    "Bundesliga": "BL1",
    "Serie A": "SA",
    "Primeira Liga": "PPL",
    "Scottish Premiership": "PDED",
    "UEFA Champions League": "CL",
}

SPORTS_DB_LEAGUE_IDS = {
    "Turkish Super Lig": "4339",
    "Premier League": "4328",
    "La Liga": "4335",
    "Primeira Liga": "4344",
    "Bundesliga": "4331",
    "Serie A": "4332",
    "Scottish Premiership": "4330",
    "UEFA Champions League": "4480",
}

API_FOOTBALL_LEAGUE_IDS = {
    "Turkish Super Lig": 203,
    "Premier League": 39,
    "La Liga": 140,
    "Primeira Liga": 94,
    "Bundesliga": 78,
    "Serie A": 135,
    "Scottish Premiership": 179,
    "UEFA Champions League": 2,
}


@dataclass
class IngestResult:
    source: str
    rows: int
    leagues_covered: list[str]
    ingested_at: str
    freshness_window: str


def _http_json(url: str, headers: dict[str, str] | None = None) -> dict:
    req = Request(url, headers=headers or {})
    with urlopen(req, timeout=40) as response:
        return json.loads(response.read().decode("utf-8"))


def _build_row(
    league: str,
    match_date: str,
    home_team: str,
    away_team: str,
    home_goals: int,
    away_goals: int,
) -> dict:
    result = "H" if home_goals > away_goals else "A" if away_goals > home_goals else "D"
    return {
        "match_date": match_date,
        "league": league,
        "home_team": home_team,
        "away_team": away_team,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "home_xg": round(max(0.1, home_goals + 0.25), 2),
        "away_xg": round(max(0.1, away_goals + 0.2), 2),
        "home_injury_impact": 0.0,
        "away_injury_impact": 0.0,
        "home_motivation": 0.5,
        "away_motivation": 0.5,
        "home_rest_days": 4,
        "away_rest_days": 4,
        "result": result,
    }


def _fetch_api_football_injury_counts(season_year: int) -> dict[tuple[str, str], float]:
    api_key = os.getenv("API_FOOTBALL_KEY", "").strip()
    if not api_key:
        return {}

    host = os.getenv("API_FOOTBALL_HOST", "v3.football.api-sports.io")
    base = f"https://{host}"
    headers = {"x-apisports-key": api_key}
    out: dict[tuple[str, str], float] = {}

    for league, league_id in API_FOOTBALL_LEAGUE_IDS.items():
        url = f"{base}/injuries?league={league_id}&season={season_year}"
        payload = _http_json(url, headers=headers)
        counts: dict[str, int] = {}
        for injury in payload.get("response", []):
            team_name = (((injury or {}).get("team") or {}).get("name") or "").strip()
            if not team_name:
                continue
            counts[team_name] = counts.get(team_name, 0) + 1
        for team_name, count in counts.items():
            out[(league, team_name)] = min(3.0, round(count / 4.0, 2))
    return out


def _apply_enrichment(frame: pd.DataFrame, season_year: int) -> pd.DataFrame:
    if frame.empty:
        return frame

    injury_map = _fetch_api_football_injury_counts(season_year)
    frame["home_injury_impact"] = [
        injury_map.get((league, team), 0.0) for league, team in zip(frame["league"], frame["home_team"])
    ]
    frame["away_injury_impact"] = [
        injury_map.get((league, team), 0.0) for league, team in zip(frame["league"], frame["away_team"])
    ]

    # Fan confidence proxy: recent points-per-game trend (automated, no manual sentiment upload).
    work = frame.sort_values("match_date").copy()
    points_table: dict[str, list[int]] = {}
    home_conf = []
    away_conf = []

    for _, row in work.iterrows():
        home = row["home_team"]
        away = row["away_team"]
        hp = points_table.get(home, [])
        ap = points_table.get(away, [])
        home_conf.append(round((sum(hp[-5:]) / max(1, len(hp[-5:]) * 3)), 3))
        away_conf.append(round((sum(ap[-5:]) / max(1, len(ap[-5:]) * 3)), 3))

        if row["result"] == "H":
            hp.append(3)
            ap.append(0)
        elif row["result"] == "A":
            hp.append(0)
            ap.append(3)
        else:
            hp.append(1)
            ap.append(1)
        points_table[home] = hp
        points_table[away] = ap

    work["home_motivation"] = home_conf
    work["away_motivation"] = away_conf
    return work


def ingest_from_football_data(season_start_year: int) -> pd.DataFrame:
    token = os.getenv("FOOTBALL_DATA_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("FOOTBALL_DATA_API_TOKEN is required for football-data.org ingestion")

    rows: list[dict] = []
    for league, code in FOOTBALL_DATA_COMPETITIONS.items():
        params = urlencode({"season": season_start_year, "status": "FINISHED"})
        url = f"https://api.football-data.org/v4/competitions/{code}/matches?{params}"
        payload = _http_json(url, headers={"X-Auth-Token": token})

        for match in payload.get("matches", []):
            score = match.get("score", {}).get("fullTime", {})
            home_goals = score.get("home")
            away_goals = score.get("away")
            if home_goals is None or away_goals is None:
                continue
            match_date = datetime.fromisoformat(match["utcDate"].replace("Z", "+00:00")).date().isoformat()
            rows.append(
                _build_row(
                    league=league,
                    match_date=match_date,
                    home_team=match["homeTeam"]["name"],
                    away_team=match["awayTeam"]["name"],
                    home_goals=int(home_goals),
                    away_goals=int(away_goals),
                )
            )

    return _apply_enrichment(pd.DataFrame(rows), season_start_year)


def ingest_from_sportsdb(season_label: str) -> pd.DataFrame:
    rows: list[dict] = []
    for league, league_id in SPORTS_DB_LEAGUE_IDS.items():
        url = (
            "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?"
            f"id={league_id}&s={season_label}"
        )
        payload = _http_json(url)
        for event in payload.get("events") or []:
            if event.get("intHomeScore") is None or event.get("intAwayScore") is None:
                continue
            rows.append(
                _build_row(
                    league=league,
                    match_date=event.get("dateEvent", ""),
                    home_team=event.get("strHomeTeam", ""),
                    away_team=event.get("strAwayTeam", ""),
                    home_goals=int(event["intHomeScore"]),
                    away_goals=int(event["intAwayScore"]),
                )
            )

    try:
        season_year = int(season_label.split("-")[0])
    except ValueError:
        season_year = datetime.now(UTC).year
    return _apply_enrichment(pd.DataFrame(rows), season_year)


def _write_status(result: IngestResult) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(asdict(result), indent=2))


def read_ingestion_status() -> dict:
    if not STATUS_PATH.exists():
        return {"status": "not_run"}
    return json.loads(STATUS_PATH.read_text())


def ingest_online(source: str, season: str, window_days: int = 1) -> IngestResult:
    frame = ingest_from_football_data(int(season)) if source == "football_data" else ingest_from_sportsdb(season)
    if frame.empty:
        raise RuntimeError("No matches returned by selected online source")

    today = date.today()
    earliest = (today - timedelta(days=window_days)).isoformat()
    frame = frame[frame["league"].isin(SUPPORTED_LEAGUES)]
    frame = frame[frame["match_date"] >= earliest].copy()

    if HISTORY_PATH.exists():
        prior = pd.read_csv(HISTORY_PATH)
        frame = pd.concat([prior, frame], ignore_index=True)

    frame = frame.drop_duplicates(subset=["match_date", "league", "home_team", "away_team"]).sort_values("match_date")
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(HISTORY_PATH, index=False)

    result = IngestResult(
        source=source,
        rows=int(len(frame)),
        leagues_covered=sorted(frame["league"].dropna().unique().tolist()),
        ingested_at=datetime.now(UTC).isoformat(),
        freshness_window=f"t-{window_days}..t",
    )
    _write_status(result)
    return result

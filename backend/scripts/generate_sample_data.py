from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path
import random

LEAGUE_TEAMS = {
    "Turkish Super Lig": ["Galatasaray", "Fenerbahce", "Besiktas", "Trabzonspor"],
    "Premier League": ["Arsenal", "Liverpool", "Man City", "Chelsea"],
    "La Liga": ["Real Madrid", "Barcelona", "Atletico Madrid", "Sevilla"],
    "Primeira Liga": ["Benfica", "Porto", "Sporting", "Braga"],
    "Bundesliga": ["Bayern", "Dortmund", "Leipzig", "Leverkusen"],
    "Serie A": ["Inter", "Milan", "Juventus", "Napoli"],
    "Scottish Premiership": ["Celtic", "Rangers", "Hearts", "Aberdeen"],
    "UEFA Champions League": ["PSG", "Bayern", "Real Madrid", "Man City"],
}

FIELDS = [
    "match_date",
    "league",
    "home_team",
    "away_team",
    "home_goals",
    "away_goals",
    "home_xg",
    "away_xg",
    "home_injury_impact",
    "away_injury_impact",
    "home_motivation",
    "away_motivation",
    "home_rest_days",
    "away_rest_days",
    "result",
]


def main() -> None:
    random.seed(11)
    start = datetime(2022, 8, 1)
    rows = []

    for league, teams in LEAGUE_TEAMS.items():
        for week in range(90):
            match_date = start + timedelta(days=7 * week)
            home, away = random.sample(teams, 2)
            home_strength = teams.index(home) + 1
            away_strength = teams.index(away) + 1

            home_goals = max(0, int(random.gauss(1.6 + 0.15 * (away_strength - home_strength), 1.0)))
            away_goals = max(0, int(random.gauss(1.2 + 0.1 * (home_strength - away_strength), 0.9)))
            result = "H" if home_goals > away_goals else "A" if away_goals > home_goals else "D"

            rows.append(
                {
                    "match_date": match_date.strftime("%Y-%m-%d"),
                    "league": league,
                    "home_team": home,
                    "away_team": away,
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                    "home_xg": round(max(0.1, random.gauss(home_goals + 0.3, 0.6)), 2),
                    "away_xg": round(max(0.1, random.gauss(away_goals + 0.2, 0.6)), 2),
                    "home_injury_impact": round(random.uniform(0, 1.8), 2),
                    "away_injury_impact": round(random.uniform(0, 1.8), 2),
                    "home_motivation": round(random.uniform(0, 1), 2),
                    "away_motivation": round(random.uniform(0, 1), 2),
                    "home_rest_days": random.randint(2, 7),
                    "away_rest_days": random.randint(2, 7),
                    "result": result,
                }
            )

    out = Path("data/historical_matches.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated {len(rows)} rows at {out}")


if __name__ == "__main__":
    main()

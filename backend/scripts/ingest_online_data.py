from __future__ import annotations

import argparse

from backend.app.online_ingest import ingest_online


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest historical matches from online APIs")
    parser.add_argument("--source", choices=["football_data", "sportsdb"], required=True)
    parser.add_argument("--season", required=True, help="Season start year for football_data, or season label for sportsdb")
    parser.add_argument("--window-days", type=int, default=1, help="Recent window in days to append (t-1 by default)")
    args = parser.parse_args()

    result = ingest_online(args.source, args.season, args.window_days)
    print(
        f"Ingested {result.rows} matches from {result.source}. "
        f"Leagues: {', '.join(result.leagues_covered)}. "
        f"Ingested_at={result.ingested_at} window={result.freshness_window}"
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime


def run(source: str, season: str, window_days: int) -> None:
    cmd = [
        sys.executable,
        "-m",
        "backend.scripts.ingest_online_data",
        "--source",
        source,
        "--season",
        season,
        "--window-days",
        str(window_days),
    ]
    subprocess.check_call(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(description="Automated t/t-1 ingestion + retrain trigger helper")
    parser.add_argument("--source", choices=["football_data", "sportsdb"], default=os.getenv("SOCCER_SOURCE", "sportsdb"))
    parser.add_argument("--season", default=str(datetime.utcnow().year))
    parser.add_argument("--window-days", type=int, default=1)
    args = parser.parse_args()
    run(args.source, args.season, args.window_days)


if __name__ == "__main__":
    main()

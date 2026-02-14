from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .online_ingest import ingest_online, read_ingestion_status


@dataclass(frozen=True)
class DataSourceConfig:
    mode: str
    historical_csv: Path
    description: str


def get_data_source_config() -> DataSourceConfig:
    mode = os.getenv("SOCCER_DATA_SOURCE", "online_api").strip().lower()
    csv_path = Path(os.getenv("SOCCER_HISTORICAL_CSV", "data/historical_matches.csv"))

    if mode == "synthetic_csv":
        description = "Synthetic sample dataset generated locally"
    elif mode == "custom_csv":
        description = "User-supplied historical CSV mounted locally"
    elif mode == "online_api":
        description = "Automated online API ingestion cache (t/t-1 refresh)"
    else:
        description = "Unknown mode (treated as local CSV)"

    return DataSourceConfig(mode=mode, historical_csv=csv_path, description=description)


def _is_stale(status: dict, max_age_hours: int) -> bool:
    stamp = status.get("ingested_at")
    if not stamp:
        return True
    try:
        ingested_at = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return True
    return datetime.now(UTC) - ingested_at > timedelta(hours=max_age_hours)


def auto_refresh_online_data(config: DataSourceConfig) -> dict:
    if config.mode != "online_api":
        return {"status": "skipped", "reason": "mode_not_online_api"}

    if os.getenv("SOCCER_AUTO_INGEST", "true").strip().lower() in {"0", "false", "no"}:
        return {"status": "skipped", "reason": "auto_ingest_disabled"}

    max_age_hours = int(os.getenv("SOCCER_MAX_INGEST_AGE_HOURS", "30"))
    status = read_ingestion_status()
    if config.historical_csv.exists() and not _is_stale(status, max_age_hours):
        return {"status": "fresh", "reason": "existing_recent_ingest"}

    source = os.getenv("SOCCER_INGEST_SOURCE", "sportsdb")
    season = os.getenv("SOCCER_INGEST_SEASON", str(datetime.now(UTC).year))
    window_days = int(os.getenv("SOCCER_INGEST_WINDOW_DAYS", "1"))

    try:
        result = ingest_online(source=source, season=season, window_days=window_days)
        return {
            "status": "ingested",
            "source": result.source,
            "rows": result.rows,
            "ingested_at": result.ingested_at,
            "freshness_window": result.freshness_window,
        }
    except Exception as exc:
        if config.historical_csv.exists():
            return {"status": "warning", "reason": f"ingest_failed_using_cache: {exc}"}
        raise

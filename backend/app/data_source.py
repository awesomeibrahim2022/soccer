from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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

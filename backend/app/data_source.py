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
    mode = os.getenv("SOCCER_DATA_SOURCE", "synthetic_csv").strip().lower()
    csv_path = Path(os.getenv("SOCCER_HISTORICAL_CSV", "data/historical_matches.csv"))

    if mode == "synthetic_csv":
        description = (
            "Synthetic sample dataset generated locally by "
            "backend/scripts/generate_sample_data.py"
        )
    elif mode == "custom_csv":
        description = "User-supplied historical CSV mounted locally"
    else:
        description = "Unknown mode (treated as local CSV)"

    return DataSourceConfig(mode=mode, historical_csv=csv_path, description=description)

"""Support helpers for feature-store schemas, metadata, and synthetic feature generation."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

import numpy as np
import polars as pl


def build_empty_energy_frame() -> pl.DataFrame:
    """Return the empty energy-feature frame with the expected schema."""
    return pl.DataFrame(
        {
            "user_id": pl.Series([], dtype=pl.Utf8),
            "timestamp": pl.Series([], dtype=pl.Datetime),
            "battery_soc": pl.Series([], dtype=pl.Float64),
            "grid_price_uah_kwh": pl.Series([], dtype=pl.Float64),
            "solar_generation_kw": pl.Series([], dtype=pl.Float64),
            "wind_generation_kw": pl.Series([], dtype=pl.Float64),
            "load_demand_kw": pl.Series([], dtype=pl.Float64),
            "temperature_celsius": pl.Series([], dtype=pl.Float64),
            "is_peak_hour": pl.Series([], dtype=pl.Boolean),
            "day_of_week": pl.Series([], dtype=pl.Int32),
            "hour_of_day": pl.Series([], dtype=pl.Int32),
        }
    )


def feature_view_to_dict(feature_view) -> Dict[str, Any]:
    """Convert a feature view object into its persisted metadata shape."""
    return {
        "name": feature_view.name,
        "entities": feature_view.entities,
        "features": [feature.to_dict() for feature in feature_view.features],
        "online": feature_view.online,
        "batch_source": feature_view.batch_source,
        "ttl_hours": feature_view.ttl_hours,
    }


def write_feature_view_metadata(metadata_file: Path, feature_view) -> None:
    """Persist a feature-view definition to disk."""
    with open(metadata_file, "w") as handle:
        json.dump(feature_view_to_dict(feature_view), handle, indent=2)


def read_feature_view_metadata(metadata_file: Path) -> Dict[str, Any]:
    """Load raw feature-view metadata from disk."""
    with open(metadata_file) as handle:
        return json.load(handle)


def build_realistic_price(timestamp: datetime) -> float:
    """Generate a realistic electricity price for a timestamp."""
    base_price = 8.0
    if 6 <= timestamp.hour < 23:
        base_price *= 1.3
    if timestamp.weekday() < 5:
        base_price *= 1.1
    if timestamp.month in [12, 1, 2]:
        base_price *= 1.2
    elif timestamp.month in [6, 7, 8]:
        base_price *= 0.9
    base_price *= 0.8 + 0.4 * np.random.random()
    return round(base_price, 2)


def build_solar_power(timestamp: datetime) -> float:
    """Generate realistic solar power for a timestamp."""
    if timestamp.hour < 6 or timestamp.hour > 18:
        return 0.0
    hour_angle = np.pi * (timestamp.hour - 6) / 12
    solar_factor = np.sin(hour_angle)
    month_factor = 0.5 + 0.5 * np.cos(2 * np.pi * (timestamp.month - 6) / 12)
    weather_factor = 0.3 + 0.7 * np.random.random()
    return max(0, 5.0 * solar_factor * month_factor * weather_factor)


def build_load_demand(timestamp: datetime) -> float:
    """Generate realistic load demand for a timestamp."""
    base_load = 2.0
    if 6 <= timestamp.hour <= 22:
        time_factor = 1.5 + 0.5 * np.sin(2 * np.pi * (timestamp.hour - 6) / 16)
    else:
        time_factor = 0.5 + 0.3 * np.random.random()
    if timestamp.weekday() >= 5:
        time_factor *= 0.8
    random_factor = 0.7 + 0.6 * np.random.random()
    return base_load * time_factor * random_factor


def build_real_time_feature_row(current_time: datetime, entity_keys: Dict[str, Any]) -> Dict[str, Any]:
    """Build the synthetic real-time feature payload."""
    features = {
        "user_id": entity_keys.get("user_id", "default_user"),
        "timestamp": current_time,
        "battery_soc": 0.6 + 0.3 * np.random.random(),
        "grid_price_uah_kwh": 8.0 + 4.0 * np.random.random(),
        "solar_generation_kw": max(0, 3.0 * np.sin(np.pi * (current_time.hour - 6) / 12)),
        "wind_generation_kw": 1.0 + 2.0 * np.random.random(),
        "load_demand_kw": 2.0 + 3.0 * np.random.random(),
        "temperature_celsius": 15.0 + 10.0 * np.random.random(),
        "is_peak_hour": 6 <= current_time.hour < 23,
        "day_of_week": current_time.weekday(),
        "hour_of_day": current_time.hour,
    }
    features["price_ma_24h"] = features["grid_price_uah_kwh"] * (0.9 + 0.2 * np.random.random())
    features["load_ma_7d"] = features["load_demand_kw"] * (0.8 + 0.4 * np.random.random())
    features["generation_forecast_1h"] = (features["solar_generation_kw"] + features["wind_generation_kw"]) * 1.1
    return features


def generate_hourly_timestamps(start_time: datetime, end_time: datetime) -> List[datetime]:
    """Generate an inclusive hourly timestamp range."""
    timestamps: List[datetime] = []
    current_time = start_time.replace(minute=0, second=0, microsecond=0)
    while current_time <= end_time:
        timestamps.append(current_time)
        current_time += timedelta(hours=1)
    return timestamps


def build_batch_feature_row(timestamp: datetime) -> Dict[str, Any]:
    """Build a synthetic batch feature row for a timestamp."""
    row = {
        "user_id": "default_user",
        "timestamp": timestamp,
        "battery_soc": 0.3 + 0.6 * np.random.random(),
        "grid_price_uah_kwh": build_realistic_price(timestamp),
        "solar_generation_kw": build_solar_power(timestamp),
        "wind_generation_kw": 0.5 + 2.5 * np.random.random(),
        "load_demand_kw": build_load_demand(timestamp),
        "temperature_celsius": 10 + 20 * np.random.random(),
        "is_peak_hour": 6 <= timestamp.hour < 23,
        "day_of_week": timestamp.weekday(),
        "hour_of_day": timestamp.hour,
    }
    row["price_ma_24h"] = row["grid_price_uah_kwh"] * (0.9 + 0.2 * np.random.random())
    row["load_ma_7d"] = row["load_demand_kw"] * (0.8 + 0.4 * np.random.random())
    row["generation_forecast_1h"] = (row["solar_generation_kw"] + row["wind_generation_kw"]) * 1.05
    return row
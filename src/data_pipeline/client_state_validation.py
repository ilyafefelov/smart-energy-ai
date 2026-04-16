"""Validation and fallback helpers for client state data."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Dict, List

import polars as pl

from src.data_pipeline.battery_state_loader import CONFIG_STATE_SOURCE


logger = logging.getLogger(__name__)


def _validate_client_data(df: pl.DataFrame) -> pl.DataFrame:
    """Validate and clean client state data while preserving the existing schema contract."""
    logger.info("Validating client state data: %s records", len(df))

    df = df.with_columns(
        [
            pl.col("battery_soc").clip(0, 100).alias("battery_soc"),
            pl.col("battery_temp").clip(-10, 60).alias("battery_temp"),
            pl.col("solar_gen_actual").clip(0, 1000).alias("solar_gen_actual"),
            pl.col("load_actual").clip(0, 1000).alias("load_actual"),
            pl.col("grid_power").clip(-1000, 1000).alias("grid_power"),
            pl.col("system_efficiency").clip(0.5, 1.0).alias("system_efficiency"),
        ]
    )

    df = df.sort(["client_id", "timestamp"])

    df = df.with_columns(
        [
            (pl.col("battery_soc") < 10).alias("low_battery_warning"),
            (pl.col("battery_temp") > 40).alias("high_temp_warning"),
            (pl.col("grid_power").abs() > 500).alias("high_grid_usage"),
            pl.lit(datetime.now()).alias("generated_at"),
        ]
    )

    logger.info("Client data validation complete: %s valid records", len(df))
    return df


def _generate_fallback_client_data() -> List[Dict]:
    """Generate a minimal client-state fallback scaffold when asset generation fails."""
    base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    fallback_data = []

    for hour in range(24):
        fallback_data.append(
            {
                "timestamp": base_time + timedelta(hours=hour),
                "client_id": "fallback_client",
                "battery_soc": 50.0,
                "battery_health": 100.0,
                "battery_cycles": 0.0,
                "battery_temp": 25.0,
                "battery_voltage": 800.0,
                "battery_current": 0.0,
                "solar_gen_actual": 0.0,
                "load_actual": 100.0,
                "grid_power": 100.0,
                "battery_power": 0.0,
                "inverter_status": "IDLE",
                "system_efficiency": 0.90,
                "source": CONFIG_STATE_SOURCE,
                "state_source": "config_fallback",
                "state_source_detail": "asset_generation_fallback",
                "battery_state_updated_at": None,
                "telemetry_classification": "fabricated_training_scaffolding",
            }
        )

    return fallback_data


__all__ = [
    "_generate_fallback_client_data",
    "_validate_client_data",
]
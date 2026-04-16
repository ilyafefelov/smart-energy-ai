"""Reusable weather data validation helpers.

This module owns weather DataFrame cleanup rules that are independent of
Dagster orchestration. Asset layers decide when to validate and how to handle
fallback weather sources.
"""

from __future__ import annotations

from datetime import datetime
import logging

import polars as pl


logger = logging.getLogger(__name__)


def _validate_weather_data(df: pl.DataFrame) -> pl.DataFrame:
    """Validate and clean weather data while preserving the existing schema contract."""
    logger.info("Validating weather data: %s records", len(df))

    df = df.with_columns(
        [
            pl.col("temperature").clip(-40, 50).alias("temperature"),
            pl.col("solar_radiation").clip(0, 1200).alias("solar_radiation"),
            pl.col("wind_speed").clip(0, 50).alias("wind_speed"),
            pl.col("cloudcover").clip(0, 100).alias("cloudcover"),
            pl.col("humidity").clip(0, 100).alias("humidity"),
            pl.col("pressure").clip(950, 1050).alias("pressure"),
            pl.col("precipitation").clip(0, 100).alias("precipitation"),
        ]
    )

    df = df.sort("timestamp")

    df = df.with_columns(
        [
            (pl.col("solar_radiation") > 1000).alias("high_solar"),
            (pl.col("wind_speed") > 15).alias("high_wind"),
            (pl.col("precipitation") > 10).alias("heavy_rain"),
            pl.lit(datetime.now()).alias("fetched_at"),
        ]
    )

    logger.info("Weather validation complete: %s valid records", len(df))
    return df


__all__ = ["_validate_weather_data"]
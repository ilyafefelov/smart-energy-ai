"""Reusable solar feature transformations for weather data."""

from __future__ import annotations

import polars as pl


def _add_solar_features(df: pl.DataFrame, latitude: float) -> pl.DataFrame:
    """Add derived solar features for energy modeling."""

    return df.with_columns([
        pl.col("timestamp").dt.hour().alias("hour"),
        pl.col("timestamp").dt.ordinal_day().alias("day_of_year"),
        _calculate_solar_elevation(pl.col("timestamp"), latitude).alias("solar_elevation"),
        ((100 - pl.col("cloudcover")) / 100).alias("clear_sky_index"),
        (pl.col("solar_radiation") * (100 - pl.col("cloudcover")) / 100).alias("effective_solar"),
        pl.col("timestamp").dt.hour().is_between(6, 18).alias("is_daylight"),
        pl.when(pl.col("timestamp").dt.month().is_in([12, 1, 2]))
        .then(pl.lit("winter"))
        .when(pl.col("timestamp").dt.month().is_in([3, 4, 5]))
        .then(pl.lit("spring"))
        .when(pl.col("timestamp").dt.month().is_in([6, 7, 8]))
        .then(pl.lit("summer"))
        .otherwise(pl.lit("autumn"))
        .alias("season"),
        pl.when(pl.col("cloudcover") < 25)
        .then(pl.lit("clear"))
        .when(pl.col("cloudcover") < 75)
        .then(pl.lit("partly_cloudy"))
        .otherwise(pl.lit("cloudy"))
        .alias("sky_condition"),
    ])


def _calculate_solar_elevation(timestamp_col: pl.Expr, latitude: float) -> pl.Expr:
    """Simplified solar elevation calculation for Polars expressions."""

    _ = latitude
    return (
        pl.lit(90)
        - (timestamp_col.dt.hour() - 12).abs() * pl.lit(15.0 / 90.0) * 90
    ).clip(0, 90)


__all__ = ["_add_solar_features", "_calculate_solar_elevation"]
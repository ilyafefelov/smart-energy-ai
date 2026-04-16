"""Reusable feature helpers for the DAM price forecast baseline."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Tuple

import numpy as np
import polars as pl
from sklearn.metrics import mean_absolute_error, mean_squared_error


def _build_feature_frame(market_data: pl.DataFrame) -> pl.DataFrame:
    ordered = market_data.sort("timestamp")
    return ordered.with_columns(
        [
            pl.col("timestamp").dt.hour().alias("hour"),
            pl.col("timestamp").dt.weekday().alias("weekday"),
            pl.col("timestamp").dt.month().alias("month"),
            pl.col("timestamp").dt.ordinal_day().alias("day_of_year"),
            pl.col("price_eur_mwh").shift(1).alias("lag_1h"),
            pl.col("price_eur_mwh").shift(24).alias("lag_24h"),
            pl.col("price_eur_mwh").rolling_mean(window_size=24).alias("roll_mean_24h"),
            pl.col("price_eur_mwh").rolling_std(window_size=24).alias("roll_std_24h"),
            pl.col("price_eur_mwh").shift(-24).alias("target_price_t_plus_24h"),
            pl.col("timestamp").dt.weekday().is_in([5, 6]).cast(pl.Int8).alias("is_weekend"),
        ]
    )


def _split_train_eval(df: pl.DataFrame) -> Tuple[pl.DataFrame, pl.DataFrame]:
    if len(df) < 72:
        return df, pl.DataFrame(schema=df.schema)
    eval_size = max(24, int(len(df) * 0.2))
    return df.slice(0, len(df) - eval_size), df.slice(len(df) - eval_size, eval_size)


def _build_persistence_forecast(market_data: pl.DataFrame, labeled_rows: int) -> pl.DataFrame:
    last_prices = market_data.sort("timestamp").tail(24)
    anchor = market_data.sort("timestamp").select("price_eur_mwh").tail(1).item()
    return last_prices.select(
        [
            (pl.col("timestamp") + pl.duration(hours=24)).alias("forecast_timestamp"),
            pl.lit(float(anchor)).alias("predicted_price_eur_mwh"),
            pl.lit(float(anchor)).alias("lower_bound_eur_mwh"),
            pl.lit(float(anchor)).alias("upper_bound_eur_mwh"),
            pl.lit("persistence_fallback").alias("model_name"),
            pl.lit(datetime.now(timezone.utc)).alias("trained_at_utc"),
            pl.lit(0.0).alias("eval_rmse"),
            pl.lit(0.0).alias("eval_mae"),
            pl.lit(labeled_rows).alias("training_rows"),
        ]
    )


def _compute_eval_metrics(model, eval_df: pl.DataFrame, feature_cols: Sequence[str]) -> Tuple[float, float, float]:
    x_eval = eval_df.select(feature_cols).to_numpy()
    y_eval = eval_df.select("target_price_t_plus_24h").to_numpy().reshape(-1)
    y_hat = model.predict(x_eval)
    eval_rmse = float(np.sqrt(mean_squared_error(y_eval, y_hat)))
    eval_mae = float(mean_absolute_error(y_eval, y_hat))
    residual_std = float(np.std(y_eval - y_hat))
    return eval_rmse, eval_mae, residual_std


__all__ = [
    "_build_feature_frame",
    "_build_persistence_forecast",
    "_compute_eval_metrics",
    "_split_train_eval",
]
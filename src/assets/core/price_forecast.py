"""
DAM Price Forecast Asset.

Builds a day-ahead (24h) baseline forecasting model from historical market data.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import polars as pl
from dagster import AssetIn, asset
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from src.data_pipeline.price_forecast_features import (
    _build_feature_frame,
    _build_persistence_forecast,
    _compute_eval_metrics,
    _split_train_eval,
)


@asset(
    group_name="market_data",
    description="24-hour day-ahead market (DAM) price forecast baseline model",
    ins={"market_data": AssetIn("market_data_asset")},
    metadata={
        "forecast_horizon_hours": 24,
        "model_family": "random_forest_regressor",
        "target_market": "DAM Ukraine",
    },
)
def price_forecast_asset(market_data: pl.DataFrame) -> pl.DataFrame:
    """
    Train a baseline DAM forecaster and return the next 24 hourly predictions.
    """
    feature_df = _build_feature_frame(market_data)

    labeled = feature_df.drop_nulls(
        [
            "lag_1h",
            "lag_24h",
            "roll_mean_24h",
            "roll_std_24h",
            "target_price_t_plus_24h",
        ]
    )

    if len(labeled) < 48:
        return _build_persistence_forecast(market_data, len(labeled))

    train_df, eval_df = _split_train_eval(labeled)
    feature_cols = [
        "hour",
        "weekday",
        "month",
        "day_of_year",
        "is_weekend",
        "lag_1h",
        "lag_24h",
        "roll_mean_24h",
        "roll_std_24h",
    ]

    x_train = train_df.select(feature_cols).to_numpy()
    y_train = train_df.select("target_price_t_plus_24h").to_numpy().reshape(-1)

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=14,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(x_train, y_train)

    eval_rmse = 0.0
    eval_mae = 0.0
    residual_std = 0.0
    if len(eval_df) > 0:
        eval_rmse, eval_mae, residual_std = _compute_eval_metrics(model, eval_df, feature_cols)

    # For 24h-ahead horizon, use the latest 24 feature rows as inference inputs.
    infer_features = feature_df.drop_nulls(["lag_1h", "lag_24h", "roll_mean_24h", "roll_std_24h"]).tail(24)
    x_infer = infer_features.select(feature_cols).to_numpy()
    predictions = model.predict(x_infer)

    spread = residual_std if residual_std > 0 else max(eval_rmse, 5.0)
    forecast_df = infer_features.select(
        [
            (pl.col("timestamp") + pl.duration(hours=24)).alias("forecast_timestamp"),
        ]
    ).with_columns(
        [
            pl.Series("predicted_price_eur_mwh", predictions.tolist()).clip(0.0, 1000.0),
        ]
    ).with_columns(
        [
            (pl.col("predicted_price_eur_mwh") - spread).clip(0.0, 1000.0).alias("lower_bound_eur_mwh"),
            (pl.col("predicted_price_eur_mwh") + spread).clip(0.0, 1000.0).alias("upper_bound_eur_mwh"),
            pl.lit("random_forest_dam_24h").alias("model_name"),
            pl.lit(datetime.now(timezone.utc)).alias("trained_at_utc"),
            pl.lit(eval_rmse).alias("eval_rmse"),
            pl.lit(eval_mae).alias("eval_mae"),
            pl.lit(len(train_df)).alias("training_rows"),
        ]
    )

    return forecast_df.sort("forecast_timestamp")

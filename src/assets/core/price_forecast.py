"""
DAM Price Forecast Asset.

Builds a day-ahead (24h) baseline forecasting model from historical market data.
"""

from __future__ import annotations

from datetime import datetime, timezone

import polars as pl
from dagster import AssetIn, asset
from src.data_pipeline.forecast_model_registry import (
    DEFAULT_FORECAST_MODEL_NAME,
    get_forecast_model_spec,
    resolve_active_forecast_model_name,
)
from src.data_pipeline.price_forecast_features import (
    _build_feature_frame,
    _build_persistence_forecast,
    _compute_eval_metrics,
    _fit_forecast_model,
    _predict_forecast_model,
    _run_walk_forward_evaluation,
    _split_train_eval,
)


def _build_forecast_with_model_spec(
    market_data: pl.DataFrame, model_spec
) -> pl.DataFrame:
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

    model = model_spec.build_estimator()
    _fit_forecast_model(model, train_df, feature_cols)

    eval_rmse = 0.0
    eval_mae = 0.0
    residual_std = 0.0
    eval_value_capture_ratio = 0.0
    eval_realized_spread_eur_mwh = 0.0
    eval_optimal_spread_eur_mwh = 0.0
    evaluation_folds = 0
    walk_forward_metrics = _run_walk_forward_evaluation(
        labeled,
        feature_cols,
        model_spec.build_estimator,
        min_train_size=48,
        eval_size=24,
        step_size=24,
    )
    if int(walk_forward_metrics["fold_count"]) > 0:
        eval_rmse = walk_forward_metrics["eval_rmse"]
        eval_mae = walk_forward_metrics["eval_mae"]
        residual_std = walk_forward_metrics["residual_std"]
        eval_value_capture_ratio = walk_forward_metrics["value_capture_ratio"]
        eval_realized_spread_eur_mwh = walk_forward_metrics["realized_spread_eur_mwh"]
        eval_optimal_spread_eur_mwh = walk_forward_metrics["optimal_spread_eur_mwh"]
        evaluation_folds = int(walk_forward_metrics["fold_count"])
    elif len(eval_df) > 0:
        eval_rmse, eval_mae, residual_std = _compute_eval_metrics(model, eval_df, feature_cols)

    # For 24h-ahead horizon, use the latest 24 feature rows as inference inputs.
    infer_features = feature_df.drop_nulls(["lag_1h", "lag_24h", "roll_mean_24h", "roll_std_24h"]).tail(24)
    x_infer = infer_features.select(feature_cols).to_numpy()
    predictions = _predict_forecast_model(model, infer_features, feature_cols)

    spread = residual_std if residual_std > 0 else max(eval_rmse, 5.0)
    forecast_df = infer_features.select(
        [
            (pl.col("timestamp") + pl.duration(hours=24)).alias("forecast_timestamp"),
        ]
    ).with_columns(
        [
            pl.Series("predicted_price_eur_mwh", list(predictions)).clip(0.0, 1000.0),
        ]
    ).with_columns(
        [
            (pl.col("predicted_price_eur_mwh") - spread).clip(0.0, 1000.0).alias("lower_bound_eur_mwh"),
            (pl.col("predicted_price_eur_mwh") + spread).clip(0.0, 1000.0).alias("upper_bound_eur_mwh"),
            pl.lit(model_spec.model_name).alias("model_name"),
            pl.lit(model_spec.model_family).alias("model_family"),
            pl.lit(datetime.now(timezone.utc)).alias("trained_at_utc"),
            pl.lit(model_spec.forecast_horizon_hours).alias("forecast_horizon_hours"),
            pl.lit(eval_rmse).alias("eval_rmse"),
            pl.lit(eval_mae).alias("eval_mae"),
            pl.lit(eval_value_capture_ratio).alias("eval_value_capture_ratio"),
            pl.lit(eval_realized_spread_eur_mwh).alias("eval_realized_spread_eur_mwh"),
            pl.lit(eval_optimal_spread_eur_mwh).alias("eval_optimal_spread_eur_mwh"),
            pl.lit(evaluation_folds).alias("evaluation_folds"),
            pl.lit(len(train_df)).alias("training_rows"),
        ]
    )

    return forecast_df.sort("forecast_timestamp")


@asset(
    group_name="market_data",
    description="24-hour day-ahead market (DAM) price forecast baseline model",
    ins={"market_data": AssetIn("market_data_asset")},
    metadata={
        "forecast_horizon_hours": 24,
        "default_model_name": DEFAULT_FORECAST_MODEL_NAME,
        "model_registry_enabled": True,
        "target_market": "DAM Ukraine",
    },
)
def price_forecast_asset(market_data: pl.DataFrame) -> pl.DataFrame:
    """
    Train a baseline DAM forecaster and return the next 24 hourly predictions.
    """
    resolved_model_name = resolve_active_forecast_model_name()
    model_spec = get_forecast_model_spec(resolved_model_name)
    return _build_forecast_with_model_spec(market_data, model_spec)

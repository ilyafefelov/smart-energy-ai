"""
DAM Price Forecast Asset.

Builds a day-ahead (24h) baseline forecasting model from historical market data.
"""

from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter

import polars as pl
from dagster import AssetIn, asset
from src.data_pipeline.forecast_lineage import build_forecast_lineage
from src.data_pipeline.forecast_model_registry import (
    DEFAULT_FORECAST_MODEL_NAME,
    get_forecast_model_spec,
    load_promoted_forecast_metadata,
    resolve_forecast_model_version,
    resolve_active_forecast_model_name,
)
from src.data_pipeline.price_forecast_features import (
    _build_feature_frame,
    _build_persistence_forecast,
    _build_uncertainty_contract_columns,
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

    if residual_std > 0:
        spread = residual_std
        uncertainty_source = "walk_forward_residual_std"
    elif eval_rmse > 0:
        spread = max(eval_rmse, 5.0)
        uncertainty_source = "eval_rmse_floor"
    else:
        spread = 5.0
        uncertainty_source = "minimum_spread_floor"

    # Phase 2: Compute residual skewness for asymmetric quantile intervals
    residual_skewness = 0.0
    if int(walk_forward_metrics["fold_count"]) > 0:
        # Compute skewness from walk-forward residuals
        all_residuals: list[float] = []
        labeled_sorted = labeled.sort("timestamp")
        min_train = 48
        eval_size = 24
        step_size = 24
        for train_end in range(min_train, len(labeled_sorted) - eval_size + 1, step_size):
            train_df = labeled_sorted.slice(0, train_end)
            eval_df = labeled_sorted.slice(train_end, eval_size)
            if len(eval_df) == 0:
                continue
            fold_model = model_spec.build_estimator()
            _fit_forecast_model(fold_model, train_df, feature_cols)
            y_eval = eval_df.select("target_price_t_plus_24h").to_numpy().reshape(-1)
            y_hat = _predict_forecast_model(fold_model, eval_df, feature_cols)
            all_residuals.extend((y_eval - y_hat).tolist())
        if len(all_residuals) >= 3:
            from scipy import stats as scipy_stats
            residual_skewness = float(scipy_stats.skew(all_residuals))

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
            *_build_uncertainty_contract_columns(
                spread=spread,
                uncertainty_source=uncertainty_source,
                residual_std=residual_std,
                skewness=residual_skewness,
            ),
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


def _attach_promotion_provenance(
    forecast_df: pl.DataFrame,
    *,
    resolved_model_name: str,
    promoted_metadata: dict[str, object] | None,
) -> pl.DataFrame:
    comparison_model_name = resolved_model_name
    if len(forecast_df) > 0:
        comparison_model_name = str(
            forecast_df.sort("forecast_timestamp").select("model_name").to_series().to_list()[0]
        )

    active_promotion = None
    if (
        promoted_metadata is not None
        and promoted_metadata.get("model_name") == comparison_model_name
    ):
        active_promotion = promoted_metadata

    return forecast_df.with_columns(
        [
            pl.lit(active_promotion is not None, dtype=pl.Boolean).alias(
                "promotion_active"
            ),
            pl.lit(
                active_promotion.get("promotion_source") if active_promotion else None,
                dtype=pl.Utf8,
            ).alias("promotion_source"),
            pl.lit(
                active_promotion.get("promoted_at_utc") if active_promotion else None,
                dtype=pl.Utf8,
            ).alias("promotion_promoted_at_utc"),
            pl.lit(
                active_promotion.get("benchmark_value_capture_ratio")
                if active_promotion
                else None,
                dtype=pl.Float64,
            ).alias("promotion_benchmark_value_capture_ratio"),
            pl.lit(
                active_promotion.get("benchmark_rmse") if active_promotion else None,
                dtype=pl.Float64,
            ).alias("promotion_benchmark_rmse"),
            pl.lit(
                active_promotion.get("benchmark_mae") if active_promotion else None,
                dtype=pl.Float64,
            ).alias("promotion_benchmark_mae"),
            pl.lit(
                active_promotion.get("benchmark_uncertainty_source")
                if active_promotion
                else None,
                dtype=pl.Utf8,
            ).alias("promotion_benchmark_uncertainty_source"),
            pl.lit(
                active_promotion.get("benchmark_avg_uncertainty_spread_eur_mwh")
                if active_promotion
                else None,
                dtype=pl.Float64,
            ).alias("promotion_benchmark_avg_uncertainty_spread_eur_mwh"),
            pl.lit(
                active_promotion.get("benchmark_max_uncertainty_spread_eur_mwh")
                if active_promotion
                else None,
                dtype=pl.Float64,
            ).alias("promotion_benchmark_max_uncertainty_spread_eur_mwh"),
            pl.lit(
                active_promotion.get("benchmark_candidate_status")
                if active_promotion
                else None,
                dtype=pl.Utf8,
            ).alias("promotion_benchmark_candidate_status"),
            pl.lit(
                active_promotion.get("benchmark_candidate_ready")
                if active_promotion
                else None,
                dtype=pl.Boolean,
            ).alias("promotion_benchmark_candidate_ready"),
            pl.lit(
                active_promotion.get("benchmark_candidate_rank")
                if active_promotion
                else None,
                dtype=pl.Int64,
            ).alias("promotion_benchmark_candidate_rank"),
            pl.lit(
                active_promotion.get("promotion_decision") if active_promotion else None,
                dtype=pl.Utf8,
            ).alias("promotion_decision"),
            pl.lit(
                active_promotion.get("promotion_decision_reason")
                if active_promotion
                else None,
                dtype=pl.Utf8,
            ).alias("promotion_decision_reason"),
            pl.lit(
                active_promotion.get("promotion_gate_version")
                if active_promotion
                else None,
                dtype=pl.Utf8,
            ).alias("promotion_gate_version"),
        ]
    )


def _attach_forecast_lineage(
    forecast_df: pl.DataFrame,
    *,
    source_max_timestamp: datetime | None,
    promoted_metadata: dict[str, object] | None,
    latency_ms: int,
) -> pl.DataFrame:
    forecast_rows = forecast_df.sort("forecast_timestamp").to_dicts() if len(forecast_df) else []
    actual_model_name = str(forecast_rows[0].get("model_name") or "").strip() if forecast_rows else ""
    lineage = build_forecast_lineage(
        forecast_rows,
        model_name=actual_model_name or None,
        model_family=str(forecast_rows[0].get("model_family") or "").strip() or None if forecast_rows else None,
        model_version=resolve_forecast_model_version(actual_model_name or "unknown", promoted_metadata),
        source_max_timestamp=source_max_timestamp,
        latency_ms=latency_ms,
    )

    return forecast_df.with_columns(
        [
            pl.lit(lineage["forecast_run_id"], dtype=pl.Utf8).alias("forecast_run_id"),
            pl.lit(lineage["forecast_model_version"], dtype=pl.Utf8).alias("forecast_model_version"),
            pl.lit(lineage["forecast_window_start_utc"], dtype=pl.Utf8).alias("forecast_window_start_utc"),
            pl.lit(lineage["forecast_window_end_utc"], dtype=pl.Utf8).alias("forecast_window_end_utc"),
            pl.lit(lineage["forecast_latency_ms"], dtype=pl.Int64).alias("forecast_latency_ms"),
            pl.lit(lineage["forecast_freshness_minutes"], dtype=pl.Float64).alias("forecast_freshness_minutes"),
        ]
    )


@asset(
    group_name="market_data",
    description="24-hour day-ahead market (DAM) price forecast baseline model",
    ins={"market_data": AssetIn("market_data_asset")},
    metadata={
        "forecast_horizon_hours": 24,
        "default_model_name": DEFAULT_FORECAST_MODEL_NAME,
        "model_registry_enabled": True,
        "runtime_selection": "validated_benchmark_promotion_only",
        "lineage_fields": [
            "forecast_run_id",
            "forecast_model_version",
            "forecast_latency_ms",
            "forecast_freshness_minutes",
        ],
        "target_market": "DAM Ukraine",
    },
)
def price_forecast_asset(market_data: pl.DataFrame) -> pl.DataFrame:
    """
    Train a baseline DAM forecaster and return the next 24 hourly predictions.
    """
    started_at = perf_counter()
    resolved_model_name = resolve_active_forecast_model_name()
    promoted_metadata = load_promoted_forecast_metadata()
    model_spec = get_forecast_model_spec(resolved_model_name)
    forecast_df = _build_forecast_with_model_spec(market_data, model_spec)
    forecast_df = _attach_promotion_provenance(
        forecast_df,
        resolved_model_name=resolved_model_name,
        promoted_metadata=promoted_metadata,
    )
    source_max_timestamp = None
    if len(market_data) and "timestamp" in market_data.columns:
        source_max_timestamp = market_data.sort("timestamp").select("timestamp").to_series().to_list()[-1]

    return _attach_forecast_lineage(
        forecast_df,
        source_max_timestamp=source_max_timestamp,
        promoted_metadata=promoted_metadata,
        latency_ms=int((perf_counter() - started_at) * 1000),
    )

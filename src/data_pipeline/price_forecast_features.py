"""Reusable feature helpers for the DAM price forecast baseline."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Sequence, Tuple

import numpy as np
import polars as pl
from sklearn.metrics import mean_absolute_error, mean_squared_error


UNCERTAINTY_CONTRACT_VERSION = "probabilistic_forecast_v1"
SCENARIO_LOW_QUANTILE = 0.10
SCENARIO_BASE_QUANTILE = 0.50
SCENARIO_HIGH_QUANTILE = 0.90


def _fit_forecast_model(
    model: object,
    train_df: pl.DataFrame,
    feature_cols: Sequence[str],
    target_col: str = "target_price_t_plus_24h",
) -> None:
    fit_frame = getattr(model, "fit_frame", None)
    if callable(fit_frame):
        fit_frame(train_df, feature_cols, target_col)
        return

    x_train = train_df.select(feature_cols).to_numpy()
    y_train = train_df.select(target_col).to_numpy().reshape(-1)
    model.fit(x_train, y_train)


def _predict_forecast_model(
    model: object,
    df: pl.DataFrame,
    feature_cols: Sequence[str],
) -> np.ndarray:
    predict_frame = getattr(model, "predict_frame", None)
    if callable(predict_frame):
        predictions = predict_frame(df, feature_cols)
    else:
        predictions = model.predict(df.select(feature_cols).to_numpy())
    return np.asarray(predictions, dtype=float).reshape(-1)


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


def _build_uncertainty_contract_columns(
    *,
    spread: float,
    uncertainty_source: str,
    residual_std: float = 0.0,
    skewness: float = 0.0,
) -> list[pl.Expr]:
    """Build uncertainty contract columns with quantile-based intervals.

    Args:
        spread: The uncertainty spread (residual_std or fallback).
        uncertainty_source: Source of uncertainty estimate.
        residual_std: Standard deviation of residuals for quantile calculation.
        skewness: Skewness of residuals for asymmetric intervals.

    Returns:
        List of polars expressions for uncertainty columns.
    """
    bounded_spread = max(float(spread), 0.0)

    # Calculate quantile-based intervals from residual distribution
    # Using normal approximation with optional skewness adjustment
    # p10 = mean - 1.28 * std, p90 = mean + 1.28 * std
    # p25 = mean - 0.67 * std, p75 = mean + 0.67 * std
    quantile_std = residual_std if residual_std > 0 else bounded_spread

    # Apply skewness adjustment for asymmetric intervals
    # Positive skew: upper tail is fatter, negative skew: lower tail is fatter
    skew_adj = float(skewness) * 0.5  # Dampen skewness effect

    # Quantile factors (normal distribution)
    q10_factor = -1.28 + skew_adj
    q25_factor = -0.67 + skew_adj
    q75_factor = 0.67 + skew_adj
    q90_factor = 1.28 + skew_adj

    return [
        # Legacy symmetric bounds (backward compatibility)
        (pl.col("predicted_price_eur_mwh") - bounded_spread)
        .clip(0.0, 1000.0)
        .alias("lower_bound_eur_mwh"),
        (pl.col("predicted_price_eur_mwh") - bounded_spread)
        .clip(0.0, 1000.0)
        .alias("scenario_low_price_eur_mwh"),
        pl.col("predicted_price_eur_mwh").alias("scenario_base_price_eur_mwh"),
        (pl.col("predicted_price_eur_mwh") + bounded_spread)
        .clip(0.0, 1000.0)
        .alias("scenario_high_price_eur_mwh"),
        (pl.col("predicted_price_eur_mwh") + bounded_spread)
        .clip(0.0, 1000.0)
        .alias("upper_bound_eur_mwh"),

        # Explicit scenario contract metadata
        pl.lit(UNCERTAINTY_CONTRACT_VERSION).alias("uncertainty_contract_version"),
        pl.lit(3, dtype=pl.Int8).alias("scenario_count"),
        pl.lit(SCENARIO_LOW_QUANTILE).alias("scenario_low_quantile"),
        pl.lit(SCENARIO_BASE_QUANTILE).alias("scenario_base_quantile"),
        pl.lit(SCENARIO_HIGH_QUANTILE).alias("scenario_high_quantile"),

        # Phase 2: Explicit quantile columns for probabilistic forecasting
        (pl.col("predicted_price_eur_mwh") + q10_factor * quantile_std)
        .clip(0.0, 1000.0)
        .alias("quantile_p10_eur_mwh"),
        (pl.col("predicted_price_eur_mwh") + q25_factor * quantile_std)
        .clip(0.0, 1000.0)
        .alias("quantile_p25_eur_mwh"),
        pl.col("predicted_price_eur_mwh").alias("quantile_p50_eur_mwh"),  # Same as point forecast
        (pl.col("predicted_price_eur_mwh") + q75_factor * quantile_std)
        .clip(0.0, 1000.0)
        .alias("quantile_p75_eur_mwh"),
        (pl.col("predicted_price_eur_mwh") + q90_factor * quantile_std)
        .clip(0.0, 1000.0)
        .alias("quantile_p90_eur_mwh"),

        # Summary statistics
        pl.lit(bounded_spread).alias("uncertainty_spread_eur_mwh"),
        pl.lit(uncertainty_source).alias("uncertainty_source"),
        pl.lit(quantile_std).alias("quantile_std_eur_mwh"),
        pl.lit(skewness).alias("residual_skewness"),
    ]


def _build_persistence_forecast(market_data: pl.DataFrame, labeled_rows: int) -> pl.DataFrame:
    last_prices = market_data.sort("timestamp").tail(24)
    anchor = market_data.sort("timestamp").select("price_eur_mwh").tail(1).item()
    return last_prices.select(
        [
            (pl.col("timestamp") + pl.duration(hours=24)).alias("forecast_timestamp"),
            pl.lit(float(anchor)).alias("predicted_price_eur_mwh"),
            pl.lit("persistence_fallback").alias("model_name"),
            pl.lit("persistence").alias("model_family"),
            pl.lit(datetime.now(timezone.utc)).alias("trained_at_utc"),
            pl.lit(24).alias("forecast_horizon_hours"),
            pl.lit(0.0).alias("eval_rmse"),
            pl.lit(0.0).alias("eval_mae"),
            pl.lit(0.0).alias("eval_value_capture_ratio"),
            pl.lit(0.0).alias("eval_realized_spread_eur_mwh"),
            pl.lit(0.0).alias("eval_optimal_spread_eur_mwh"),
            pl.lit(0).alias("evaluation_folds"),
            pl.lit(labeled_rows).alias("training_rows"),
        ]
    ).with_columns(
        _build_uncertainty_contract_columns(
            spread=0.0,
            uncertainty_source="persistence_flat",
        )
    )


def _compute_eval_metrics(model, eval_df: pl.DataFrame, feature_cols: Sequence[str]) -> Tuple[float, float, float]:
    y_eval = eval_df.select("target_price_t_plus_24h").to_numpy().reshape(-1)
    y_hat = _predict_forecast_model(model, eval_df, feature_cols)
    eval_rmse = float(np.sqrt(mean_squared_error(y_eval, y_hat)))
    eval_mae = float(mean_absolute_error(y_eval, y_hat))
    residual_std = float(np.std(y_eval - y_hat))
    return eval_rmse, eval_mae, residual_std


def _best_one_cycle_trade(prices: np.ndarray) -> Tuple[int, int, float]:
    if len(prices) < 2:
        return 0, 0, 0.0

    min_index = 0
    buy_index = 0
    sell_index = 0
    best_spread = 0.0

    for current_index in range(1, len(prices)):
        current_spread = float(prices[current_index] - prices[min_index])
        if current_spread > best_spread:
            best_spread = current_spread
            buy_index = min_index
            sell_index = current_index
        if prices[current_index] < prices[min_index]:
            min_index = current_index

    return buy_index, sell_index, best_spread


def _compute_value_capture_metrics(actual_prices: np.ndarray, predicted_prices: np.ndarray) -> dict[str, float]:
    actual = np.asarray(actual_prices, dtype=float).reshape(-1)
    predicted = np.asarray(predicted_prices, dtype=float).reshape(-1)

    if len(actual) != len(predicted) or len(actual) < 2:
        return {
            "value_capture_ratio": 0.0,
            "realized_spread_eur_mwh": 0.0,
            "optimal_spread_eur_mwh": 0.0,
        }

    predicted_buy, predicted_sell, _ = _best_one_cycle_trade(predicted)
    realized_spread = 0.0
    if predicted_sell > predicted_buy:
        realized_spread = max(float(actual[predicted_sell] - actual[predicted_buy]), 0.0)

    _, _, optimal_spread = _best_one_cycle_trade(actual)
    if optimal_spread <= 0.0:
        value_capture_ratio = 1.0 if realized_spread <= 0.0 else 0.0
    else:
        value_capture_ratio = realized_spread / optimal_spread

    return {
        "value_capture_ratio": float(value_capture_ratio),
        "realized_spread_eur_mwh": float(realized_spread),
        "optimal_spread_eur_mwh": float(optimal_spread),
    }


def _run_walk_forward_evaluation(
    labeled_df: pl.DataFrame,
    feature_cols: Sequence[str],
    model_builder: Callable[[], object],
    *,
    target_col: str = "target_price_t_plus_24h",
    min_train_size: int = 48,
    eval_size: int = 24,
    step_size: int = 24,
) -> dict[str, float]:
    if len(labeled_df) < min_train_size + eval_size:
        return {
            "eval_rmse": 0.0,
            "eval_mae": 0.0,
            "residual_std": 0.0,
            "value_capture_ratio": 0.0,
            "realized_spread_eur_mwh": 0.0,
            "optimal_spread_eur_mwh": 0.0,
            "fold_count": 0.0,
        }

    fold_metrics: list[dict[str, float]] = []
    last_train_end = len(labeled_df) - eval_size
    for train_end in range(min_train_size, last_train_end + 1, step_size):
        train_df = labeled_df.slice(0, train_end)
        eval_df = labeled_df.slice(train_end, eval_size)
        if len(eval_df) == 0:
            continue

        model = model_builder()
        _fit_forecast_model(model, train_df, feature_cols, target_col)

        y_eval = eval_df.select(target_col).to_numpy().reshape(-1)
        y_hat = _predict_forecast_model(model, eval_df, feature_cols)

        value_metrics = _compute_value_capture_metrics(y_eval, y_hat)
        fold_metrics.append(
            {
                "eval_rmse": float(np.sqrt(mean_squared_error(y_eval, y_hat))),
                "eval_mae": float(mean_absolute_error(y_eval, y_hat)),
                "residual_std": float(np.std(y_eval - y_hat)),
                **value_metrics,
            }
        )

    if not fold_metrics:
        return {
            "eval_rmse": 0.0,
            "eval_mae": 0.0,
            "residual_std": 0.0,
            "value_capture_ratio": 0.0,
            "realized_spread_eur_mwh": 0.0,
            "optimal_spread_eur_mwh": 0.0,
            "fold_count": 0.0,
        }

    return {
        "eval_rmse": float(np.mean([fold["eval_rmse"] for fold in fold_metrics])),
        "eval_mae": float(np.mean([fold["eval_mae"] for fold in fold_metrics])),
        "residual_std": float(np.mean([fold["residual_std"] for fold in fold_metrics])),
        "value_capture_ratio": float(
            np.mean([fold["value_capture_ratio"] for fold in fold_metrics])
        ),
        "realized_spread_eur_mwh": float(
            np.mean([fold["realized_spread_eur_mwh"] for fold in fold_metrics])
        ),
        "optimal_spread_eur_mwh": float(
            np.mean([fold["optimal_spread_eur_mwh"] for fold in fold_metrics])
        ),
        "fold_count": float(len(fold_metrics)),
    }


__all__ = [
    "UNCERTAINTY_CONTRACT_VERSION",
    "SCENARIO_LOW_QUANTILE",
    "SCENARIO_BASE_QUANTILE",
    "SCENARIO_HIGH_QUANTILE",
    "_build_feature_frame",
    "_build_persistence_forecast",
    "_build_uncertainty_contract_columns",
    "_compute_eval_metrics",
    "_compute_value_capture_metrics",
    "_fit_forecast_model",
    "_predict_forecast_model",
    "_run_walk_forward_evaluation",
    "_split_train_eval",
]
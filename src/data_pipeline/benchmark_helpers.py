"""Reusable benchmark analysis, scenario, and MLflow helpers."""

from datetime import datetime
from math import sqrt
from typing import Any, Sequence, TypedDict

import mlflow
import polars as pl


class BenchmarkMetrics(TypedDict):
    engine_name: str
    data_size: int
    processing_time_seconds: float
    memory_peak_mb: float
    memory_current_mb: float
    throughput_records_per_second: float
    success: bool
    error_message: str | None
    output_rows: int
    benchmark_timestamp: datetime


FORECAST_VALUE_SCORECARD_SCHEMA = {
    "model_name": pl.Utf8,
    "model_family": pl.Utf8,
    "forecast_horizon_hours": pl.Int64,
    "forecast_rows": pl.Int64,
    "training_rows": pl.Int64,
    "evaluation_folds": pl.Int64,
    "eval_rmse": pl.Float64,
    "eval_mae": pl.Float64,
    "eval_value_capture_ratio": pl.Float64,
    "eval_realized_spread_eur_mwh": pl.Float64,
    "eval_optimal_spread_eur_mwh": pl.Float64,
    "benchmark_rmse": pl.Float64,
    "benchmark_mae": pl.Float64,
    "benchmark_value_capture_ratio": pl.Float64,
    "benchmark_realized_spread_eur_mwh": pl.Float64,
    "benchmark_optimal_spread_eur_mwh": pl.Float64,
    "benchmark_window_start": pl.Datetime,
    "benchmark_window_end": pl.Datetime,
    "benchmark_timestamp": pl.Datetime,
}


def add_performance_analysis(df: pl.DataFrame) -> pl.DataFrame:
    """Add rankings and ratio columns to benchmark results."""

    df = df.with_columns(
        [
            pl.col("processing_time_seconds").rank().over("data_size").alias("time_rank"),
            pl.col("throughput_records_per_second")
            .rank(descending=True)
            .over("data_size")
            .alias("throughput_rank"),
            pl.col("memory_peak_mb").rank().over("data_size").alias("memory_rank"),
            pl.col("success").cast(pl.Int32).alias("success_int"),
        ]
    )

    df = df.with_columns(
        [
            (
                pl.col("processing_time_seconds")
                / pl.col("processing_time_seconds").min().over("data_size")
            ).alias("time_ratio"),
            (
                pl.col("throughput_records_per_second")
                / pl.col("throughput_records_per_second").max().over("data_size")
            ).alias("throughput_ratio"),
            (
                pl.col("memory_peak_mb") / pl.col("memory_peak_mb").min().over("data_size")
            ).alias("memory_ratio"),
        ]
    )

    return df.with_columns(
        [
            pl.when(pl.col("time_ratio") <= 1.2)
            .then(pl.lit("excellent"))
            .when(pl.col("time_ratio") <= 2.0)
            .then(pl.lit("good"))
            .when(pl.col("time_ratio") <= 5.0)
            .then(pl.lit("acceptable"))
            .otherwise(pl.lit("poor"))
            .alias("performance_category"),
            pl.when(pl.col("memory_ratio") <= 1.5)
            .then(pl.lit("efficient"))
            .when(pl.col("memory_ratio") <= 3.0)
            .then(pl.lit("moderate"))
            .otherwise(pl.lit("memory_intensive"))
            .alias("memory_category"),
        ]
    )


def create_economic_test_scenarios() -> list[dict[str, Any]]:
    """Create benchmark scenarios with known economic expectations."""

    from physics.economics import BatteryTechnology, OperationProfile

    return [
        {
            "name": "standard_lfp_system",
            "expected_lcos": 0.080,
            "expected_arbitrage": 50.0,
            "technology": BatteryTechnology.LFP,
            "capacity_kwh": 100.0,
            "operation_profile": OperationProfile(
                daily_cycles=1.0,
                seasonal_variation=0.2,
                capacity_factor=0.85,
                grid_services_revenue=0.0,
                energy_arbitrage_spread=40.0,
            ),
            "price_spreads": [30.0, 40.0, 50.0, 35.0, 45.0],
        },
        {
            "name": "premium_nmc_system",
            "expected_lcos": 0.120,
            "expected_arbitrage": 75.0,
            "technology": BatteryTechnology.NMC,
            "capacity_kwh": 100.0,
            "operation_profile": OperationProfile(
                daily_cycles=1.5,
                seasonal_variation=0.25,
                capacity_factor=0.80,
                grid_services_revenue=0.0,
                energy_arbitrage_spread=60.0,
            ),
            "price_spreads": [50.0, 70.0, 90.0, 60.0, 80.0],
        },
        {
            "name": "large_scale_system",
            "expected_lcos": 0.060,
            "expected_arbitrage": 200.0,
            "technology": BatteryTechnology.LFP,
            "capacity_kwh": 500.0,
            "operation_profile": OperationProfile(
                daily_cycles=2.0,
                seasonal_variation=0.15,
                capacity_factor=0.90,
                grid_services_revenue=0.0,
                energy_arbitrage_spread=50.0,
            ),
            "price_spreads": [40.0, 55.0, 65.0, 45.0, 60.0],
        },
    ]


def _best_one_cycle_trade(prices: Sequence[float]) -> tuple[int, int, float]:
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


def _compute_forecast_value_metrics(
    actual_prices: Sequence[float], predicted_prices: Sequence[float]
) -> dict[str, float]:
    if len(actual_prices) != len(predicted_prices) or len(actual_prices) < 2:
        return {
            "benchmark_value_capture_ratio": 0.0,
            "benchmark_realized_spread_eur_mwh": 0.0,
            "benchmark_optimal_spread_eur_mwh": 0.0,
        }

    predicted_buy, predicted_sell, _ = _best_one_cycle_trade(predicted_prices)
    realized_spread = 0.0
    if predicted_sell > predicted_buy:
        realized_spread = max(
            float(actual_prices[predicted_sell] - actual_prices[predicted_buy]),
            0.0,
        )

    _, _, optimal_spread = _best_one_cycle_trade(actual_prices)
    if optimal_spread <= 0.0:
        value_capture_ratio = 1.0 if realized_spread <= 0.0 else 0.0
    else:
        value_capture_ratio = realized_spread / optimal_spread

    return {
        "benchmark_value_capture_ratio": float(value_capture_ratio),
        "benchmark_realized_spread_eur_mwh": float(realized_spread),
        "benchmark_optimal_spread_eur_mwh": float(optimal_spread),
    }


def _build_eval_only_scorecard(price_forecast: pl.DataFrame) -> pl.DataFrame:
    grouped_rows: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for row in price_forecast.to_dicts():
        model_name = str(row.get("model_name") or "unknown_model")
        model_family = str(row.get("model_family") or "unknown_family")
        forecast_horizon_hours = int(row.get("forecast_horizon_hours") or 0)
        grouped_rows.setdefault((model_name, model_family, forecast_horizon_hours), []).append(dict(row))

    if not grouped_rows:
        return pl.DataFrame(schema=FORECAST_VALUE_SCORECARD_SCHEMA)

    benchmark_rows = []
    benchmark_timestamp = datetime.now()
    for (model_name, model_family, forecast_horizon_hours), rows in grouped_rows.items():
        first_row = rows[0]
        evaluation_folds = int(first_row.get("evaluation_folds") or 0)
        if evaluation_folds <= 0:
            continue

        eval_rmse = float(first_row.get("eval_rmse") or 0.0)
        eval_mae = float(first_row.get("eval_mae") or 0.0)
        eval_value_capture_ratio = float(first_row.get("eval_value_capture_ratio") or 0.0)
        eval_realized_spread_eur_mwh = float(first_row.get("eval_realized_spread_eur_mwh") or 0.0)
        eval_optimal_spread_eur_mwh = float(first_row.get("eval_optimal_spread_eur_mwh") or 0.0)

        benchmark_rows.append(
            {
                "model_name": model_name,
                "model_family": model_family,
                "forecast_horizon_hours": forecast_horizon_hours,
                "forecast_rows": len(rows),
                "training_rows": int(first_row.get("training_rows") or 0),
                "evaluation_folds": evaluation_folds,
                "eval_rmse": eval_rmse,
                "eval_mae": eval_mae,
                "eval_value_capture_ratio": eval_value_capture_ratio,
                "eval_realized_spread_eur_mwh": eval_realized_spread_eur_mwh,
                "eval_optimal_spread_eur_mwh": eval_optimal_spread_eur_mwh,
                "benchmark_rmse": eval_rmse,
                "benchmark_mae": eval_mae,
                "benchmark_value_capture_ratio": eval_value_capture_ratio,
                "benchmark_realized_spread_eur_mwh": eval_realized_spread_eur_mwh,
                "benchmark_optimal_spread_eur_mwh": eval_optimal_spread_eur_mwh,
                "benchmark_window_start": min(row["forecast_timestamp"] for row in rows),
                "benchmark_window_end": max(row["forecast_timestamp"] for row in rows),
                "benchmark_timestamp": benchmark_timestamp,
            }
        )

    if not benchmark_rows:
        return pl.DataFrame(schema=FORECAST_VALUE_SCORECARD_SCHEMA)

    return pl.DataFrame(benchmark_rows, schema=FORECAST_VALUE_SCORECARD_SCHEMA)


def build_forecast_value_scorecard(
    market_data: pl.DataFrame, price_forecast: pl.DataFrame
) -> pl.DataFrame:
    if len(market_data) == 0 or len(price_forecast) == 0:
        return pl.DataFrame(schema=FORECAST_VALUE_SCORECARD_SCHEMA)

    actual_prices_by_timestamp = {
        row["forecast_timestamp"]: float(row["actual_price_eur_mwh"])
        for row in market_data.select(
            [
                pl.col("timestamp").alias("forecast_timestamp"),
                pl.col("price_eur_mwh").alias("actual_price_eur_mwh"),
            ]
        ).to_dicts()
    }

    grouped_rows: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for row in price_forecast.to_dicts():
        forecast_timestamp = row.get("forecast_timestamp")
        if forecast_timestamp not in actual_prices_by_timestamp:
            continue

        model_name = str(row.get("model_name") or "unknown_model")
        model_family = str(row.get("model_family") or "unknown_family")
        forecast_horizon_hours = int(row.get("forecast_horizon_hours") or 0)
        key = (model_name, model_family, forecast_horizon_hours)

        enriched_row = dict(row)
        enriched_row["actual_price_eur_mwh"] = actual_prices_by_timestamp[forecast_timestamp]
        grouped_rows.setdefault(key, []).append(enriched_row)

    if not grouped_rows:
        return _build_eval_only_scorecard(price_forecast)

    benchmark_rows = []
    benchmark_timestamp = datetime.now()
    for (model_name, model_family, forecast_horizon_hours), rows in grouped_rows.items():
        actual_prices = [float(row["actual_price_eur_mwh"]) for row in rows]
        predicted_prices = [float(row["predicted_price_eur_mwh"]) for row in rows]
        benchmark_rmse = sqrt(
            sum((actual - predicted) ** 2 for actual, predicted in zip(actual_prices, predicted_prices))
            / len(rows)
        )
        benchmark_mae = sum(
            abs(actual - predicted) for actual, predicted in zip(actual_prices, predicted_prices)
        ) / len(rows)
        value_metrics = _compute_forecast_value_metrics(actual_prices, predicted_prices)
        first_row = rows[0]

        benchmark_rows.append(
            {
                "model_name": model_name,
                "model_family": model_family,
                "forecast_horizon_hours": forecast_horizon_hours,
                "forecast_rows": len(rows),
                "training_rows": int(first_row.get("training_rows") or 0),
                "evaluation_folds": int(first_row.get("evaluation_folds") or 0),
                "eval_rmse": float(first_row.get("eval_rmse") or 0.0),
                "eval_mae": float(first_row.get("eval_mae") or 0.0),
                "eval_value_capture_ratio": float(first_row.get("eval_value_capture_ratio") or 0.0),
                "eval_realized_spread_eur_mwh": float(
                    first_row.get("eval_realized_spread_eur_mwh") or 0.0
                ),
                "eval_optimal_spread_eur_mwh": float(
                    first_row.get("eval_optimal_spread_eur_mwh") or 0.0
                ),
                "benchmark_rmse": float(benchmark_rmse),
                "benchmark_mae": float(benchmark_mae),
                **value_metrics,
                "benchmark_window_start": min(row["forecast_timestamp"] for row in rows),
                "benchmark_window_end": max(row["forecast_timestamp"] for row in rows),
                "benchmark_timestamp": benchmark_timestamp,
            }
        )

    return pl.DataFrame(benchmark_rows, schema=FORECAST_VALUE_SCORECARD_SCHEMA)


def log_engine_benchmark_run(
    row: dict[str, Any], tracking_module: Any | None = None
) -> dict[str, Any]:
    """Log one engine benchmark row to MLflow and return tracking metadata."""

    tracking_module = tracking_module or mlflow

    with tracking_module.start_run(run_name=f"{row['engine_name']}_size_{row['data_size']}"):
        tracking_module.log_param("engine_name", row["engine_name"])
        tracking_module.log_param("data_size", row["data_size"])
        tracking_module.log_metric("processing_time_seconds", row["processing_time_seconds"])
        tracking_module.log_metric("memory_peak_mb", row["memory_peak_mb"])
        tracking_module.log_metric(
            "throughput_records_per_second", row["throughput_records_per_second"]
        )
        tracking_module.set_tag("benchmark_type", "engine_performance")
        tracking_module.set_tag("success", str(row["success"]))

    return {
        "experiment_name": "engine_benchmarks",
        "run_name": f"{row['engine_name']}_size_{row['data_size']}",
        "engine_name": row["engine_name"],
        "data_size": row["data_size"],
        "metric_processing_time": row["processing_time_seconds"],
        "metric_memory_peak": row["memory_peak_mb"],
        "metric_throughput": row["throughput_records_per_second"],
        "param_success": row["success"],
        "tag_benchmark_type": "engine_performance",
        "timestamp": row["benchmark_timestamp"],
    }


def log_accuracy_benchmark_run(
    row: dict[str, Any], tracking_module: Any | None = None
) -> dict[str, Any] | None:
    """Log one accuracy benchmark row to MLflow and return tracking metadata."""

    if not row["success"]:
        return None

    tracking_module = tracking_module or mlflow

    with tracking_module.start_run(run_name=f"{row['scenario_name']}_{row['metric_type']}"):
        tracking_module.log_param("scenario_name", row["scenario_name"])
        tracking_module.log_param("metric_type", row["metric_type"])
        tracking_module.log_param("expected_value", row["expected_value"])
        tracking_module.log_metric("absolute_error", row["absolute_error"])
        tracking_module.log_metric("relative_error_percent", row["relative_error_percent"])
        tracking_module.set_tag("benchmark_type", "accuracy_validation")
        tracking_module.set_tag("success", str(row["success"]))

    return {
        "experiment_name": "accuracy_benchmarks",
        "run_name": f"{row['scenario_name']}_{row['metric_type']}",
        "scenario_name": row["scenario_name"],
        "metric_type": row["metric_type"],
        "metric_relative_error": row["relative_error_percent"],
        "metric_absolute_error": row["absolute_error"],
        "param_expected_value": row["expected_value"],
        "param_calculated_value": row["calculated_value"],
        "tag_benchmark_type": "accuracy_validation",
        "timestamp": row["benchmark_timestamp"],
    }


def log_forecast_benchmark_run(
    row: dict[str, Any], tracking_module: Any | None = None
) -> dict[str, Any]:
    """Log one forecast benchmark row to MLflow and return tracking metadata."""

    tracking_module = tracking_module or mlflow

    with tracking_module.start_run(run_name=f"forecast_value_{row['model_name']}"):
        tracking_module.log_param("model_name", row["model_name"])
        tracking_module.log_param("model_family", row["model_family"])
        tracking_module.log_param("forecast_horizon_hours", row["forecast_horizon_hours"])
        tracking_module.log_param("forecast_rows", row["forecast_rows"])
        tracking_module.log_metric("benchmark_rmse", row["benchmark_rmse"])
        tracking_module.log_metric("benchmark_mae", row["benchmark_mae"])
        tracking_module.log_metric(
            "benchmark_value_capture_ratio", row["benchmark_value_capture_ratio"]
        )
        tracking_module.log_metric("eval_rmse", row["eval_rmse"])
        tracking_module.log_metric("eval_mae", row["eval_mae"])
        tracking_module.log_metric("eval_value_capture_ratio", row["eval_value_capture_ratio"])
        tracking_module.set_tag("benchmark_type", "forecast_value")

    return {
        "experiment_name": "forecast_value_benchmarks",
        "run_name": f"forecast_value_{row['model_name']}",
        "model_name": row["model_name"],
        "model_family": row["model_family"],
        "forecast_horizon_hours": row["forecast_horizon_hours"],
        "forecast_rows": row["forecast_rows"],
        "metric_benchmark_rmse": row["benchmark_rmse"],
        "metric_benchmark_mae": row["benchmark_mae"],
        "metric_benchmark_value_capture_ratio": row["benchmark_value_capture_ratio"],
        "metric_eval_rmse": row["eval_rmse"],
        "metric_eval_mae": row["eval_mae"],
        "metric_eval_value_capture_ratio": row["eval_value_capture_ratio"],
        "tag_benchmark_type": "forecast_value",
        "timestamp": row["benchmark_timestamp"],
    }
from datetime import datetime, timedelta

import numpy as np
import polars as pl

from src.data_pipeline.price_forecast_features import (
    _build_feature_frame,
    _build_persistence_forecast,
    _compute_eval_metrics,
    _compute_value_capture_metrics,
    _run_walk_forward_evaluation,
)


class _FakeModel:
    def predict(self, rows):
        return [50.0 for _ in range(len(rows))]


class _WalkForwardFakeModel:
    def __init__(self) -> None:
        self.mean_target = 0.0

    def fit(self, rows, targets) -> None:
        self.mean_target = float(np.mean(targets))

    def predict(self, rows):
        return [self.mean_target for _ in range(len(rows))]


def test_build_persistence_forecast_preserves_expected_contract() -> None:
    timestamps = [datetime(2026, 3, 1, 0, 0) + timedelta(hours=hour) for hour in range(30)]
    market_data = pl.DataFrame({"timestamp": timestamps, "price_eur_mwh": [40.0 + hour for hour in range(30)]})

    result = _build_persistence_forecast(market_data, labeled_rows=7)

    assert len(result) == 24
    assert set(result["model_name"].unique().to_list()) == {"persistence_fallback"}
    assert set(result["model_family"].unique().to_list()) == {"persistence"}
    assert set(result["forecast_horizon_hours"].unique().to_list()) == {24}
    assert set(result["training_rows"].unique().to_list()) == {7}


def test_compute_eval_metrics_returns_expected_values() -> None:
    eval_df = pl.DataFrame(
        {
            "hour": [0, 1],
            "weekday": [0, 0],
            "month": [3, 3],
            "day_of_year": [60, 60],
            "is_weekend": [0, 0],
            "lag_1h": [48.0, 49.0],
            "lag_24h": [30.0, 31.0],
            "roll_mean_24h": [40.0, 41.0],
            "roll_std_24h": [5.0, 5.0],
            "target_price_t_plus_24h": [55.0, 45.0],
        }
    )

    rmse, mae, residual_std = _compute_eval_metrics(
        _FakeModel(),
        eval_df,
        ["hour", "weekday", "month", "day_of_year", "is_weekend", "lag_1h", "lag_24h", "roll_mean_24h", "roll_std_24h"],
    )

    assert rmse == 5.0
    assert mae == 5.0
    assert residual_std == 5.0


def test_compute_value_capture_metrics_returns_proxy_arbitrage_value() -> None:
    metrics = _compute_value_capture_metrics(
        np.array([50.0, 20.0, 70.0, 65.0]),
        np.array([10.0, 15.0, 5.0, 40.0]),
    )

    assert metrics["realized_spread_eur_mwh"] == 0.0
    assert metrics["optimal_spread_eur_mwh"] == 50.0
    assert metrics["value_capture_ratio"] == 0.0


def test_run_walk_forward_evaluation_reports_error_and_value_metrics() -> None:
    timestamps = [datetime(2026, 3, 1, 0, 0) + timedelta(hours=hour) for hour in range(120)]
    prices = [45.0 + float(hour % 24) for hour in range(120)]
    market_data = pl.DataFrame({"timestamp": timestamps, "price_eur_mwh": prices})
    labeled = _build_feature_frame(market_data).drop_nulls(
        [
            "lag_1h",
            "lag_24h",
            "roll_mean_24h",
            "roll_std_24h",
            "target_price_t_plus_24h",
        ]
    )
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

    metrics = _run_walk_forward_evaluation(
        labeled,
        feature_cols,
        _WalkForwardFakeModel,
        min_train_size=48,
        eval_size=24,
        step_size=24,
    )

    assert metrics["fold_count"] == 1.0
    assert metrics["eval_rmse"] >= 0.0
    assert metrics["eval_mae"] >= 0.0
    assert metrics["residual_std"] >= 0.0
    assert 0.0 <= metrics["value_capture_ratio"] <= 1.0
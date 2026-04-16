from datetime import datetime, timedelta

import polars as pl

from src.data_pipeline.price_forecast_features import (
    _build_persistence_forecast,
    _compute_eval_metrics,
)


class _FakeModel:
    def predict(self, rows):
        return [50.0 for _ in range(len(rows))]


def test_build_persistence_forecast_preserves_expected_contract() -> None:
    timestamps = [datetime(2026, 3, 1, 0, 0) + timedelta(hours=hour) for hour in range(30)]
    market_data = pl.DataFrame({"timestamp": timestamps, "price_eur_mwh": [40.0 + hour for hour in range(30)]})

    result = _build_persistence_forecast(market_data, labeled_rows=7)

    assert len(result) == 24
    assert set(result["model_name"].unique().to_list()) == {"persistence_fallback"}
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
from __future__ import annotations

import importlib.util
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(module_name: str, relative_path: str, injected_modules: dict[str, object] | None = None):
    module_path = REPO_ROOT / relative_path
    injected_modules = injected_modules or {}
    previous = {}

    for name, module in injected_modules.items():
        previous[name] = sys.modules.get(name)
        sys.modules[name] = module

    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        for name, old in previous.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old


def build_dagster_module():
    module = types.ModuleType("dagster")
    module.asset = lambda *args, **kwargs: (lambda func: func)
    module.AssetIn = lambda asset_key: {"asset_key": asset_key}
    return module


def build_mlflow_module():
    module = types.ModuleType("mlflow")
    module.set_tracking_uri = lambda uri: None

    class RunContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    module.start_run = lambda run_name=None: RunContext()
    module.log_param = lambda name, value: None
    module.log_metric = lambda name, value: None
    module.set_tag = lambda name, value: None
    return module


def test_build_forecast_value_scorecard_computes_realized_metrics() -> None:
    helper_module = load_module(
        "src.data_pipeline.benchmark_helpers_under_test",
        "src/data_pipeline/benchmark_helpers.py",
        injected_modules={"mlflow": build_mlflow_module()},
    )

    start = datetime(2026, 3, 1, 0, 0)
    timestamps = [start + timedelta(hours=hour) for hour in range(4)]
    market_data = pl.DataFrame(
        {
            "timestamp": timestamps,
            "price_eur_mwh": [50.0, 20.0, 70.0, 65.0],
        }
    )
    price_forecast = pl.DataFrame(
        {
            "forecast_timestamp": timestamps,
            "predicted_price_eur_mwh": [50.0, 20.0, 70.0, 65.0],
            "model_name": ["random_forest_dam_24h"] * 4,
            "model_family": ["random_forest_regressor"] * 4,
            "forecast_horizon_hours": [24] * 4,
            "training_rows": [72] * 4,
            "evaluation_folds": [2] * 4,
            "eval_rmse": [4.2] * 4,
            "eval_mae": [3.1] * 4,
            "eval_value_capture_ratio": [0.75] * 4,
            "eval_realized_spread_eur_mwh": [37.5] * 4,
            "eval_optimal_spread_eur_mwh": [50.0] * 4,
        }
    )

    scorecard = helper_module.build_forecast_value_scorecard(market_data, price_forecast)

    assert len(scorecard) == 1
    row = scorecard.to_dicts()[0]
    assert row["model_name"] == "random_forest_dam_24h"
    assert row["forecast_rows"] == 4
    assert row["benchmark_rmse"] == 0.0
    assert row["benchmark_mae"] == 0.0
    assert row["benchmark_realized_spread_eur_mwh"] == 50.0
    assert row["benchmark_optimal_spread_eur_mwh"] == 50.0
    assert row["benchmark_value_capture_ratio"] == 1.0
    assert row["eval_value_capture_ratio"] == 0.75


def test_forecast_value_benchmark_asset_builds_scorecard() -> None:
    module = load_module(
        "src.assets.benchmarks.performance_forecast_under_test",
        "src/assets/benchmarks/performance.py",
        injected_modules={
            "dagster": build_dagster_module(),
            "mlflow": build_mlflow_module(),
        },
    )

    start = datetime(2026, 3, 1, 0, 0)
    timestamps = [start + timedelta(hours=hour) for hour in range(4)]
    market_data = pl.DataFrame(
        {
            "timestamp": timestamps,
            "price_eur_mwh": [50.0, 20.0, 70.0, 65.0],
        }
    )
    price_forecast = pl.DataFrame(
        {
            "forecast_timestamp": timestamps,
            "predicted_price_eur_mwh": [48.0, 22.0, 66.0, 67.0],
            "model_name": ["demo_model"] * 4,
            "model_family": ["demo_family"] * 4,
            "forecast_horizon_hours": [24] * 4,
            "training_rows": [72] * 4,
            "evaluation_folds": [1] * 4,
            "eval_rmse": [5.0] * 4,
            "eval_mae": [4.0] * 4,
            "eval_value_capture_ratio": [0.6] * 4,
            "eval_realized_spread_eur_mwh": [30.0] * 4,
            "eval_optimal_spread_eur_mwh": [50.0] * 4,
        }
    )

    result = module.forecast_value_benchmark_asset(market_data, price_forecast)

    assert len(result) == 1
    row = result.to_dicts()[0]
    assert row["model_name"] == "demo_model"
    assert row["benchmark_rmse"] > 0.0
    assert 0.0 <= row["benchmark_value_capture_ratio"] <= 1.0
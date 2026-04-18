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
            "uncertainty_source": ["walk_forward_residual_std"] * 4,
            "uncertainty_spread_eur_mwh": [6.0, 8.0, 10.0, 12.0],
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
    assert row["benchmark_uncertainty_source"] == "walk_forward_residual_std"
    assert row["benchmark_avg_uncertainty_spread_eur_mwh"] == 9.0
    assert row["benchmark_max_uncertainty_spread_eur_mwh"] == 12.0
    assert row["benchmark_candidate_status"] == "validated"
    assert row["benchmark_candidate_ready"] is True
    assert row["benchmark_candidate_rank"] == 1
    assert row["benchmark_incumbent_baseline"] is True
    assert row["promotion_eligible"] is True
    assert row["promotion_decision"] == "promoted"
    assert row["promotion_decision_reason"] == "incumbent_baseline_retained"
    assert row["promotion_gate_version"] == "forecast_value_scorecard_v1"


def test_build_forecast_value_scorecard_falls_back_to_eval_metrics_without_actual_overlap() -> None:
    helper_module = load_module(
        "src.data_pipeline.benchmark_helpers_eval_fallback_under_test",
        "src/data_pipeline/benchmark_helpers.py",
        injected_modules={"mlflow": build_mlflow_module()},
    )

    start = datetime(2026, 3, 1, 0, 0)
    market_timestamps = [start + timedelta(hours=hour) for hour in range(48)]
    forecast_timestamps = [start + timedelta(hours=48 + hour) for hour in range(24)]
    market_data = pl.DataFrame(
        {
            "timestamp": market_timestamps,
            "price_eur_mwh": [50.0 + float(hour % 6) for hour in range(48)],
        }
    )
    price_forecast = pl.DataFrame(
        {
            "forecast_timestamp": forecast_timestamps,
            "predicted_price_eur_mwh": [48.0 + float(hour % 4) for hour in range(24)],
            "model_name": ["random_forest_dam_24h"] * 24,
            "model_family": ["random_forest_regressor"] * 24,
            "forecast_horizon_hours": [24] * 24,
            "training_rows": [96] * 24,
            "evaluation_folds": [3] * 24,
            "eval_rmse": [4.2] * 24,
            "eval_mae": [3.1] * 24,
            "eval_value_capture_ratio": [0.75] * 24,
            "eval_realized_spread_eur_mwh": [37.5] * 24,
            "eval_optimal_spread_eur_mwh": [50.0] * 24,
            "uncertainty_source": ["eval_rmse_floor"] * 24,
            "uncertainty_spread_eur_mwh": [5.0] * 24,
        }
    )

    scorecard = helper_module.build_forecast_value_scorecard(market_data, price_forecast)

    assert len(scorecard) == 1
    row = scorecard.to_dicts()[0]
    assert row["model_name"] == "random_forest_dam_24h"
    assert row["benchmark_rmse"] == 4.2
    assert row["benchmark_mae"] == 3.1
    assert row["benchmark_value_capture_ratio"] == 0.75
    assert row["evaluation_folds"] == 3
    assert row["benchmark_uncertainty_source"] == "eval_rmse_floor"
    assert row["benchmark_avg_uncertainty_spread_eur_mwh"] == 5.0
    assert row["benchmark_max_uncertainty_spread_eur_mwh"] == 5.0
    assert row["benchmark_candidate_status"] == "validated"
    assert row["promotion_decision"] == "promoted"
    assert row["promotion_gate_version"] == "forecast_value_scorecard_v1"


def test_build_forecast_value_scorecard_keeps_empty_result_without_evaluated_folds() -> None:
    helper_module = load_module(
        "src.data_pipeline.benchmark_helpers_empty_eval_fallback_under_test",
        "src/data_pipeline/benchmark_helpers.py",
        injected_modules={"mlflow": build_mlflow_module()},
    )

    start = datetime(2026, 3, 1, 0, 0)
    market_timestamps = [start + timedelta(hours=hour) for hour in range(48)]
    forecast_timestamps = [start + timedelta(hours=48 + hour) for hour in range(24)]
    market_data = pl.DataFrame(
        {
            "timestamp": market_timestamps,
            "price_eur_mwh": [50.0 + float(hour % 6) for hour in range(48)],
        }
    )
    price_forecast = pl.DataFrame(
        {
            "forecast_timestamp": forecast_timestamps,
            "predicted_price_eur_mwh": [48.0 + float(hour % 4) for hour in range(24)],
            "model_name": ["persistence_fallback"] * 24,
            "model_family": ["persistence"] * 24,
            "forecast_horizon_hours": [24] * 24,
            "training_rows": [0] * 24,
            "evaluation_folds": [0] * 24,
            "eval_rmse": [0.0] * 24,
            "eval_mae": [0.0] * 24,
            "eval_value_capture_ratio": [0.0] * 24,
            "eval_realized_spread_eur_mwh": [0.0] * 24,
            "eval_optimal_spread_eur_mwh": [0.0] * 24,
        }
    )

    scorecard = helper_module.build_forecast_value_scorecard(market_data, price_forecast)

    assert len(scorecard) == 0


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
            "scenario_low_price_eur_mwh": [44.0, 28.0, 61.0, 60.0],
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
            "uncertainty_source": ["walk_forward_residual_std"] * 4,
            "uncertainty_spread_eur_mwh": [7.0, 7.0, 7.0, 7.0],
        }
    )
    module.write_promoted_forecast_model_metadata = lambda metadata: metadata

    result = module.forecast_value_benchmark_asset(market_data, price_forecast)

    assert len(result) >= 1
    rows_by_model = {row["model_name"]: row for row in result.to_dicts()}
    row = rows_by_model["demo_model"]
    assert row["model_name"] == "demo_model"
    assert row["benchmark_rmse"] > 0.0
    assert 0.0 <= row["benchmark_value_capture_ratio"] <= 1.0
    assert row["benchmark_dispatch_comparison_mode"] == "point_vs_conservative"
    assert row["benchmark_conservative_dispatch_source"] == "scenario_low_price_eur_mwh"
    assert 0.0 <= row["benchmark_conservative_value_capture_ratio"] <= 1.0
    assert row["benchmark_uncertainty_source"] == "walk_forward_residual_std"
    assert row["benchmark_avg_uncertainty_spread_eur_mwh"] == 7.0
    assert row["benchmark_candidate_status"] == "untracked"
    assert row["benchmark_candidate_ready"] is False
    assert row["benchmark_candidate_skip_reason"] == "model_not_in_registry"
    assert row["promotion_decision"] == "not_promoted"
    assert row["promotion_gate_version"] == "forecast_value_scorecard_v1"
    assert "skipped" in set(result["benchmark_candidate_status"].to_list())


def test_forecast_value_benchmark_asset_appends_registry_candidates(monkeypatch) -> None:
    module = load_module(
        "src.assets.benchmarks.performance_multi_candidate_under_test",
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

    monkeypatch.setattr(
        module,
        "list_forecast_model_specs",
        lambda: [types.SimpleNamespace(model_name="demo_model"), types.SimpleNamespace(model_name="alt_model")],
    )
    monkeypatch.setattr(
        module,
        "_build_forecast_with_model_spec",
        lambda market_df, model_spec: pl.DataFrame(
            {
                "forecast_timestamp": market_df["timestamp"],
                "predicted_price_eur_mwh": [52.0, 18.0, 74.0, 60.0],
                "model_name": [model_spec.model_name] * len(market_df),
                "model_family": ["alt_family"] * len(market_df),
                "forecast_horizon_hours": [24] * len(market_df),
                "training_rows": [96] * len(market_df),
                "evaluation_folds": [2] * len(market_df),
                "eval_rmse": [3.0] * len(market_df),
                "eval_mae": [2.0] * len(market_df),
                "eval_value_capture_ratio": [0.8] * len(market_df),
                "eval_realized_spread_eur_mwh": [40.0] * len(market_df),
                "eval_optimal_spread_eur_mwh": [50.0] * len(market_df),
            }
        ),
    )
    monkeypatch.setattr(
        module,
        "write_promoted_forecast_model_metadata",
        lambda metadata: metadata,
    )

    result = module.forecast_value_benchmark_asset(market_data, price_forecast)

    assert len(result) == 2
    assert set(result["model_name"].to_list()) == {"demo_model", "alt_model"}
    rows_by_model = {row["model_name"]: row for row in result.to_dicts()}
    assert rows_by_model["alt_model"]["benchmark_candidate_status"] == "validated"
    assert rows_by_model["alt_model"]["promotion_decision"] == "promoted"
    assert rows_by_model["demo_model"]["promotion_decision"] == "not_promoted"


def test_forecast_value_benchmark_asset_skips_unavailable_optional_candidates(monkeypatch) -> None:
    module = load_module(
        "src.assets.benchmarks.performance_optional_candidate_under_test",
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

    monkeypatch.setattr(
        module,
        "list_forecast_model_specs",
        lambda: [types.SimpleNamespace(model_name="demo_model"), types.SimpleNamespace(model_name="nbeatsx_dam_24h")],
    )
    monkeypatch.setattr(
        module,
        "_build_forecast_with_model_spec",
        lambda market_df, model_spec: (_ for _ in ()).throw(ModuleNotFoundError("missing neuralforecast")),
    )
    monkeypatch.setattr(
        module,
        "write_promoted_forecast_model_metadata",
        lambda metadata: metadata,
    )

    result = module.forecast_value_benchmark_asset(market_data, price_forecast)

    assert len(result) == 2
    rows_by_model = {row["model_name"]: row for row in result.to_dicts()}
    assert set(rows_by_model) == {"demo_model", "nbeatsx_dam_24h"}
    assert rows_by_model["demo_model"]["benchmark_candidate_status"] == "validated"
    assert rows_by_model["nbeatsx_dam_24h"]["benchmark_candidate_status"] == "skipped"
    assert rows_by_model["nbeatsx_dam_24h"]["promotion_decision"] == "skipped"
    assert "neuralforecast" in rows_by_model["nbeatsx_dam_24h"]["benchmark_candidate_skip_reason"]


def test_forecast_value_benchmark_asset_persists_promoted_winner(monkeypatch) -> None:
    module = load_module(
        "src.assets.benchmarks.performance_promotion_under_test",
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
            "scenario_low_price_eur_mwh": [44.0, 28.0, 61.0, 60.0],
            "model_name": ["random_forest_dam_24h"] * 4,
            "model_family": ["random_forest_regressor"] * 4,
            "forecast_horizon_hours": [24] * 4,
            "training_rows": [72] * 4,
            "evaluation_folds": [1] * 4,
            "eval_rmse": [5.0] * 4,
            "eval_mae": [4.0] * 4,
            "eval_value_capture_ratio": [0.6] * 4,
            "eval_realized_spread_eur_mwh": [30.0] * 4,
            "eval_optimal_spread_eur_mwh": [50.0] * 4,
            "uncertainty_source": ["walk_forward_residual_std"] * 4,
            "uncertainty_spread_eur_mwh": [6.0, 8.0, 10.0, 12.0],
        }
    )
    captured_metadata = {}

    monkeypatch.setattr(
        module,
        "write_promoted_forecast_model_metadata",
        lambda metadata: captured_metadata.setdefault("value", dict(metadata)),
    )

    result = module.forecast_value_benchmark_asset(market_data, price_forecast)

    assert len(result) >= 1
    assert "skipped" in set(result["benchmark_candidate_status"].to_list())
    assert captured_metadata["value"]["model_name"] == "random_forest_dam_24h"
    assert captured_metadata["value"]["promotion_source"] == "forecast_value_benchmark_asset"
    assert captured_metadata["value"]["benchmark_dispatch_comparison_mode"] == "point_vs_conservative"
    assert captured_metadata["value"]["benchmark_conservative_dispatch_source"] == "scenario_low_price_eur_mwh"
    assert captured_metadata["value"]["benchmark_uncertainty_source"] == "walk_forward_residual_std"
    assert captured_metadata["value"]["benchmark_avg_uncertainty_spread_eur_mwh"] == 9.0
    assert captured_metadata["value"]["benchmark_max_uncertainty_spread_eur_mwh"] == 12.0
    assert captured_metadata["value"]["benchmark_candidate_status"] == "validated"
    assert captured_metadata["value"]["promotion_eligible"] is True
    assert captured_metadata["value"]["promotion_decision"] == "promoted"
    assert captured_metadata["value"]["promotion_gate_version"] == "forecast_value_scorecard_v1"
    assert captured_metadata["value"]["model_ready"] is True


def test_log_forecast_benchmark_run_preserves_uncertainty_summaries() -> None:
    helper_module = load_module(
        "src.data_pipeline.benchmark_helpers_mlflow_uncertainty_under_test",
        "src/data_pipeline/benchmark_helpers.py",
        injected_modules={"mlflow": build_mlflow_module()},
    )

    row = {
        "model_name": "random_forest_dam_24h",
        "model_family": "random_forest_regressor",
        "forecast_horizon_hours": 24,
        "forecast_rows": 24,
        "benchmark_rmse": 4.0,
        "benchmark_mae": 3.0,
        "benchmark_value_capture_ratio": 0.8,
        "benchmark_dispatch_comparison_mode": "point_vs_conservative",
        "benchmark_conservative_dispatch_source": "scenario_low_price_eur_mwh",
        "benchmark_conservative_value_capture_ratio": 0.72,
        "benchmark_point_vs_conservative_value_capture_delta": -0.08,
        "benchmark_uncertainty_source": "walk_forward_residual_std",
        "benchmark_avg_uncertainty_spread_eur_mwh": 9.0,
        "benchmark_max_uncertainty_spread_eur_mwh": 12.0,
        "benchmark_candidate_status": "validated",
        "benchmark_candidate_ready": True,
        "benchmark_candidate_skip_reason": None,
        "promotion_eligible": True,
        "promotion_decision": "promoted",
        "promotion_decision_reason": "incumbent_baseline_retained",
        "promotion_gate_version": "forecast_value_scorecard_v1",
        "eval_rmse": 4.2,
        "eval_mae": 3.1,
        "eval_value_capture_ratio": 0.75,
        "benchmark_timestamp": datetime(2026, 3, 6, 12, 0, 0),
    }

    log_row = helper_module.log_forecast_benchmark_run(row, tracking_module=build_mlflow_module())

    assert log_row["run_name"] == "forecast_value_random_forest_dam_24h"
    assert log_row["param_benchmark_candidate_status"] == "validated"
    assert log_row["param_promotion_decision"] == "promoted"
    assert log_row["param_promotion_gate_version"] == "forecast_value_scorecard_v1"
    assert log_row["param_promotion_eligible"] is True
    assert log_row["param_benchmark_uncertainty_source"] == "walk_forward_residual_std"
    assert log_row["param_benchmark_dispatch_comparison_mode"] == "point_vs_conservative"
    assert log_row["param_benchmark_conservative_dispatch_source"] == "scenario_low_price_eur_mwh"
    assert log_row["metric_benchmark_avg_uncertainty_spread_eur_mwh"] == 9.0
    assert log_row["metric_benchmark_max_uncertainty_spread_eur_mwh"] == 12.0
    assert log_row["metric_benchmark_conservative_value_capture_ratio"] == 0.72
    assert log_row["metric_benchmark_point_vs_conservative_value_capture_delta"] == -0.08
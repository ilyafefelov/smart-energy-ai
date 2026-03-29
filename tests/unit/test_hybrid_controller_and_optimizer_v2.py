from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_hybrid_controller_forecasting_and_strategy_flow(monkeypatch) -> None:
    module = load_module("hybrid_ml_controller_under_test", "src/hybrid_ml_controller.py")
    monkeypatch.setattr(pd.DataFrame, "clone", pd.DataFrame.copy, raising=False)

    forecaster = module.PatternBasedForecaster(module.ForecastConfig())
    first_day = pd.DataFrame({"hour": list(range(24)), "price_eur_mwh": [50.0 + hour for hour in range(24)]})
    second_day = pd.DataFrame({"hour": list(range(24)), "price_eur_mwh": [60.0 + hour for hour in range(24)]})
    forecaster.add_historical_data(first_day)
    forecaster.add_historical_data(second_day)

    patterns = forecaster.extract_patterns()
    forecast, confidence = forecaster.forecast_prices(10, {"solar_forecast": [100.0] * 24})

    assert patterns["daily_patterns_extracted"] == 24
    assert len(forecast) == 24
    assert len(confidence) == 24

    optimizer = module.MILPOptimizer(module.OptimizationConfig())
    schedule = optimizer.optimize_schedule(forecast, 0.5, module.np.full(24, 50.0))
    assert len(schedule["schedule"]) == 24
    assert schedule["optimization_method"] == "greedy_milp_placeholder"

    controller = module.create_hybrid_controller()
    controller.update_with_new_prices(first_day)
    controller.update_with_new_prices(second_day)
    strategy = controller.generate_optimal_strategy({"hour": 14, "soc": 0.6}, {"solar_forecast": [100.0] * 24})

    assert strategy["strategy_type"] == "hybrid_ml"
    assert len(strategy["optimal_schedule"]["schedule"]) == 24
    assert controller.get_current_action(0) in {"BUY_FROM_GRID", "CHARGE_FROM_GRID", "DISCHARGE_BATTERY"}
    assert controller.get_current_action(99) in {"BUY_FROM_GRID", "CHARGE_FROM_GRID", "DISCHARGE_BATTERY"}


def test_optimizer_v2_generates_scenario_outputs(monkeypatch, tmp_path) -> None:
    module = load_module("optimizer_v2_under_test", "src/optimizer_v2.py")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module.np.random, "normal", lambda mean, std=None: 0.0)

    normal = module.run_optimized_scenario("Normal")
    winter = module.run_optimized_scenario("Winter")
    blackout = module.run_optimized_scenario("Blackout")

    assert len(normal) == 24
    assert len(winter) == 24
    assert len(blackout) == 24
    assert (tmp_path / "projects" / "smart-energy-ai" / "data" / "processed" / "opt_normal.csv").exists()
    assert blackout["Action"].str.contains("OFF-GRID").any()
    assert winter["Solar"].max() < normal["Solar"].max()
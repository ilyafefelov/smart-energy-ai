from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _build_pipeline_asset_modules() -> dict[str, object]:
    energy_ml_pkg = types.ModuleType("energy_ml")
    energy_ml_pkg.__path__ = [str(ROOT / "energy_ml")]
    assets_pkg = types.ModuleType("energy_ml.assets")
    assets_pkg.__path__ = [str(ROOT / "energy_ml" / "assets")]

    dagster_mod = types.ModuleType("dagster")

    def asset(*args, **kwargs):
        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return args[0]

        def decorator(func):
            return func

        return decorator

    class AssetIn:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    dagster_mod.asset = asset
    dagster_mod.AssetIn = AssetIn

    polars_mod = types.ModuleType("polars")

    class DataFrame:
        def __init__(self, rows=None):
            self.rows = rows or {}
            self.columns = list(self.rows.keys()) if isinstance(self.rows, dict) else []
            self.shape = (1, len(self.columns)) if self.columns else (0, 0)

    polars_mod.DataFrame = DataFrame

    pipeline_mod = types.ModuleType("energy_ml.pipeline")

    class PipelineOrchestrator:
        def __init__(self, config=None):
            self.config = config

        def validate_all_inputs(self):
            return True, []

        def calculate_recommendation(self, config):
            return {
                "action": "HOLD",
                "reasoning": "stub",
                "confidence": 0.0,
                "estimated_savings": 0.0,
                "battery_impact": 0.0,
                "timestamp": "2026-04-13T00:00:00",
                "details": {},
            }

    pipeline_mod.PipelineOrchestrator = PipelineOrchestrator

    features_mod = types.ModuleType("energy_ml.features")

    class FeatureEngineer:
        def extract_features(self, orchestrator):
            return DataFrame({"feature": [0.0]})

    features_mod.FeatureEngineer = FeatureEngineer

    ml_integration_mod = types.ModuleType("energy_ml.ml_integration")

    class PredictionService:
        def predict(self, engineered_features):
            return {
                "action": "HOLD",
                "confidence": 0.0,
                "reasoning": "stub",
                "model_version": "stub",
                "feature_importance": {},
                "timestamp": "2026-04-13T00:00:00",
            }

    ml_integration_mod.PredictionService = PredictionService

    user_config_mod = types.ModuleType("energy_ml.user_config")

    class ConfigLoadResult:
        def __init__(self, success: bool, config=None, errors=None):
            self.success = success
            self.config = config
            self.errors = errors or []

    class ConfigurationManager:
        def resolve_config(self, user_config_data):
            return ConfigLoadResult(False, None, ["stub failure"])

    user_config_mod.UserConfigModel = object
    user_config_mod.ConfigurationManager = ConfigurationManager
    user_config_mod.UserConfigPayload = dict
    user_config_mod.ConfigLoadResult = ConfigLoadResult

    optimization_mod = types.ModuleType("energy_ml.mlops.optimization_engine")

    class OptimizationEngine:
        def get_user_strategy(self, config):
            return {"weights": {}, "constraints": {}}

        def optimize_decision(self, base_prediction, strategy, physics_data=None, renewable_data=None, weights=None):
            return base_prediction

    optimization_mod.OptimizationEngine = OptimizationEngine

    battery_physics_mod = types.ModuleType("energy_ml.mlops.battery_physics")

    class BatteryPhysicsEngine:
        def simulate_battery_behavior(self, config):
            return {}

        def apply_physics_constraints(self, optimized_prediction, battery_physics_simulation):
            return optimized_prediction

    battery_physics_mod.BatteryPhysicsEngine = BatteryPhysicsEngine

    renewable_mod = types.ModuleType("energy_ml.mlops.renewable_forecasting")

    class RenewableForecaster:
        def generate_forecasts(self, config):
            return {}

        def integrate_with_prediction(self, prediction, renewable_generation_forecast):
            return prediction

    renewable_mod.RenewableForecaster = RenewableForecaster

    return {
        "energy_ml": energy_ml_pkg,
        "energy_ml.assets": assets_pkg,
        "dagster": dagster_mod,
        "polars": polars_mod,
        "energy_ml.pipeline": pipeline_mod,
        "energy_ml.features": features_mod,
        "energy_ml.ml_integration": ml_integration_mod,
        "energy_ml.user_config": user_config_mod,
        "energy_ml.mlops.optimization_engine": optimization_mod,
        "energy_ml.mlops.battery_physics": battery_physics_mod,
        "energy_ml.mlops.renewable_forecasting": renewable_mod,
    }


def _load_pipeline_asset_module():
    module_path = ROOT / "energy_ml" / "assets" / "pipeline.py"
    module_name = "energy_ml.assets.pipeline_under_test"
    injected_modules = _build_pipeline_asset_modules()
    previous: dict[str, object | None] = {}

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
        sys.modules.pop(module_name, None)
        for name, old in previous.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old


def test_optimization_preferences_asset_returns_enveloped_config_error() -> None:
    module = _load_pipeline_asset_module()

    result = module.optimization_preferences_asset(user_config_data={})

    assert result["status"] == "error"
    assert result["strategy"] == "balanced"
    assert result["error"] == "stub failure"
    assert "timestamp" in result
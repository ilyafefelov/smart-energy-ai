import importlib.util
import json
import sys
import types
from pathlib import Path

import polars as pl


ROOT = Path(__file__).resolve().parents[2]


def _ensure_energy_ml_package() -> types.ModuleType:
    package = sys.modules.get("energy_ml")
    if package is None:
        package = types.ModuleType("energy_ml")
        package.__path__ = [str(ROOT / "energy_ml")]
        sys.modules["energy_ml"] = package
    return package


def _load_module(module_name: str, relative_path: str, injected_modules: dict[str, types.ModuleType] | None = None):
    _ensure_energy_ml_package()
    module_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    previous_modules: dict[str, types.ModuleType | None] = {}
    for name, injected in (injected_modules or {}).items():
        previous_modules[name] = sys.modules.get(name)
        sys.modules[name] = injected
    try:
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    finally:
        for name, previous in previous_modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    return module


ML_INTEGRATION = _load_module("energy_ml.ml_integration", "energy_ml/ml_integration.py")
FEATURE_STORE = _load_module("energy_ml.mlops.feature_store", "energy_ml/mlops/feature_store.py")


def _load_ml_integration_api_module():
    _ensure_energy_ml_package()

    pipeline_module = types.ModuleType("energy_ml.pipeline")
    user_config_module = types.ModuleType("energy_ml.user_config")
    optimization_module = types.ModuleType("energy_ml.mlops.optimization_engine")
    battery_module = types.ModuleType("energy_ml.mlops.battery_physics")
    renewable_module = types.ModuleType("energy_ml.mlops.renewable_forecasting")
    mlops_package = types.ModuleType("energy_ml.mlops")
    mlops_package.__path__ = [str(ROOT / "energy_ml" / "mlops")]

    class FakeConfig:
        def __init__(self):
            self.optimization_strategy = "balanced"
            self.custom_optimization_weights = None

    class ConfigurationManager:
        def load_config_or_raise(self):
            return FakeConfig()

        def save_config(self, config):
            return types.SimpleNamespace(success=True, errors=[])

    class PipelineOrchestrator:
        def __init__(self, user_config):
            self.user_config = user_config

        def calculate_recommendation(self):
            return {
                "action": "SELL",
                "confidence": 0.81,
                "reasoning": "Stub recommendation",
                "estimated_savings": 4.5,
                "battery_impact": 0.02,
            }

        def get_hourly_forecast(self, hours):
            return pl.DataFrame(
                {
                    "hour": [0, 1],
                    "action": ["BUY", "SELL"],
                    "confidence": [0.61, 0.74],
                    "reasoning": ["low tariff", "peak tariff"],
                    "savings_estimate": [1.5, 2.0],
                    "battery_impact": [0.01, 0.02],
                }
            )

        def get_status(self):
            return {
                "battery_state": {
                    "soc_percent": 72.0,
                    "cycles_remaining": 4200,
                }
            }

    class OptimizationEngine:
        def get_user_strategy(self, user_config):
            return {"weights": {"profit": 0.7}}

        def optimize_decision(self, recommendation, strategy, weights=None):
            recommendation = dict(recommendation)
            recommendation["optimized"] = True
            return recommendation

        def get_strategy_info(self, strategy):
            return {"description": strategy, "weights": {"profit": 0.7}, "constraints": {}}

    class BatteryPhysicsEngine:
        def simulate_battery_behavior(self, user_config):
            return {"physics_constraints": {}, "current_state": {}, "power_limits": {}}

        def apply_physics_constraints(self, recommendation, physics_data):
            recommendation = dict(recommendation)
            recommendation["physics_applied"] = True
            return recommendation

    class RenewableForecaster:
        def generate_forecasts(self, user_config):
            return {"renewable": "ok"}

        def integrate_with_prediction(self, recommendation, renewable_data):
            recommendation = dict(recommendation)
            recommendation["renewable_applied"] = True
            return recommendation

    pipeline_module.PipelineOrchestrator = PipelineOrchestrator
    user_config_module.ConfigurationManager = ConfigurationManager
    optimization_module.OptimizationEngine = OptimizationEngine
    battery_module.BatteryPhysicsEngine = BatteryPhysicsEngine
    renewable_module.RenewableForecaster = RenewableForecaster

    injected = {
        "energy_ml.pipeline": pipeline_module,
        "energy_ml.user_config": user_config_module,
        "energy_ml.mlops": mlops_package,
        "energy_ml.mlops.optimization_engine": optimization_module,
        "energy_ml.mlops.battery_physics": battery_module,
        "energy_ml.mlops.renewable_forecasting": renewable_module,
    }
    return _load_module("energy_ml.ml_integration_api", "energy_ml/ml_integration_api.py", injected)


ML_INTEGRATION_API = _load_ml_integration_api_module()


def _feature_frame(**overrides) -> pl.DataFrame:
    base = {
        "hour_of_day": 0.5,
        "day_of_week": 0.5,
        "is_peak_hour": 0.0,
        "season": 0.5,
        "current_tariff_uah_mwh": 0.4,
        "price_trend": 0.5,
        "price_volatility": 0.3,
        "soc_percent": 0.5,
        "battery_health": 0.8,
        "degradation_cost_uah_kwh": 0.1,
        "battery_cycles_remaining": 0.8,
        "current_load_kw": 0.4,
        "load_forecast_1h": 0.4,
        "load_trend": 0.5,
    }
    base.update(overrides)
    return pl.DataFrame([base])


def test_prediction_service_validates_missing_and_out_of_range_features():
    service = ML_INTEGRATION.PredictionService()

    valid, errors = service.validate_features(
        _feature_frame().drop("load_trend").with_columns(pl.lit(1.2).alias("soc_percent"))
    )

    assert valid is False
    assert any("Missing features" in error for error in errors)
    assert any("out of bounds" in error for error in errors)


def test_prediction_service_mock_predict_returns_sell_path():
    service = ML_INTEGRATION.PredictionService()

    result = service.predict(_feature_frame(is_peak_hour=1.0, soc_percent=0.9, current_tariff_uah_mwh=0.7))

    assert result["action"] == "SELL"
    assert result["confidence"] > 0.75
    assert result["model_version"] == "mock-v1"


def test_feature_store_generates_online_features_when_cache_missing(tmp_path):
    store = FEATURE_STORE.FeatureStore(store_path=str(tmp_path / "feature_store"))

    result = store.load_online_features("energy_features", {"user_id": "alice"})

    assert result["user_id"] == "alice"
    assert "grid_price_uah_kwh" in result
    assert "generation_forecast_1h" in result


def test_feature_store_parquet_source_returns_expected_empty_schema(tmp_path):
    source = FEATURE_STORE.ParquetSource(str(tmp_path / "missing.parquet"))

    result = source.read()

    assert result.is_empty()
    assert result.columns[:3] == ["user_id", "timestamp", "battery_soc"]


def test_ml_integration_api_get_recommendation_builds_dashboard_payload():
    result = ML_INTEGRATION_API.get_recommendation(enhanced=True)

    assert result["success"] is True
    assert result["action"] == "SELL"
    assert result["daily_savings_estimate"] == 3.5
    assert result["battery_impact"]["current_soc"] == 72.0


def test_ml_integration_api_set_strategy_uses_shared_config_contract():
    result = ML_INTEGRATION_API.set_optimization_strategy("profit", {"profit": 0.9})

    assert result["success"] is True
    assert result["strategy"] == "profit"
    assert result["weights"]["profit"] == 0.7


def test_ml_integration_api_main_emits_json(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["ml_integration_api.py", "--action", "get_status"])
    exit_codes = []

    def fake_exit(code):
        exit_codes.append(code)
        raise SystemExit(code)

    monkeypatch.setattr(ML_INTEGRATION_API.sys, "exit", fake_exit)

    try:
        ML_INTEGRATION_API.main()
    except SystemExit:
        pass

    payload = json.loads(capsys.readouterr().out)
    assert payload["success"] is True
    assert payload["status"]["battery_state"]["cycles_remaining"] == 4200
    assert exit_codes == [0]
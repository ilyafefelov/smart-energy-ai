import importlib.util
import json
import os
import sys
import types
from pathlib import Path

import polars as pl
import pytest


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


TARIFF_MODELS = _load_module("energy_ml.tariff_models_under_test", "energy_ml/tariff_models.py")


def _load_root_ml_api_module():
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
            self.battery_type = "LFP"
            self.battery_capacity_kwh = 20.0
            self.battery_efficiency = 0.95
            self.battery_soc_min = 0.1
            self.battery_soc_max = 1.0
            self.load_profile_type = "standard"
            self.solar_capacity_kw = 12.0
            self.wind_capacity_kw = 4.0
            self.solar_efficiency = 0.2
            self.wind_efficiency = 0.35
            self.latitude = 50.45
            self.longitude = 30.52
            self.timezone = "Europe/Kiev"

    class ConfigurationManager:
        def load_config(self):
            return FakeConfig()

        def save_config(self, config):
            return types.SimpleNamespace(success=True, errors=[])

    class PipelineOrchestrator:
        def __init__(self, user_config):
            self.user_config = user_config
            self.live_context = {}

        def set_live_context(self, live_context):
            self.live_context = live_context

        def calculate_recommendation(self):
            return {
                "action": "HOLD",
                "confidence": 0.62,
                "reasoning": "Base recommendation",
                "estimated_savings": 5.0,
                "battery_impact": 0.03,
            }

        def get_hourly_forecast(self, hours):
            return pl.DataFrame(
                {
                    "hour": list(range(hours)),
                    "action": ["BUY"] * hours,
                    "confidence": [0.6] * hours,
                    "reasoning": ["forecast"] * hours,
                    "savings_estimate": [1.25] * hours,
                    "battery_impact": [0.01] * hours,
                }
            )

        def get_status(self):
            return {
                "battery_state": {
                    "soc_percent": 42.0,
                    "cycles_remaining": 4000,
                }
            }

    class OptimizationEngine:
        def get_user_strategy(self, user_config):
            return {"weights": {"profit": 0.7, "health": 0.3}}

        def optimize_decision(self, recommendation, strategy, weights=None):
            updated = dict(recommendation)
            updated["optimized"] = True
            return updated

        def get_strategy_info(self, strategy):
            return {
                "description": f"Strategy: {strategy}",
                "weights": {"profit": 0.7},
                "constraints": {"max_cycles": 6},
                "available_strategies": ["max_earn", "balanced"],
                "current_cycles": 2,
            }

    class BatteryPhysicsEngine:
        def simulate_battery_behavior(self, user_config):
            return {"status": "ok", "power_limits": {"charge_kw": 5.0}}

        def apply_physics_constraints(self, recommendation, physics_data):
            updated = dict(recommendation)
            updated["physics_applied"] = True
            return updated

    class RenewableForecaster:
        def generate_forecasts(self, user_config):
            return {"solar_kw": 3.0, "wind_kw": 1.0}

        def integrate_with_prediction(self, recommendation, renewable_data):
            updated = dict(recommendation)
            updated["renewable_applied"] = True
            return updated

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
    return _load_module("root_ml_integration_api_under_test", "ml_integration_api.py", injected)


ROOT_ML_API = _load_root_ml_api_module()


def test_tariff_model_uses_expected_peak_boundaries_and_daily_costs() -> None:
    model = TARIFF_MODELS.UkraineTariffModel()

    assert model.get_hourly_rate(5) == pytest.approx(model.off_peak_rate)
    assert model.get_hourly_rate(6) == pytest.approx(model.on_peak_rate)
    assert model.get_hourly_rate(22) == pytest.approx(model.on_peak_rate)
    assert model.get_hourly_rate(23) == pytest.approx(model.off_peak_rate)

    total, hourly_costs = model.calculate_daily_cost([10.0] * 24)

    assert len(hourly_costs) == 24
    assert total == pytest.approx(sum(hourly_costs))
    assert hourly_costs[6] > hourly_costs[5]


def test_tariff_model_calculates_annual_breakdown_and_savings_signal() -> None:
    model = TARIFF_MODELS.UkraineTariffModel()
    annual_load = [10.0] * 8760

    result = model.calculate_365day_cost(annual_load)
    savings = model.estimate_savings_with_battery(annual_load, battery_capacity_kwh=40.0)

    assert len(result.daily_costs) == 365
    assert len(result.hourly_breakdown) == 8760
    assert result.on_peak_hours == 365 * 17
    assert result.off_peak_hours == 365 * 7
    assert savings["original_cost_uah"] > savings["optimized_cost_uah"]
    assert savings["savings_uah"] > 0


def test_tariff_model_rejects_non_annual_inputs() -> None:
    model = TARIFF_MODELS.UkraineTariffModel()

    with pytest.raises(ValueError):
        model.calculate_365day_cost([1.0] * 24)


def test_root_ml_api_recommendation_applies_live_price_signal(monkeypatch: pytest.MonkeyPatch) -> None:
    live_context = {
        "tenant_id": "tenant-alpha",
        "captured_at": "2026-03-06T17:00:00Z",
        "price_signal": {
            "source": "live-prices",
            "current_uah_kwh": 5.0,
            "forecast_next24h": [
                {"hour": hour, "price": 5.0 if hour < 8 else 12.0}
                for hour in range(24)
            ],
        },
        "weather_signal": {"source": "live-weather", "current": {"temp_c": 3.0}},
        "battery_signal": {"soc_percent": 42.0, "health_percent": 96.0, "cycles_remaining": 4000},
    }
    monkeypatch.setenv("ENERGY_ML_LIVE_CONTEXT_JSON", json.dumps(live_context))

    result = ROOT_ML_API.get_recommendation(enhanced=True)

    assert result["success"] is True
    assert result["action"] == "BUY"
    assert result["feature_provenance"]["tenant_id"] == "tenant-alpha"
    assert result["feature_provenance"]["used_live_price_signal"] is True
    assert result["model_inputs"]["battery"]["type"] == "LFP"
    assert len(result["hourly_forecast"]) == 24
    assert result["daily_savings_estimate"] == pytest.approx(24 * 1.25)


def test_root_ml_api_learned_policy_mode_requires_explicit_model_and_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENERGY_ML_SERVING_MODE", "learned_policy")
    monkeypatch.delenv("ENERGY_ML_MODEL_URI", raising=False)
    monkeypatch.delenv("ENERGY_ML_MODEL_NAME", raising=False)
    monkeypatch.delenv("ENERGY_ML_MODEL_ALIAS", raising=False)
    monkeypatch.delenv("ENERGY_ML_MODEL_STAGE", raising=False)

    result = ROOT_ML_API.get_recommendation(enhanced=True)

    assert result["success"] is True
    assert result["serving"]["requested_mode"] == "learned_policy"
    assert result["serving"]["active_mode"] == "incumbent"
    assert result["serving"]["fallback_used"] is True
    assert result["serving"]["fallback_reason_code"] == "learned_policy_model_not_configured"
    assert result["serving"]["model_info"]["availability_error"] == "learned_policy_model_not_configured"
    assert result["contract"]["provenance"]["decision_source"] == "python_rule_engine"
    assert result["contract"]["provenance"]["fallback_reason_code"] == "learned_policy_model_not_configured"


def test_root_ml_api_supports_forecast_status_and_auxiliary_surfaces(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENERGY_ML_LIVE_CONTEXT_JSON", raising=False)

    forecast = ROOT_ML_API.get_forecast(hours=3)
    status = ROOT_ML_API.get_pipeline_status()
    strategy = ROOT_ML_API.get_optimization_strategy()
    updated = ROOT_ML_API.set_optimization_strategy("max_earn", {"profit": 0.9})
    physics = ROOT_ML_API.get_battery_physics()
    renewable = ROOT_ML_API.get_renewable_forecast()

    assert forecast["success"] is True
    assert len(forecast["forecast"]) == 3
    assert status["success"] is True
    assert status["status"]["battery_state"]["cycles_remaining"] == 4000
    assert strategy["success"] is True
    assert strategy["strategy"] == "balanced"
    assert updated["success"] is True
    assert updated["strategy"] == "max_earn"
    assert physics["success"] is True
    assert physics["physics_data"]["power_limits"]["charge_kw"] == 5.0
    assert renewable["success"] is True
    assert renewable["forecast_data"]["solar_kw"] == 3.0


def test_root_ml_api_main_emits_json_for_cli(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["ml_integration_api.py", "--action", "get_status"])
    exit_codes: list[int] = []

    def fake_exit(code: int) -> None:
        exit_codes.append(code)
        raise SystemExit(code)

    monkeypatch.setattr(ROOT_ML_API.sys, "exit", fake_exit)

    with pytest.raises(SystemExit):
        ROOT_ML_API.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["success"] is True
    assert payload["status"]["battery_state"]["soc_percent"] == 42.0
    assert exit_codes == [0]


def test_root_ml_api_wrapper_contract_preserves_expected_exports() -> None:
    expected_exports = {
        "INCUMBENT_SERVING_MODE",
        "LEARNED_POLICY_SERVING_MODE",
        "_load_user_config",
        "_save_user_config",
        "get_battery_physics",
        "get_forecast",
        "get_optimization_strategy",
        "get_pipeline_status",
        "get_recommendation",
        "get_renewable_forecast",
        "load_user_config",
        "main",
        "set_optimization_strategy",
        "setup_logging",
        "sys",
    }

    assert set(ROOT_ML_API.__all__) == expected_exports
    assert ROOT_ML_API._CANONICAL_BRIDGE is not None

    for export_name in expected_exports:
        assert hasattr(ROOT_ML_API, export_name)

    assert ROOT_ML_API.load_user_config is ROOT_ML_API._load_user_config
    assert callable(ROOT_ML_API.get_recommendation)
    assert callable(ROOT_ML_API.get_forecast)
    assert callable(ROOT_ML_API.get_pipeline_status)
    assert callable(ROOT_ML_API.set_optimization_strategy)
    assert callable(ROOT_ML_API.get_optimization_strategy)
    assert callable(ROOT_ML_API.get_battery_physics)
    assert callable(ROOT_ML_API.get_renewable_forecast)
    assert callable(ROOT_ML_API.main)
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import types

import pandas as pd
import polars as pl
import pytest


def load_module(module_name, module_path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_pipeline_module():
    module_path = Path(__file__).resolve().parents[2] / "energy_ml" / "pipeline.py"
    package = types.ModuleType("energy_ml")
    package.__path__ = [str(module_path.parent)]
    mlops_package = types.ModuleType("energy_ml.mlops")
    mlops_package.__path__ = [str(module_path.parent / "mlops")]

    sys.modules.setdefault("energy_ml", package)
    sys.modules.setdefault("energy_ml.mlops", mlops_package)

    user_config = types.ModuleType("energy_ml.user_config")

    class UserConfigModel:
        def __init__(self, **kwargs):
            defaults = {
                "battery_type": "LFP",
                "battery_capacity_kwh": 10.0,
                "battery_efficiency": 0.95,
                "battery_soc_min": 0.1,
                "battery_soc_max": 1.0,
                "battery_cycles_max": 8000,
                "load_profile_type": "standard",
                "load_peak_kw": 10.0,
                "tariff_region": "ukraine",
            }
            defaults.update(kwargs)
            self.__dict__.update(defaults)

        def model_dump(self):
            return dict(self.__dict__)

    class ConfigurationManager:
        def load_config_or_raise(self):
            return UserConfigModel()

    user_config.UserConfigModel = UserConfigModel
    user_config.ConfigurationManager = ConfigurationManager

    config_models = types.ModuleType("energy_ml.config_models")

    class BatteryConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.cycles_to_eol = 4000

    class LoadProfileConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    config_models.BatteryConfig = BatteryConfig
    config_models.LoadProfileConfig = LoadProfileConfig

    battery_degradation = types.ModuleType("energy_ml.battery_degradation")
    battery_degradation.BatteryModel = lambda config: SimpleNamespace(config=config)

    load_simulation = types.ModuleType("energy_ml.load_simulation")

    class StandardWorkSimulator:
        def __init__(self, config):
            self.config = config

        def get_hourly_coefficient(self, hour, default):
            return {0: 0.2, 8: 1.0, 12: 0.9}.get(hour, 0.5)

    load_simulation.StandardWorkSimulator = StandardWorkSimulator

    tariff_models = types.ModuleType("energy_ml.tariff_models")

    class UkraineTariffModel:
        def get_hourly_rate(self, hour):
            return 12000 if 6 <= hour < 23 else 6000

    tariff_models.UkraineTariffModel = UkraineTariffModel

    optimization_engine = types.ModuleType("energy_ml.mlops.optimization_engine")
    optimization_engine.OptimizationEngine = lambda: SimpleNamespace()
    battery_physics = types.ModuleType("energy_ml.mlops.battery_physics")
    battery_physics.BatteryPhysicsEngine = lambda: SimpleNamespace()
    renewable_forecasting = types.ModuleType("energy_ml.mlops.renewable_forecasting")
    renewable_forecasting.RenewableForecaster = lambda: SimpleNamespace()

    sys.modules["energy_ml.user_config"] = user_config
    sys.modules["energy_ml.config_models"] = config_models
    sys.modules["energy_ml.battery_degradation"] = battery_degradation
    sys.modules["energy_ml.load_simulation"] = load_simulation
    sys.modules["energy_ml.tariff_models"] = tariff_models
    sys.modules["energy_ml.mlops.optimization_engine"] = optimization_engine
    sys.modules["energy_ml.mlops.battery_physics"] = battery_physics
    sys.modules["energy_ml.mlops.renewable_forecasting"] = renewable_forecasting

    return load_module("energy_ml.pipeline", module_path)

pipeline_module = load_pipeline_module()


def test_pipeline_live_context_overrides_tariff_and_battery_state():
    orchestrator = pipeline_module.PipelineOrchestrator()
    orchestrator.set_live_context(
        {
            "price_signal": {
                "current_uah_kwh": 10.0,
                "forecast_next24h": [{"hour": 8, "price": 11.5}, {"hour": 9, "price": 12.0}],
            },
            "battery_signal": {
                "soc_percent": 66.0,
                "health_percent": 89.0,
                "cycles_remaining": 3100,
            },
        }
    )

    assert orchestrator._resolve_tariff_rate_uah_mwh(8) == 11500.0
    assert orchestrator._resolve_battery_state() == (66.0, 89.0, 3100.0)

    orchestrator.set_live_context(None)
    default_soc, default_health, default_cycles = orchestrator._resolve_battery_state()
    assert default_soc == pytest.approx(55.0)
    assert default_health == 95.0
    assert default_cycles == 6400.0


def test_pipeline_live_battery_alias_keys_and_invalid_cycles_fall_back():
    orchestrator = pipeline_module.PipelineOrchestrator()
    orchestrator.set_live_context(
        {
            "battery_signal": {
                "soc": 42.0,
                "health": 87.0,
                "cycles_remaining": -10.0,
            }
        }
    )

    battery_soc, battery_health, cycles_remaining = orchestrator._resolve_battery_state()

    assert battery_soc == 42.0
    assert battery_health == 87.0
    assert cycles_remaining == 6400.0


def test_pipeline_decision_and_status_surfaces_remain_stable():
    config = pipeline_module.UserConfigModel(load_peak_kw=12.0)
    orchestrator = pipeline_module.PipelineOrchestrator(user_config=config)
    orchestrator.set_live_context(
        {
            "price_signal": {"forecast_next24h": [{"hour": 8, "price": 13.0}]},
            "battery_signal": {"soc_percent": 74.0, "health_percent": 91.0, "cycles_remaining": 2800},
        }
    )

    action, confidence, reasoning = orchestrator._make_decision(
        load_kw=10.0,
        tariff_rate=13000.0,
        battery_soc=74.0,
        battery_health=91.0,
        charge_cost=2.0,
        discharge_revenue=5.0,
        degradation_cost=0.2,
        is_peak_hour=True,
        current_hour=8,
    )
    forecast = orchestrator.get_hourly_forecast(hours=3)
    status = orchestrator.get_status()

    assert action == "SELL"
    assert confidence == 0.85
    assert "Peak hour" in reasoning
    assert forecast.shape == (3, 6)
    assert status["battery_state"]["soc_percent"] == 74.0
    assert status["tariff"]["current_rate_uah_mwh"] in {11500.0, 12000}
    assert status["last_recommendation"]["decision_source"] == "python_rule_engine"
    assert status["last_recommendation"]["fallback_reason_code"] == "none"


def test_pipeline_economic_helpers_remain_stable():
    orchestrator = pipeline_module.PipelineOrchestrator()

    assert orchestrator._calculate_degradation_cost() == pytest.approx(1.25)
    assert orchestrator._calculate_savings("SELL", 2.0, 5.0, 10.0) == pytest.approx(50.0)
    assert orchestrator._calculate_savings("BUY", 2.0, 5.0, 10.0) == pytest.approx(15.0)
    assert orchestrator._calculate_savings("HOLD", 2.0, 5.0, 10.0) == 0.0
    assert orchestrator._calculate_battery_impact("BUY") == pytest.approx(0.01)
    assert orchestrator._calculate_battery_impact("SELL") == pytest.approx(0.05)
    assert orchestrator._calculate_battery_impact("HOLD") == 0.0


def test_pipeline_recommendation_details_track_price_source():
    orchestrator = pipeline_module.PipelineOrchestrator()
    orchestrator.set_live_context(
        {
            "price_signal": {
                "forecast_next24h": [{"hour": 8, "price": 13.0}],
            },
            "battery_signal": {"soc_percent": 74.0, "health_percent": 91.0, "cycles_remaining": 2800},
        }
    )

    live_details = orchestrator._build_recommendation_details(
        current_hour=8,
        load_kw=10.0,
        tariff_rate=13000.0,
        battery_soc=74.0,
        battery_health=91.0,
        cycles_remaining=2800.0,
        is_peak_hour=True,
        charge_cost=2.0,
        discharge_revenue=5.0,
        battery_degradation_cost=0.2,
    )
    tariff_details = orchestrator._build_recommendation_details(
        current_hour=7,
        load_kw=10.0,
        tariff_rate=12000.0,
        battery_soc=74.0,
        battery_health=91.0,
        cycles_remaining=2800.0,
        is_peak_hour=True,
        charge_cost=2.0,
        discharge_revenue=5.0,
        battery_degradation_cost=0.2,
    )

    assert live_details["price_source"] == "live_market"
    assert tariff_details["price_source"] == "tariff_model"


def test_pipeline_validation_reports_invalid_config_values():
    orchestrator = pipeline_module.PipelineOrchestrator()
    orchestrator.config.battery_capacity_kwh = 0
    orchestrator.config.battery_efficiency = 1.2
    orchestrator.config.load_peak_kw = 0
    orchestrator.config.load_profile_type = "unknown"

    is_valid, errors = orchestrator.validate_all_inputs()

    assert is_valid is False
    assert "Invalid battery capacity: 0" in errors
    assert "Invalid efficiency: 1.2" in errors
    assert "Invalid peak load: 0" in errors
    assert "Unknown load profile: unknown" in errors


def test_pipeline_recommendation_override_rebuilds_runtime_components():
    orchestrator = pipeline_module.PipelineOrchestrator()
    override = pipeline_module.UserConfigModel(
        battery_capacity_kwh=18.0,
        battery_efficiency=0.9,
        load_peak_kw=22.0,
    )

    recommendation = orchestrator.calculate_recommendation(user_config=override, current_hour=8)

    assert orchestrator.config.load_peak_kw == 22.0
    assert orchestrator.battery.config.capacity_kwh == 18.0
    assert orchestrator.load_profile.config.peak_load_kw == 22.0
    assert recommendation["decision_source"] == "python_rule_engine"
    assert recommendation["fallback_reason_code"] == "none"
    assert recommendation["normalized_action"]["action"] == recommendation["action"]
    assert recommendation["details"]["load_kw"] == pytest.approx(22.0)
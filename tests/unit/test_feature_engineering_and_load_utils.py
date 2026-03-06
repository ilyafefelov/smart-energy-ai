import importlib.util
import math
import sys
import types
from datetime import datetime
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


CONFIG_MODELS = _load_module("energy_ml.config_models", "energy_ml/config_models.py")

pipeline_stub = types.ModuleType("energy_ml.pipeline")


class PipelineOrchestrator:
    pass


pipeline_stub.PipelineOrchestrator = PipelineOrchestrator

UTILS = _load_module("nested_utils_under_test", "energy_ml/energy_ml/utils.py")
FEATURES = _load_module(
    "feature_engineer_under_test",
    "energy_ml/features.py",
    injected_modules={"energy_ml.pipeline": pipeline_stub},
)
LOAD_SIMULATION = _load_module("load_simulation_under_test", "energy_ml/load_simulation.py")


BatteryConfig = CONFIG_MODELS.BatteryConfig
GenerationConfig = CONFIG_MODELS.GenerationConfig
LoadProfileConfig = CONFIG_MODELS.LoadProfileConfig
UkraineTariffConfig = CONFIG_MODELS.UkraineTariffConfig
UserProfile = CONFIG_MODELS.UserProfile


class FakeTariff:
    def __init__(self, rate):
        self.rate = rate

    def get_hourly_rate(self, hour):
        return self.rate + hour


class FakeLoadProfile:
    def __init__(self, base_coeff):
        self.base_coeff = base_coeff

    def get_hourly_coefficient(self, hour, day):
        return self.base_coeff + (hour / 100.0)


class FakePipeline:
    def __init__(self, rate=1300.0, load_coeff=60.0):
        self.tariff = FakeTariff(rate)
        self.load_profile = FakeLoadProfile(load_coeff)
        self.battery = object()


def _make_user_profile(profile_type: str = "standard") -> UserProfile:
    if profile_type == "24_7":
        load_profile = LoadProfileConfig.create_24_7_profile(peak_load_kw=12.0)
    else:
        load_profile = LoadProfileConfig.create_standard_work_profile(peak_load_kw=12.0)

    return UserProfile(
        user_id="test-user",
        profile_name="Test Profile",
        battery=BatteryConfig(
            type="LFP",
            capacity_kwh=20.0,
            efficiency=0.94,
            max_charge_rate_kw=5.0,
            max_discharge_rate_kw=5.0,
        ),
        load_profile=load_profile,
        generation=GenerationConfig(solar_capacity_kw=5.0, wind_capacity_kw=0.0),
        tariff=UkraineTariffConfig(),
    )


def test_get_solar_position_and_irradiance_handle_day_and_night():
    midday = datetime(2026, 6, 21, 12, 0, 0)
    midnight = datetime(2026, 6, 21, 0, 0, 0)

    day_position = UTILS.get_solar_position(50.45, 30.52, midday)
    night_position = UTILS.get_solar_position(50.45, 30.52, midnight)
    night_irradiance = UTILS.calculate_irradiance(night_position, cloud_cover=10.0)

    assert day_position["elevation"] > 0
    assert night_position["is_night"] is True
    assert night_irradiance == {"GHI": 0, "DNI": 0, "DHI": 0}


def test_wind_and_solar_generation_utilities_follow_expected_thresholds():
    assert UTILS.wind_power_curve(2.5) == 0
    assert UTILS.wind_power_curve(20.0, rated_capacity=7.5) == 7.5
    assert UTILS.solar_generation_from_irradiance(800.0, 10.0, panel_efficiency=0.2) == 1.6


def test_feature_engineer_extracts_14_clamped_features():
    engineer = FEATURES.FeatureEngineer()
    pipeline = FakePipeline()
    history = {
        "tariff_history": [800.0, 820.0, 840.0, 860.0, 880.0, 900.0, 920.0, 940.0, 960.0, 980.0, 1000.0, 1020.0],
        "load_history": [5.0, 6.0, 5.5, 6.5, 7.0, 8.0],
    }

    result = engineer.extract_features(pipeline, history)

    assert isinstance(result, pl.DataFrame)
    assert result.shape == (1, 14)
    for column in result.columns:
        assert 0.0 <= result[column].item(0) <= 1.0
    assert len(engineer.feature_history) == 1


def test_feature_engineer_reports_importance_for_all_features():
    importance = FEATURES.FeatureEngineer().get_feature_importance()

    assert len(importance) == 14
    assert math.isclose(sum(importance.values()), 1.03, rel_tol=0, abs_tol=1e-9)
    assert importance["is_peak_hour"] > importance["season"]


def test_generate_yearly_load_returns_expected_shapes():
    result = LOAD_SIMULATION.generate_yearly_load(_make_user_profile().load_profile, random_seed=7)

    assert len(result["hourly"]) == 8760
    assert len(result["daily_stats"]) == 365
    assert result["overall"]["annual_peak_kW"] <= round(12.0 * 1.05, 3)


def test_estimate_self_consumption_validates_input_lengths_and_calculates_percentage():
    with pytest.raises(ValueError):
        LOAD_SIMULATION.estimate_self_consumption([1.0, 2.0], [1.0])

    result = LOAD_SIMULATION.estimate_self_consumption([4.0, 2.0, 1.0], [1.0, 3.0, 2.0])

    assert result["self_consumption_pct"] == 57.14
    assert result["estimated_peak_shave_kW"] == 3.0


def test_simple_generation_hourly_is_daylight_only():
    profile = _make_user_profile(profile_type="24_7")

    generation = LOAD_SIMULATION.simple_generation_hourly(profile, seed=3)

    assert len(generation) == 8760
    assert generation[0] == 0.0
    assert max(generation[6:19]) > 0.0
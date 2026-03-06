import importlib.util
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl


ROOT = Path(__file__).resolve().parents[2]


def _dagster_stub() -> types.ModuleType:
    module = types.ModuleType("dagster")

    def asset(*args, **kwargs):
        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return args[0]

        def decorator(func):
            return func

        return decorator

    class Output:
        def __init__(self, value, metadata=None):
            self.value = value
            self.metadata = metadata or {}

        @classmethod
        def __class_getitem__(cls, _item):
            return cls

    class Definitions:
        def __init__(self, assets):
            self.assets = assets

    module.asset = asset
    module.Output = Output
    module.Definitions = Definitions
    return module


def _tenacity_stub() -> types.ModuleType:
    module = types.ModuleType("tenacity")

    def retry(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def stop_after_attempt(attempts):
        return attempts

    def wait_exponential(**kwargs):
        return kwargs

    module.retry = retry
    module.stop_after_attempt = stop_after_attempt
    module.wait_exponential = wait_exponential
    return module


def _load_module(module_name: str, relative_path: str, injected_modules: dict[str, types.ModuleType] | None = None):
    module_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    previous_modules: dict[str, types.ModuleType | None] = {}
    for name, injected in (injected_modules or {}).items():
        previous_modules[name] = sys.modules.get(name)
        sys.modules[name] = injected
    try:
        spec.loader.exec_module(module)
    finally:
        for name, previous in previous_modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    return module


def _energy_ml_nested_stubs() -> dict[str, types.ModuleType]:
    package = types.ModuleType("energy_ml")
    package.__path__ = [str(ROOT / "energy_ml" / "energy_ml")]

    config = types.ModuleType("energy_ml.config")
    config.OPENWEATHER_API_KEY = "test-key"
    config.KYIV_LAT = 50.45
    config.KYIV_LON = 30.52
    config.OPENWEATHER_CACHE_TTL = 3600
    config.OREE_API_URL = "https://example.invalid"

    utils = types.ModuleType("energy_ml.utils")

    def get_solar_position(lat, lon, timestamp):
        return {"elevation": 32.5, "azimuth": 144.0, "is_night": False}

    def calculate_irradiance(position, cloud_cover, pressure):
        return {"GHI": 650.0, "DNI": 520.0, "DHI": 130.0}

    def wind_power_curve(wind_speed, rated_capacity=5.0):
        return min(rated_capacity, round(wind_speed / 2.0, 2))

    utils.get_solar_position = get_solar_position
    utils.calculate_irradiance = calculate_irradiance
    utils.wind_power_curve = wind_power_curve

    return {
        "dagster": _dagster_stub(),
        "tenacity": _tenacity_stub(),
        "energy_ml": package,
        "energy_ml.config": config,
        "energy_ml.utils": utils,
    }


DATA_SOURCES = _load_module(
    "nested_data_sources_under_test",
    "energy_ml/energy_ml/assets/data_sources.py",
    injected_modules=_energy_ml_nested_stubs(),
)
FEATURES = _load_module(
    "nested_features_under_test",
    "energy_ml/energy_ml/assets/features.py",
    injected_modules={"dagster": _dagster_stub()},
)


def test_weather_data_uses_fresh_cache_metadata(monkeypatch):
    cached = pl.DataFrame({
        "timestamp": [datetime.utcnow()],
        "temp": [21.0],
        "humidity": [55.0],
        "cloud_cover": [20.0],
        "wind_speed": [4.0],
        "wind_direction": [180.0],
        "pressure": [1012.0],
        "description": ["clear sky"],
    })
    monkeypatch.setitem(DATA_SOURCES._weather_cache, "data", cached)
    monkeypatch.setitem(DATA_SOURCES._weather_cache, "timestamp", datetime.utcnow())

    result = DATA_SOURCES.weather_data()

    assert result.metadata["source"] == "cache"
    assert result.value.equals(cached)


def test_weather_data_falls_back_to_defaults_on_request_error(monkeypatch):
    monkeypatch.setitem(DATA_SOURCES._weather_cache, "data", None)
    monkeypatch.setitem(DATA_SOURCES._weather_cache, "timestamp", None)

    def fail_request(*args, **kwargs):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr(DATA_SOURCES.requests, "get", fail_request)

    result = DATA_SOURCES.weather_data()

    assert result.metadata["error"] == "network unavailable"
    assert result.value["temp"].item(0) == 15.0
    assert result.value["description"].item(0) == "Unknown"


def test_solar_and_wind_assets_translate_weather_frame_into_metadata():
    weather = pl.DataFrame({
        "timestamp": [datetime(2026, 3, 6, 12, 0, 0)],
        "temp": [18.0],
        "humidity": [45.0],
        "cloud_cover": [25.0],
        "wind_speed": [6.0],
        "wind_direction": [135.0],
        "pressure": [1015.0],
        "description": ["partly cloudy"],
    })

    solar_result = DATA_SOURCES.solar_irradiance(weather)
    wind_result = DATA_SOURCES.wind_potential(weather)

    assert solar_result.metadata["ghi_w_m2"] == 650.0
    assert solar_result.value["elevation_deg"].item(0) == 32.5
    assert wind_result.metadata["power_potential_kw"] == 3.0
    assert wind_result.value["wind_direction_deg"].item(0) == 135.0


def test_time_and_weather_features_produce_expected_aggregates():
    current_timestamp = pd.Timestamp("2026-03-06 09:00:00")
    weather_data = pd.DataFrame([
        {
            "timestamp": current_timestamp,
            "temp": 20.0,
            "humidity": 80.0,
            "cloud_cover": 40.0,
            "wind_speed": 8.0,
            "wind_direction": 90.0,
            "pressure": 1018.0,
        }
    ])
    forecast = pd.DataFrame([
        {"timestamp": current_timestamp + timedelta(hours=0), "temp": 20.0, "cloud_cover": 40.0, "wind_speed": 8.0},
        {"timestamp": current_timestamp + timedelta(hours=6), "temp": 22.0, "cloud_cover": 50.0, "wind_speed": 10.0},
        {"timestamp": current_timestamp + timedelta(hours=12), "temp": 24.0, "cloud_cover": 30.0, "wind_speed": 6.0},
        {"timestamp": current_timestamp + timedelta(hours=18), "temp": 30.0, "cloud_cover": 80.0, "wind_speed": 3.0},
    ])

    time_result = FEATURES.time_features(weather_data)
    weather_result = FEATURES.weather_features(weather_data, forecast)

    assert time_result.metadata["hour"] == 9
    assert time_result.value.iloc[0]["is_working_hours"] == 1
    assert weather_result.value.iloc[0]["forecast_temp_12h"] == 22.0
    assert round(weather_result.value.iloc[0]["wind_direction_cos"], 6) == 0.0


def test_feature_matrix_cleans_missing_and_infinite_numeric_values():
    time_features = pd.DataFrame([{"hour": 9.0}])
    weather_features = pd.DataFrame([{"temp_c": 20.0}])
    generation_features = pd.DataFrame([{"solar_power_kw": np.nan}])
    battery_features = pd.DataFrame([{"soc_percent": 60.0}])
    price_features = pd.DataFrame([{"price_uah_kwh": 14.5}])
    interaction_features = pd.DataFrame([{"charge_opportunity": np.inf}])

    result = FEATURES.feature_matrix(
        time_features,
        weather_features,
        generation_features,
        battery_features,
        price_features,
        interaction_features,
    )

    assert result.metadata["missing_values"] == 1
    assert result.metadata["infinite_values"] == 1
    numeric_values = result.value.select_dtypes(include=[np.number]).to_numpy()
    assert np.isfinite(numeric_values).all()


def test_interaction_features_keep_scores_non_negative_when_generation_is_low():
    result = FEATURES.interaction_features(
        pd.DataFrame([{"hour": 18, "is_peak_hours": 1}]),
        pd.DataFrame([{"temp_c": 10.0, "cloud_cover_norm": 0.8, "wind_speed_ms": 4.0}]),
        pd.DataFrame([{"solar_power_kw": 0.0, "wind_power_kw": 0.5, "total_gen_potential_kw": 0.5}]),
        pd.DataFrame([{"soc_percent": 40.0, "hours_to_empty": 2.0}]),
        pd.DataFrame([{"price_uah_kwh": 16.0}]),
    )

    row = result.value.iloc[0]
    assert row["charge_opportunity"] >= 0.0
    assert row["discharge_opportunity"] >= 0.0
    assert result.metadata["num_features"] == len(result.value.columns)
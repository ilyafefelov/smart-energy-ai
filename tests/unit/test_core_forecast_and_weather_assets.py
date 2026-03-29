from __future__ import annotations

import importlib.util
import json
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl


REPO_ROOT = Path(__file__).resolve().parents[2]


def build_dagster_module():
    module = types.ModuleType("dagster")
    module.asset = lambda *args, **kwargs: (lambda func: func)
    module.AssetIn = lambda asset_key: {"asset_key": asset_key}
    module.MetadataValue = object
    return module


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


def build_milp_injected_modules():
    dagster_mod = build_dagster_module()

    src_pkg = types.ModuleType("src")
    src_pkg.__path__ = [str(REPO_ROOT / "src")]
    assets_pkg = types.ModuleType("src.assets")
    assets_pkg.__path__ = [str(REPO_ROOT / "src" / "assets")]
    core_pkg = types.ModuleType("src.assets.core")
    core_pkg.__path__ = [str(REPO_ROOT / "src" / "assets" / "core")]
    optimization_mod = types.ModuleType("src.optimization")
    opt_sched_mod = types.ModuleType("src.assets.core.optimization_schedule")

    class MilpSchedulerConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class MilpBatteryScheduler:
        def __init__(self, config):
            self.config = config

        def optimize(self, prices, load_forecast, solar_forecast):
            rows = []
            for hour, price in enumerate(prices):
                rows.append(
                    {
                        "hour": hour,
                        "action_kw": 2.0 if hour == 0 else 0.0,
                        "charge_kwh": 0.0,
                        "discharge_kwh": 2.0 if hour == 0 else 0.0,
                        "soc_before_kwh": 120.0,
                        "soc_after_kwh": 118.0,
                        "throughput_total_kwh": float(hour + 1),
                        "price_eur_mwh": float(price),
                        "load_kwh": float(load_forecast[hour]),
                        "solar_kwh": float(solar_forecast[hour]),
                        "grid_import_kwh": 0.0,
                        "grid_export_kwh": 2.0 if hour == 0 else 0.0,
                        "purchase_cost_eur": 0.0,
                        "export_revenue_eur": 1.2,
                        "degradation_penalty_eur": 0.1,
                        "net_cost_eur": -1.1 if hour == 0 else 0.0,
                    }
                )
            return {
                "schedule": rows,
                "objective": {"net_cost_eur": -1.1},
                "constraints": {"final_soc_kwh": 118.0, "throughput_limit_kwh": self.config.throughput_limit_kwh},
                "metadata": {"algorithm": "milp", "solver": "stub-solver"},
            }

    optimization_mod.MilpBatteryScheduler = MilpBatteryScheduler
    optimization_mod.MilpSchedulerConfig = MilpSchedulerConfig

    opt_sched_mod._extract_price_horizon = lambda df: df["predicted_price_eur_mwh"].to_list() if "predicted_price_eur_mwh" in df.columns else []
    opt_sched_mod._get_client_series = lambda client_df, column, horizon, fallback: [float(v) for v in client_df[column].to_list()[-horizon:]] if column in client_df.columns else [fallback] * horizon
    opt_sched_mod._load_client_capacities = lambda: {"tenant-a": 180.0}
    schema = {
        "client_id": pl.Utf8,
        "hour": pl.Int64,
        "action_kw": pl.Float64,
        "charge_kwh": pl.Float64,
        "discharge_kwh": pl.Float64,
        "soc_before_kwh": pl.Float64,
        "soc_after_kwh": pl.Float64,
        "throughput_total_kwh": pl.Float64,
        "price_eur_mwh": pl.Float64,
        "load_kwh": pl.Float64,
        "solar_kwh": pl.Float64,
        "grid_import_kwh": pl.Float64,
        "grid_export_kwh": pl.Float64,
        "purchase_cost_eur": pl.Float64,
        "export_revenue_eur": pl.Float64,
        "degradation_penalty_eur": pl.Float64,
        "net_cost_eur": pl.Float64,
        "total_net_cost_eur": pl.Float64,
        "final_soc_kwh": pl.Float64,
        "throughput_limit_kwh": pl.Float64,
        "algorithm": pl.Utf8,
        "solver": pl.Utf8,
    }
    opt_sched_mod.build_empty_optimization_schedule = lambda: pl.DataFrame(schema=schema)
    opt_sched_mod.build_optimization_schedule_frame = lambda rows: pl.DataFrame(rows, schema=schema)

    return {
        "dagster": dagster_mod,
        "src": src_pkg,
        "src.assets": assets_pkg,
        "src.assets.core": core_pkg,
        "src.optimization": optimization_mod,
        "src.assets.core.optimization_schedule": opt_sched_mod,
    }


def test_optimization_schedule_milp_asset_outputs_schedule() -> None:
    module = load_module(
        "src.assets.core.optimization_schedule_milp",
        "src/assets/core/optimization_schedule_milp.py",
        injected_modules=build_milp_injected_modules(),
    )

    context = types.SimpleNamespace(log=types.SimpleNamespace(info=lambda *args, **kwargs: None, warning=lambda *args, **kwargs: None))
    price_forecast = pl.DataFrame({"predicted_price_eur_mwh": [50.0, 55.0]})
    client_state = pl.DataFrame(
        {
            "client_id": ["tenant-a", "tenant-a"],
            "timestamp": [datetime(2026, 3, 6, 0, 0), datetime(2026, 3, 6, 1, 0)],
            "battery_soc": [60.0, 62.0],
            "load_actual": [40.0, 42.0],
            "solar_gen_actual": [5.0, 6.0],
        }
    )

    result = module.optimization_schedule_milp_asset(context, price_forecast, client_state)

    assert len(result) == 2
    assert result["client_id"].to_list() == ["tenant-a", "tenant-a"]
    assert result["solver"].to_list()[0] == "stub-solver"


def test_price_forecast_helpers_and_fallback_asset() -> None:
    module = load_module(
        "src.assets.core.price_forecast_under_test",
        "src/assets/core/price_forecast.py",
        injected_modules={"dagster": build_dagster_module()},
    )

    timestamps = [datetime(2026, 3, 1, 0, 0) + timedelta(hours=hour) for hour in range(30)]
    market_data = pl.DataFrame({"timestamp": timestamps, "price_eur_mwh": [40.0 + hour for hour in range(30)]})

    feature_df = module._build_feature_frame(market_data)
    train_df, eval_df = module._split_train_eval(feature_df)
    forecast = module.price_forecast_asset(market_data)

    assert "lag_1h" in feature_df.columns
    assert len(train_df) == len(feature_df)
    assert len(eval_df) == 0
    assert len(forecast) == 24
    assert set(forecast["model_name"].unique().to_list()) == {"persistence_fallback"}


def test_weather_helpers_and_asset_flow(monkeypatch) -> None:
    module = load_module(
        "src.assets.core.weather_under_test",
        "src/assets/core/weather.py",
        injected_modules={"dagster": build_dagster_module()},
    )

    monkeypatch.setenv("WEATHER_LATITUDE", "91")
    monkeypatch.setenv("WEATHER_LONGITUDE", "-200")
    monkeypatch.setenv("WEATHER_TIMEZONE", "UTC")
    lat, lon, tz = module._resolve_weather_location()
    assert (lat, lon, tz) == (90.0, -180.0, "UTC")

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "hourly": {
                    "time": ["2026-03-06T00:00", "2026-03-06T01:00"],
                    "temperature_2m": [2.0, 3.0],
                    "shortwave_radiation": [0.0, 10.0],
                    "windspeed_10m": [4.0, 5.0],
                    "cloudcover": [20.0, 30.0],
                    "precipitation": [0.0, 0.1],
                    "surface_pressure": [1010.0, 1011.0],
                    "relativehumidity_2m": [70.0, 71.0],
                }
            }

    monkeypatch.setattr(module.requests, "get", lambda *args, **kwargs: Response())
    fetched = module._fetch_openmeteo_data(50.45, 30.52, "UTC")
    assert len(fetched) == 2
    assert fetched[1]["wind_speed"] == 5.0

    validated = module._validate_weather_data(
        pl.DataFrame(
            {
                "timestamp": [datetime(2026, 3, 6, 0, 0)],
                "temperature": [100.0],
                "solar_radiation": [1500.0],
                "wind_speed": [60.0],
                "cloudcover": [120.0],
                "precipitation": [200.0],
                "pressure": [2000.0],
                "humidity": [120.0],
                "source": ["OPEN_METEO"],
            }
        )
    )
    assert validated["temperature"].item() == 50.0
    assert validated["solar_radiation"].item() == 1200.0

    monkeypatch.setattr(module, "_fetch_openmeteo_data", lambda lat, lon, timezone: fetched)
    asset_df = module.weather_asset()
    assert len(asset_df) == 2
    assert "effective_solar" in asset_df.columns
    assert set(asset_df["source"].unique().to_list()) == {"OPEN_METEO"}
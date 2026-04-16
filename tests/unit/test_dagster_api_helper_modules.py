from __future__ import annotations

import dataclasses
import importlib.util
import json
import os
import sys
import types
from datetime import datetime
from pathlib import Path


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


def build_src_packages():
    src_pkg = types.ModuleType("src")
    src_pkg.__path__ = [str(REPO_ROOT / "src")]
    dagster_api_pkg = types.ModuleType("src.dagster_api")
    dagster_api_pkg.__path__ = [str(REPO_ROOT / "src" / "dagster_api")]
    assets_pkg = types.ModuleType("src.assets")
    assets_pkg.__path__ = [str(REPO_ROOT / "src" / "assets")]
    assets_core_pkg = types.ModuleType("src.assets.core")
    assets_core_pkg.__path__ = [str(REPO_ROOT / "src" / "assets" / "core")]
    assets_benchmarks_pkg = types.ModuleType("src.assets.benchmarks")
    assets_benchmarks_pkg.__path__ = [str(REPO_ROOT / "src" / "assets" / "benchmarks")]
    src_pkg.dagster_api = dagster_api_pkg
    src_pkg.assets = assets_pkg
    assets_pkg.core = assets_core_pkg
    assets_pkg.benchmarks = assets_benchmarks_pkg
    return src_pkg, dagster_api_pkg, assets_pkg, assets_core_pkg, assets_benchmarks_pkg


def test_models_round_trip_serialization() -> None:
    module = load_module("models_under_test", "src/dagster_api/models.py")

    result = module.AssetResult(
        asset_name="weather_asset",
        run_id="run-1",
        tenant_id="tenant-a",
        materialization_time=datetime(2026, 3, 6, 12, 0),
        data={"value": 1},
        execution_time_ms=42,
    )
    as_dict = result.to_dict()
    as_json = result.to_json()
    restored = module.AssetResult.from_dict(as_dict.copy())
    metadata = module.AssetMetadata(
        asset_name="weather_asset",
        description="Weather output",
        created_at=datetime(2026, 3, 1, 0, 0),
        last_updated=datetime(2026, 3, 6, 0, 0),
        schema={"type": "object"},
    )

    assert as_dict["materialization_time"] == "2026-03-06T12:00:00"
    assert json.loads(as_json)["tenant_id"] == "tenant-a"
    assert restored.materialization_time == datetime(2026, 3, 6, 12, 0)
    assert metadata.schema == {"type": "object"}


def test_store_results_reads_latest_temp_storage(monkeypatch, tmp_path) -> None:
    src_pkg, dagster_api_pkg, _, _, _ = build_src_packages()
    stored = []

    asset_service_mod = types.ModuleType("src.dagster_api.asset_service")
    asset_service_mod.get_asset_service = lambda: types.SimpleNamespace(
        store_asset_result=lambda **kwargs: stored.append(kwargs)
    )

    module = load_module(
        "store_results_under_test",
        "src/dagster_api/store_results.py",
        injected_modules={
            "src": src_pkg,
            "src.dagster_api": dagster_api_pkg,
            "src.dagster_api.asset_service": asset_service_mod,
        },
    )

    latest = tmp_path / ".tmp_dagster_home_latest" / "storage"
    latest.mkdir(parents=True)
    (latest / "weather_asset").write_bytes(b"abc")
    (latest / "market_data_asset").write_bytes(b"12345")

    older = tmp_path / ".tmp_dagster_home_old" / "storage"
    older.mkdir(parents=True)
    (older / "old_asset").write_bytes(b"zzz")

    os.utime(older.parent, (1, 1))
    os.utime(latest.parent, None)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module.time, "time", lambda: 1000.0)

    module.store_asset_outputs()

    assert len(stored) == 2
    assert {item["asset_name"] for item in stored} == {"weather_asset", "market_data_asset"}
    assert all(item["status"] == "success" for item in stored)


def test_trigger_materializes_assets_and_handles_failure(monkeypatch, capsys) -> None:
    src_pkg, dagster_api_pkg, assets_pkg, assets_core_pkg, assets_benchmarks_pkg = build_src_packages()
    stored = []

    class FakeDatabase:
        def __init__(self):
            self.init_calls = 0

        def init_schema(self):
            self.init_calls += 1

    fake_db = FakeDatabase()

    class FakeAssetService:
        def __init__(self, database):
            self.database = database
            self.raise_once = False

        def store_asset_result(self, **kwargs):
            stored.append(kwargs)
            if self.raise_once:
                self.raise_once = False
                raise RuntimeError("store failed")
            return True

        def list_assets(self):
            return ["weather_asset"]

        def get_asset_summary(self):
            return {"weather_asset": {"runs": 1}}

    dagster_mod = types.ModuleType("dagster")
    dagster_mod.DagsterInstance = types.SimpleNamespace(get=lambda: object())
    autodiscovery_mod = types.ModuleType("dagster._core.workspace.autodiscovery")
    autodiscovery_mod.load_assets_from_modules = lambda modules: []
    polars_mod = types.ModuleType("polars")

    database_mod = types.ModuleType("src.dagster_api.database")
    database_mod.Database = FakeDatabase
    database_mod.get_database = lambda: fake_db

    asset_service_mod = types.ModuleType("src.dagster_api.asset_service")
    asset_service_mod.AssetService = FakeAssetService

    performance_mod = types.ModuleType("src.assets.benchmarks.performance")
    performance_mod.accuracy_benchmark_asset = object()
    performance_mod.engine_benchmark_asset = object()
    performance_mod.forecast_value_benchmark_asset = object()
    performance_mod.mlflow_tracking_asset = object()
    assets_benchmarks_pkg.performance = performance_mod

    market_mod = types.ModuleType("src.assets.core.market")
    market_mod.market_data_asset = object()
    weather_mod = types.ModuleType("src.assets.core.weather")
    weather_mod.weather_asset = object()
    client_state_mod = types.ModuleType("src.assets.core.client_state")
    client_state_mod.client_state_asset = object()
    feature_matrix_mod = types.ModuleType("src.assets.core.feature_matrix")
    feature_matrix_mod.feature_matrix_asset = object()
    price_forecast_mod = types.ModuleType("src.assets.core.price_forecast")
    price_forecast_mod.price_forecast_asset = object()
    optimization_schedule_mod = types.ModuleType("src.assets.core.optimization_schedule")
    optimization_schedule_mod.optimization_schedule_asset = object()
    optimization_schedule_milp_mod = types.ModuleType("src.assets.core.optimization_schedule_milp")
    optimization_schedule_milp_mod.optimization_schedule_milp_asset = object()
    assets_core_pkg.market = market_mod
    assets_core_pkg.weather = weather_mod
    assets_core_pkg.client_state = client_state_mod
    assets_core_pkg.feature_matrix = feature_matrix_mod
    assets_core_pkg.price_forecast = price_forecast_mod
    assets_core_pkg.optimization_schedule = optimization_schedule_mod
    assets_core_pkg.optimization_schedule_milp = optimization_schedule_milp_mod

    module = load_module(
        "src.dagster_api.trigger",
        "src/dagster_api/trigger.py",
        injected_modules={
            "src": src_pkg,
            "src.dagster_api": dagster_api_pkg,
            "src.assets": assets_pkg,
            "src.assets.core": assets_core_pkg,
            "src.assets.benchmarks": assets_benchmarks_pkg,
            "dagster": dagster_mod,
            "dagster._core.workspace.autodiscovery": autodiscovery_mod,
            "polars": polars_mod,
            "src.dagster_api.database": database_mod,
            "src.dagster_api.asset_service": asset_service_mod,
            "src.assets.benchmarks.performance": performance_mod,
            "src.assets.core.market": market_mod,
            "src.assets.core.weather": weather_mod,
            "src.assets.core.client_state": client_state_mod,
            "src.assets.core.feature_matrix": feature_matrix_mod,
            "src.assets.core.price_forecast": price_forecast_mod,
            "src.assets.core.optimization_schedule": optimization_schedule_mod,
            "src.assets.core.optimization_schedule_milp": optimization_schedule_milp_mod,
        },
    )

    runtime_modules = {
        "src": src_pkg,
        "src.dagster_api": dagster_api_pkg,
        "src.assets": assets_pkg,
        "src.assets.core": assets_core_pkg,
        "src.assets.benchmarks": assets_benchmarks_pkg,
        "dagster": dagster_mod,
        "dagster._core.workspace.autodiscovery": autodiscovery_mod,
        "polars": polars_mod,
        "src.dagster_api.database": database_mod,
        "src.dagster_api.asset_service": asset_service_mod,
        "src.assets.benchmarks.performance": performance_mod,
        "src.assets.core.market": market_mod,
        "src.assets.core.weather": weather_mod,
        "src.assets.core.client_state": client_state_mod,
        "src.assets.core.feature_matrix": feature_matrix_mod,
        "src.assets.core.price_forecast": price_forecast_mod,
        "src.assets.core.optimization_schedule": optimization_schedule_mod,
        "src.assets.core.optimization_schedule_milp": optimization_schedule_milp_mod,
    }
    for name, runtime_module in runtime_modules.items():
        monkeypatch.setitem(sys.modules, name, runtime_module)

    monkeypatch.setattr(module.time, "time", lambda: 1000.0)
    trigger = module.DagsterTrigger()
    success = trigger.materialize_asset("weather_asset")
    unknown = trigger.materialize_asset("missing_asset")

    assert success["status"] == "success"
    assert unknown["error"] == "Unknown asset: missing_asset"
    assert fake_db.init_calls >= 1

    trigger.asset_service.raise_once = True
    failed = trigger.materialize_asset("market_data_asset")
    assert failed["status"] == "failed"
    assert stored[-1]["status"] == "failed"

    monkeypatch.setattr(sys, "argv", ["trigger.py", "list"])
    module.main()
    list_output = capsys.readouterr().out
    assert "Stored assets:" in list_output

    monkeypatch.setattr(sys, "argv", ["trigger.py", "summary"])
    module.main()
    summary_output = capsys.readouterr().out
    assert "Asset Summary:" in summary_output
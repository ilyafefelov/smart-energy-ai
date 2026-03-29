from __future__ import annotations

import dataclasses
import importlib.util
import json
import subprocess
import sys
import time
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
    return src_pkg, dagster_api_pkg


def test_asset_service_handles_tenant_scoped_reads_and_writes(monkeypatch) -> None:
    src_pkg, dagster_api_pkg = build_src_packages()
    fake_db = types.SimpleNamespace()
    executed = []

    @dataclasses.dataclass
    class AssetResult:
        asset_name: str
        run_id: str
        tenant_id: str | None
        materialization_time: datetime
        data: dict
        status: str = "success"
        error_message: str | None = None
        execution_time_ms: int | None = None

    def execute(query, params=None):
        executed.append((query, params))
        if "SELECT asset_name, run_id, tenant_id, materialization_time, status" in query:
            return [{"asset_name": "weather_asset", "run_id": "r1", "tenant_id": "tenant-a", "materialization_time": datetime(2026, 3, 6), "status": "success", "execution_time_ms": 42, "error_message": None}]
        if "SELECT asset_name, run_id, tenant_id, materialization_time, data" in query and "LIMIT %s" in query:
            return [{"asset_name": "weather_asset", "run_id": "r1", "tenant_id": "tenant-a", "materialization_time": datetime(2026, 3, 6), "data": json.dumps({"value": 1}), "status": "success", "error_message": None, "execution_time_ms": 42}]
        if "SELECT DISTINCT asset_name" in query:
            return [{"asset_name": "market_data_asset"}, {"asset_name": "weather_asset"}]
        if "COUNT(*) as run_count" in query:
            return [{"asset_name": "weather_asset", "run_count": 2, "last_run": datetime(2026, 3, 6), "first_success": datetime(2026, 3, 5), "last_success": datetime(2026, 3, 6), "avg_execution_time_ms": 50.0}]
        return []

    fake_db.execute = execute
    fake_db.execute_one = lambda query, params=None: execute(query, params)[0]

    dagster_mod = types.ModuleType("dagster")
    dagster_mod.DagsterInstance = types.SimpleNamespace(get=lambda: object())

    database_mod = types.ModuleType("src.dagster_api.database")
    database_mod.Database = object
    database_mod.get_database = lambda: fake_db

    models_mod = types.ModuleType("src.dagster_api.models")
    models_mod.AssetResult = AssetResult

    monkeypatch.setenv("ENERGY_ML_TENANT_ID", "Tenant-A")
    module = load_module(
        "src.dagster_api.asset_service",
        "src/dagster_api/asset_service.py",
        injected_modules={
            "src": src_pkg,
            "src.dagster_api": dagster_api_pkg,
            "dagster": dagster_mod,
            "src.dagster_api.database": database_mod,
            "src.dagster_api.models": models_mod,
        },
    )

    service = module.AssetService(database=fake_db)
    assert module._normalize_tenant_id(" Tenant-A ") == "tenant-a"
    assert module._resolve_required_tenant_id(None) == "tenant-a"
    assert service.get_recent_runs(limit=5)[0]["asset_name"] == "weather_asset"
    result = service.get_asset_result("weather_asset")
    assert result.data == {"value": 1}
    assert service.store_asset_result("weather_asset", "run-2", {"tenant_id": "TENANT-A", "value": 2}) is True
    assert service.list_assets() == ["market_data_asset", "weather_asset"]
    assert "weather_asset" in service.get_asset_summary()
    assert service.store_asset_result("weather_asset", "run-3", {"value": 3}, tenant_id=None) is True

    monkeypatch.delenv("ENERGY_ML_TENANT_ID")
    assert module._resolve_required_tenant_id(None) is None


def test_database_initializes_schema_and_executes_queries() -> None:
    executed = []

    class FakeCursor:
        def __init__(self):
            self.lastrowid = 7

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=None):
            executed.append((query, params))

        def fetchall(self):
            return [{"value": 1}]

    class FakeConnection:
        def __init__(self):
            self.closed = False
            self.commits = 0

        def cursor(self):
            return FakeCursor()

        def commit(self):
            self.commits += 1

        def close(self):
            self.closed = True

    fake_connection = FakeConnection()
    psycopg2_mod = types.ModuleType("psycopg2")
    psycopg2_mod.connect = lambda **kwargs: fake_connection
    extras_mod = types.ModuleType("psycopg2.extras")
    extras_mod.RealDictCursor = object

    module = load_module(
        "database_under_test",
        "src/dagster_api/database.py",
        injected_modules={"psycopg2": psycopg2_mod, "psycopg2.extras": extras_mod},
    )

    database = module.Database()
    database.init_schema()
    assert database.test_connection() is True
    assert database.execute("SELECT 1") == [{"value": 1}]
    assert database.insert("INSERT INTO asset_results VALUES (%s)", (1,)) == 7
    assert any("CREATE TABLE IF NOT EXISTS asset_results" in query for query, _ in executed)
    assert fake_connection.commits >= 2


def test_cli_lists_summaries_and_runs_assets(monkeypatch, capsys) -> None:
    src_pkg, dagster_api_pkg = build_src_packages()

    @dataclasses.dataclass
    class Result:
        asset_name: str
        run_id: str
        materialization_time: datetime
        status: str
        execution_time_ms: int
        data: dict

    stored = []
    fake_service = types.SimpleNamespace(
        list_assets=lambda: ["weather_asset"],
        get_asset_summary=lambda: {"weather_asset": {"run_count": 2, "last_run": datetime(2026, 3, 6), "last_success": datetime(2026, 3, 6), "avg_execution_time_ms": 55.0}},
        get_asset_result=lambda name: Result(name, "run-1", datetime(2026, 3, 6), "success", 55, {"value": 1}),
        store_asset_result=lambda **kwargs: stored.append(kwargs),
    )

    asset_service_mod = types.ModuleType("src.dagster_api.asset_service")
    asset_service_mod.get_asset_service = lambda: fake_service

    module = load_module(
        "src.dagster_api.cli",
        "src/dagster_api/cli.py",
        injected_modules={
            "src": src_pkg,
            "src.dagster_api": dagster_api_pkg,
            "src.dagster_api.asset_service": asset_service_mod,
        },
    )

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: types.SimpleNamespace(returncode=0, stdout="ok", stderr=""))
    monkeypatch.setattr(time, "time", lambda: 1000.0)
    monkeypatch.setattr(module, "run_asset", lambda name: print(f"ran {name}"))

    module.list_assets()
    module.show_summary()
    module.get_asset("weather_asset")
    output = capsys.readouterr().out
    assert "Stored assets:" in output
    assert "Asset Summary:" in output
    assert "Asset: weather_asset" in output

    monkeypatch.setattr(module, "run_asset", lambda name: print(f"run {name}"))
    module.run_all()
    run_all_output = capsys.readouterr().out
    assert "Running: market_data_asset" in run_all_output

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: types.SimpleNamespace(returncode=0, stdout="materialized", stderr=""))
    module = load_module(
        "src.dagster_api.cli_runtime",
        "src/dagster_api/cli.py",
        injected_modules={
            "src": src_pkg,
            "src.dagster_api": dagster_api_pkg,
            "src.dagster_api.asset_service": asset_service_mod,
        },
    )
    module.run_asset("weather_asset")
    assert stored[0]["asset_name"] == "weather_asset"

    monkeypatch.setattr(sys, "argv", ["cli.py", "unknown"])
    module.main()
    main_output = capsys.readouterr().out
    assert "Unknown command: unknown" in main_output
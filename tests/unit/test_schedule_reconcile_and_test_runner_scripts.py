from __future__ import annotations

import importlib.util
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_script_module(module_name: str, relative_path: str, sqlalchemy_module=None):
    module_path = REPO_ROOT / relative_path

    previous_sqlalchemy = sys.modules.get("sqlalchemy")
    if sqlalchemy_module is not None:
        sys.modules["sqlalchemy"] = sqlalchemy_module

    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if sqlalchemy_module is not None:
            if previous_sqlalchemy is None:
                sys.modules.pop("sqlalchemy", None)
            else:
                sys.modules["sqlalchemy"] = previous_sqlalchemy


def build_sqlalchemy_module():
    module = types.ModuleType("sqlalchemy")
    module.create_engine = lambda *args, **kwargs: None
    module.text = lambda query: query
    return module


def test_read_dagster_schedule_helpers_and_main(monkeypatch, capsys, tmp_path: Path) -> None:
    module = load_script_module("scripts.read_dagster_schedule_under_test", "scripts/read_dagster_schedule.py")

    rows = [
        {"hour": 2, "action_kw": -1.25, "net_cost_eur": 3.0, "price_eur_mwh": 100.0, "solver": "milp", "client_id": "tenant-b", "soc_before_kwh": 80.0, "grid_export_kwh": 0.0, "forecast_model_name": "promoted_model", "forecast_model_family": "random_forest_regressor", "forecast_horizon_mode": "conservative", "forecast_uncertainty_source": "walk_forward_residual_std", "forecast_promotion_active": True, "forecast_promotion_source": "forecast_value_benchmark_asset"},
        {"hour": 0, "action_kw": 1.5, "net_cost_eur": -4.0, "price_eur_mwh": 120.0, "solver": "milp", "client_id": "tenant-a", "soc_before_kwh": 100.0, "grid_export_kwh": 0.4, "forecast_model_name": "promoted_model", "forecast_model_family": "random_forest_regressor", "forecast_horizon_mode": "conservative", "forecast_uncertainty_source": "walk_forward_residual_std", "forecast_promotion_active": True, "forecast_promotion_source": "forecast_value_benchmark_asset"},
        {"hour": 1, "action_kw": 0.0, "net_cost_eur": 0.5, "price_eur_mwh": 110.0, "solver": "milp", "client_id": "tenant-a", "soc_before_kwh": 99.0, "grid_export_kwh": 0.0, "forecast_model_name": "promoted_model", "forecast_model_family": "random_forest_regressor", "forecast_horizon_mode": "conservative", "forecast_uncertainty_source": "walk_forward_residual_std", "forecast_promotion_active": True, "forecast_promotion_source": "forecast_value_benchmark_asset"},
    ]

    selected_rows, selected_client = module._select_client_rows(rows, "tenant-a")
    schedule = module._normalize_schedule(selected_rows, 45.0)
    recommendation = module._build_recommendation(schedule, "optimization_schedule_milp_asset")

    assert selected_client == "tenant-a"
    assert [row["hour"] for row in schedule] == [0, 1]
    assert schedule[0]["action"] == "SELL"
    assert schedule[1]["action"] == "HOLD"
    assert schedule[0]["soc_before_kwh"] == 100.0
    assert schedule[0]["grid_export_kwh"] == 0.4
    assert schedule[0]["forecast_model_name"] == "promoted_model"
    assert schedule[0]["forecast_model_family"] == "random_forest_regressor"
    assert schedule[0]["forecast_horizon_mode"] == "conservative"
    assert schedule[0]["forecast_uncertainty_source"] == "walk_forward_residual_std"
    assert schedule[0]["forecast_promotion_active"] is True
    assert schedule[0]["forecast_promotion_source"] == "forecast_value_benchmark_asset"
    assert recommendation["action"] == "SELL"
    assert recommendation["confidence_percent"] == 90
    assert module._safe_float("bad", 1.5) == 1.5

    asset_file = tmp_path / "asset.bin"
    dagster_root = tmp_path / "dagster-home"
    monkeypatch.setattr(module, "_find_latest_asset_file", lambda project_root, asset_name: (asset_file, dagster_root))
    monkeypatch.setattr(module, "_load_pickled_asset", lambda path: rows)
    monkeypatch.setattr(sys, "argv", ["read_dagster_schedule.py", "--tenant-id", "tenant-a", "--project-root", str(tmp_path)])

    module.main()
    payload = json.loads(capsys.readouterr().out)

    assert payload["success"] is True
    assert payload["selected_client_id"] == "tenant-a"
    assert len(payload["schedule"]) == 2
    assert payload["schedule"][0]["forecast_model_name"] == "promoted_model"
    assert payload["schedule"][0]["forecast_promotion_active"] is True
    assert payload["recommendation"]["action"] == "SELL"


def test_find_latest_asset_file_falls_back_to_persistent_dagster_home(tmp_path: Path) -> None:
    module = load_script_module(
        "scripts.read_dagster_schedule_persistent_home_under_test",
        "scripts/read_dagster_schedule.py",
    )

    storage_root = tmp_path / "data" / "dagster_home" / "storage"
    storage_root.mkdir(parents=True)
    asset_path = storage_root / "optimization_schedule_asset"
    asset_path.write_bytes(b"demo")

    located = module._find_latest_asset_file(tmp_path, "optimization_schedule_asset")

    assert located == (asset_path, tmp_path / "data" / "dagster_home")


def test_read_dagster_schedule_main_reports_missing_asset(monkeypatch, capsys) -> None:
    module = load_script_module("scripts.read_dagster_schedule_missing_under_test", "scripts/read_dagster_schedule.py")
    monkeypatch.setattr(module, "_find_latest_asset_file", lambda project_root, asset_name: None)
    monkeypatch.setattr(sys, "argv", ["read_dagster_schedule.py", "--tenant-id", "tenant-a"])

    try:
        module.main()
    except SystemExit as exc:
        assert exc.code == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["success"] is False
    assert "No Dagster schedule assets found" in payload["error"]


def test_reconcile_optimization_history_computes_stats_and_main(monkeypatch, capsys) -> None:
    module = load_script_module(
        "scripts.reconcile_optimization_history_under_test",
        "scripts/reconcile_optimization_history.py",
        sqlalchemy_module=build_sqlalchemy_module(),
    )

    assert module.determine_tariff_window(datetime(2026, 3, 6, 8, 0, 0)) == "peak"
    assert module.determine_tariff_window(datetime(2026, 3, 6, 21, 0, 0)) == "shoulder"
    assert module.compute_canonical_costs(predicted_action=0, energy_kwh=4.0, unit_price_uah_kwh=10.0, peak_price=12.0, off_peak_price=6.0) == (40.0, 24.0)
    assert module._safe_number("nan") is None

    rows = [
        {
            "id": 1,
            "timestamp": datetime(2026, 3, 6, 10, 0, 0, tzinfo=timezone.utc),
            "predicted_action": 0,
            "cost_baseline": 0.0,
            "cost_rl": 0.0,
            "energy_kwh": 5.0,
            "price_uah_kwh": 10.0,
            "tariff_window": "offpeak",
            "economics_method": None,
        },
        {
            "id": 2,
            "timestamp": datetime(2026, 3, 6, 10, 0, 0, tzinfo=timezone.utc),
            "predicted_action": 1,
            "cost_baseline": 50.0,
            "cost_rl": 42.5,
            "energy_kwh": 5.0,
            "price_uah_kwh": 10.0,
            "tariff_window": "peak",
            "economics_method": None,
        },
        {
            "id": 3,
            "timestamp": datetime(2026, 3, 6, 4, 0, 0, tzinfo=timezone.utc),
            "predicted_action": 2,
            "cost_baseline": None,
            "cost_rl": None,
            "energy_kwh": 0.0,
            "price_uah_kwh": 10.0,
            "tariff_window": "offpeak",
            "economics_method": None,
        },
    ]
    updates = []

    class FakeResult:
        def __init__(self, items):
            self.items = items

        def mappings(self):
            return self

        def all(self):
            return self.items

    class FakeConn:
        def execute(self, query, params):
            if "SELECT" in query:
                return FakeResult(rows)
            updates.append(params)
            return None

    class FakeBegin:
        def __enter__(self):
            return FakeConn()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeBegin()

    monkeypatch.setattr(module, "create_engine", lambda *args, **kwargs: FakeEngine())
    monkeypatch.setenv("DATABASE_URL", "postgresql://demo")

    result = module.reconcile(days=14, limit=10, dry_run=False, note="test-note")

    assert result["success"] is True
    assert result["stats"] == {"scanned": 3, "eligible": 2, "updated": 1, "unchanged": 1, "skipped": 1}
    assert result["updated_ids"] == [1]
    assert updates[0]["reconciliation_note"] == "test-note"
    assert module.resolve_db_url() == "postgresql://demo"

    monkeypatch.setattr(module, "parse_args", lambda: SimpleNamespace(days=7, limit=5, dry_run=True, note="cli"))
    monkeypatch.setattr(module, "reconcile", lambda days, limit, dry_run, note: {"success": True, "days": days, "limit": limit, "dry_run": dry_run, "note": note})
    exit_code = module.main()
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"success": True, "days": 7, "limit": 5, "dry_run": True, "note": "cli"}



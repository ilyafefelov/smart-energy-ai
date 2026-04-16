from __future__ import annotations

import importlib.util
import json
import sys
import types
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class FakeSeries:
    def __init__(self, values):
        self.values = list(values)

    def to_list(self):
        return list(self.values)

    def __iter__(self):
        return iter(self.values)


class FakeSelection:
    def __init__(self, values):
        self.values = list(values)

    def to_series(self):
        return FakeSeries(self.values)

    def unique(self):
        seen = []
        for value in self.values:
            if value not in seen:
                seen.append(value)
        return FakeSelection(seen)


class FakeExpr:
    def __init__(self, column):
        self.column = column

    def __eq__(self, other):
        return lambda row: row.get(self.column) == other

    def is_null(self):
        return lambda row: row.get(self.column) is None


class FakePolarsFrame:
    def __init__(self, rows=None, schema=None):
        self.rows = [dict(row) for row in (rows or [])]
        self.schema = schema or {}
        if self.rows:
            self.columns = list(self.rows[0].keys())
        else:
            self.columns = list((schema or {}).keys())

    def __len__(self):
        return len(self.rows)

    def select(self, column):
        return FakeSelection([row.get(column) for row in self.rows])

    def filter(self, predicate):
        return FakePolarsFrame([row for row in self.rows if predicate(row)], schema=self.schema)

    def sort(self, columns):
        keys = columns if isinstance(columns, list) else [columns]
        return FakePolarsFrame(sorted(self.rows, key=lambda row: tuple(row.get(key) for key in keys)), schema=self.schema)

    def iter_rows(self, named=False):
        if named:
            for row in self.rows:
                yield dict(row)
        else:
            for row in self.rows:
                yield tuple(row.values())

    def to_dicts(self):
        return [dict(row) for row in self.rows]


def build_polars_module():
    module = types.ModuleType("polars")
    module.DataFrame = FakePolarsFrame
    module.Utf8 = "Utf8"
    module.Int64 = "Int64"
    module.Float64 = "Float64"
    module.DataType = object
    module.col = lambda column: FakeExpr(column)
    module.concat = lambda frames, how=None: FakePolarsFrame([row for frame in frames for row in frame.rows], schema=frames[0].schema if frames else {})
    return module


def build_dagster_module():
    module = types.ModuleType("dagster")
    module.asset = lambda *args, **kwargs: (lambda func: func)
    module.asset_check = lambda *args, **kwargs: (lambda func: func)
    module.AssetIn = lambda asset_key: {"asset_key": asset_key}
    module.AssetMaterialization = object
    module.MetadataValue = object

    class AssetCheckResult:
        def __init__(self, passed, severity, metadata):
            self.passed = passed
            self.severity = severity
            self.metadata = metadata

    class AssetCheckSeverity:
        ERROR = "ERROR"

    module.AssetCheckResult = AssetCheckResult
    module.AssetCheckSeverity = AssetCheckSeverity
    return module


def build_schedule_injected_modules():
    injected = {
        "polars": build_polars_module(),
        "dagster": build_dagster_module(),
        "yaml": __import__("yaml"),
    }

    src_pkg = types.ModuleType("src")
    src_pkg.__path__ = [str(REPO_ROOT / "src")]
    assets_pkg = types.ModuleType("src.assets")
    assets_pkg.__path__ = [str(REPO_ROOT / "src" / "assets")]
    core_pkg = types.ModuleType("src.assets.core")
    core_pkg.__path__ = [str(REPO_ROOT / "src" / "assets" / "core")]
    optimization_mod = types.ModuleType("src.optimization")

    class BaselineOptimizationConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class BaselineDPOptimizer:
        def __init__(self, config):
            self.config = config

        def optimize(self, price_eur_mwh, load_kw, solar_kw):
            schedule = []
            for hour, price in enumerate(price_eur_mwh):
                schedule.append(
                    {
                        "hour": hour,
                        "action_kw": 1.0 if hour == 0 else 0.0,
                        "charge_kwh": 0.0,
                        "discharge_kwh": 1.0 if hour == 0 else 0.0,
                        "soc_before_kwh": 100.0,
                        "soc_after_kwh": 99.0,
                        "throughput_total_kwh": float(hour + 1),
                        "price_eur_mwh": float(price),
                        "load_kwh": float(load_kw[hour]),
                        "solar_kwh": float(solar_kw[hour]),
                        "grid_import_kwh": 0.0,
                        "grid_export_kwh": 1.0 if hour == 0 else 0.0,
                        "purchase_cost_eur": 0.0,
                        "export_revenue_eur": 1.0,
                        "degradation_penalty_eur": 0.1,
                        "net_cost_eur": -0.9 if hour == 0 else 0.0,
                    }
                )
            return {
                "schedule": schedule,
                "objective": {"net_cost_eur": -0.9},
                "constraints": {"final_soc_kwh": 99.0, "throughput_limit_kwh": self.config.throughput_limit_kwh},
                "metadata": {"algorithm": "baseline_dp"},
            }

    optimization_mod.BaselineDPOptimizer = BaselineDPOptimizer
    optimization_mod.BaselineOptimizationConfig = BaselineOptimizationConfig

    milp_mod = types.ModuleType("src.assets.core.optimization_schedule_milp")
    milp_mod.optimization_schedule_milp_asset = "optimization_schedule_milp_asset"

    injected.update(
        {
            "src": src_pkg,
            "src.assets": assets_pkg,
            "src.assets.core": core_pkg,
            "src.optimization": optimization_mod,
            "src.assets.core.optimization_schedule_milp": milp_mod,
        }
    )
    return injected


def load_module(module_name: str, relative_path: str, injected_modules: dict[str, object]):
    module_path = REPO_ROOT / relative_path
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


def test_market_asset_helpers_and_flow(monkeypatch) -> None:
    module = load_module(
        "src.assets.core.market_under_test",
        "src/assets/core/market.py",
        injected_modules={"polars": build_polars_module(), "dagster": build_dagster_module()},
    )

    assert module._parse_hour_value("00:00-01:00") == 0
    assert module._parse_hour_value("23") == 23
    assert module._parse_decimal("1 234,5 грн") == 1234.5

    html = "<table><tr><th>Date</th><th>1</th><th>2</th></tr><tr><td>06.03.2026</td><td>1000</td><td>1200</td></tr></table>"
    rows = module._extract_prices_from_data_view_content(html, datetime(2026, 3, 6).date())
    assert len(rows) == 2
    assert rows[0]["price_uah_mwh"] == 1000.0
    assert rows[1]["timestamp"].hour == 1

    fetch_calls = {"count": 0}

    def fake_fetch_oree_prices(target_date):
        if fetch_calls["count"] == 0:
            fetch_calls["count"] += 1
            return [{"timestamp": datetime(2026, 3, 6, 0, 0), "price_eur_mwh": 25.0, "price_uah_mwh": 1000.0, "volume_mwh": 100.0, "source": "OREE"}]
        return []

    monkeypatch.setattr(module, "_fetch_oree_prices", fake_fetch_oree_prices)
    monkeypatch.setattr(module, "_validate_market_data", lambda df: df)
    df = module.market_data_asset()
    assert len(df) == 1
    assert df.rows[0]["source"] == "OREE"

    monkeypatch.setattr(module, "_fetch_oree_prices", lambda target_date: [])
    monkeypatch.setattr(module, "_generate_synthetic_prices", lambda: [{"timestamp": datetime(2026, 3, 6, 0, 0), "price_eur_mwh": 30.0, "price_uah_mwh": 1200.0, "volume_mwh": 100.0, "source": "SYNTHETIC"}])
    fallback_df = module.market_data_asset()
    assert fallback_df.rows[0]["source"] == "SYNTHETIC"


def test_optimization_schedule_helpers_and_asset(monkeypatch, tmp_path: Path) -> None:
    injected = build_schedule_injected_modules()
    module = load_module(
        "src.assets.core.optimization_schedule",
        "src/assets/core/optimization_schedule.py",
        injected_modules=injected,
    )

    monkeypatch.chdir(tmp_path)
    (tmp_path / "customers.yaml").write_text("customers:\n  - id: tenant-a\n    battery_capacity_kwh: 150\n", encoding="utf-8")

    capacities = module._load_client_capacities()
    assert capacities == {"tenant-a": 150.0}

    empty_df = module.build_empty_optimization_schedule()
    assert len(empty_df) == 0
    assert "client_id" in empty_df.columns

    schedule_df = module.build_optimization_schedule_frame([
        {"client_id": "tenant-a", "hour": 0, "action_kw": 1.0}
    ])
    assert schedule_df.rows[0]["client_id"] == "tenant-a"
    assert schedule_df.rows[0]["hour"] == 0

    price_forecast = FakePolarsFrame([
        {"predicted_price_eur_mwh": 50.0},
        {"predicted_price_eur_mwh": 55.0},
    ])
    client_state = FakePolarsFrame([
        {"client_id": "tenant-a", "timestamp": 1, "battery_soc": 60.0, "load_actual": 40.0, "solar_gen_actual": 5.0},
        {"client_id": "tenant-a", "timestamp": 2, "battery_soc": 62.0, "load_actual": 42.0, "solar_gen_actual": 6.0},
    ])
    context = types.SimpleNamespace(log=types.SimpleNamespace(info=lambda *args, **kwargs: None, warning=lambda *args, **kwargs: None))

    output = module.optimization_schedule_asset(context, price_forecast, client_state)
    assert len(output) == 2
    assert output.rows[0]["client_id"] == "tenant-a"
    assert output.rows[0]["algorithm"] == "baseline_dp"


def test_optimization_schedule_asset_uses_stage2_client_inputs(monkeypatch, tmp_path: Path) -> None:
    injected = build_schedule_injected_modules()
    module = load_module(
        "src.assets.core.optimization_schedule",
        "src/assets/core/optimization_schedule.py",
        injected_modules=injected,
    )

    captured = {}

    class CapturingOptimizer:
        def __init__(self, config):
            captured["config"] = config

        def optimize(self, price_eur_mwh, load_kw, solar_kw):
            schedule = []
            for hour, price in enumerate(price_eur_mwh):
                schedule.append(
                    {
                        "hour": hour,
                        "action_kw": 0.0,
                        "charge_kwh": 0.0,
                        "discharge_kwh": 0.0,
                        "soc_before_kwh": 100.0,
                        "soc_after_kwh": 100.0,
                        "throughput_total_kwh": 0.0,
                        "price_eur_mwh": float(price),
                        "load_kwh": float(load_kw[hour]),
                        "solar_kwh": float(solar_kw[hour]),
                        "grid_import_kwh": float(load_kw[hour]),
                        "grid_export_kwh": 0.0,
                        "purchase_cost_eur": 0.0,
                        "export_revenue_eur": 0.0,
                        "degradation_penalty_eur": 0.0,
                        "net_cost_eur": 0.0,
                    }
                )

            return {
                "schedule": schedule,
                "objective": {"net_cost_eur": 0.0},
                "constraints": {"final_soc_kwh": 100.0, "throughput_limit_kwh": captured["config"].throughput_limit_kwh},
                "metadata": {"algorithm": "baseline_dp"},
            }

    module.BaselineDPOptimizer = CapturingOptimizer

    monkeypatch.chdir(tmp_path)
    (tmp_path / "customers.yaml").write_text(
        "customers:\n"
        "  - id: tenant-a\n"
        "    market_regime_override: market_premium\n"
        "    energy_system:\n"
        "      battery_type: LFP\n"
        "      battery_capacity_kwh: 150\n"
        "      battery_efficiency: 0.88\n"
        "      battery_dod_max: 0.85\n"
        "      battery_soc_min: 0.2\n"
        "      connected_power_kw: 20\n",
        encoding="utf-8",
    )

    price_forecast = FakePolarsFrame([
        {"predicted_price_eur_mwh": 50.0},
        {"predicted_price_eur_mwh": 55.0},
    ])
    client_state = FakePolarsFrame([
        {"client_id": "tenant-a", "timestamp": 1, "battery_soc": 60.0, "load_actual": 40.0, "solar_gen_actual": 5.0},
        {"client_id": "tenant-a", "timestamp": 2, "battery_soc": 62.0, "load_actual": 42.0, "solar_gen_actual": 6.0},
    ])
    context = types.SimpleNamespace(log=types.SimpleNamespace(info=lambda *args, **kwargs: None, warning=lambda *args, **kwargs: None))

    module.optimization_schedule_asset(context, price_forecast, client_state)

    config = captured["config"]
    assert config.min_soc_fraction == 0.2
    assert config.roundtrip_efficiency == 0.88
    assert config.max_charge_kw == 20.0
    assert config.max_discharge_kw == 20.0
    assert config.export_price_factor == 1.0
    assert config.degradation_cost_per_kwh > 0.01


def test_optimization_schedule_checks_evaluate_contracts() -> None:
    injected = build_schedule_injected_modules()
    optimization_module = load_module(
        "src.assets.core.optimization_schedule",
        "src/assets/core/optimization_schedule.py",
        injected_modules=injected,
    )
    injected["src.assets.core.optimization_schedule"] = optimization_module
    checks_module = load_module(
        "src.assets.core.optimization_schedule_checks",
        "src/assets/core/optimization_schedule_checks.py",
        injected_modules=injected,
    )

    valid_schedule = FakePolarsFrame([
        {
            "client_id": "tenant-a",
            "hour": hour,
            "action_kw": 1.0 if hour == 0 else 0.0,
            "charge_kwh": 0.0,
            "discharge_kwh": 1.0 if hour == 0 else 0.0,
            "price_eur_mwh": 50.0,
        }
        for hour in range(24)
    ])

    completeness = checks_module.evaluate_schedule_completeness(valid_schedule)
    numeric = checks_module.evaluate_schedule_numeric_fields(valid_schedule)
    semantics = checks_module.evaluate_schedule_action_semantics(valid_schedule)

    assert completeness["passed"] is True
    assert numeric["passed"] is True
    assert semantics["passed"] is True

    invalid_schedule = FakePolarsFrame([
        {"client_id": "tenant-a", "hour": 0, "action_kw": 0.5, "charge_kwh": 1.0, "discharge_kwh": 1.0, "price_eur_mwh": None}
    ])
    invalid_numeric = checks_module.evaluate_schedule_numeric_fields(invalid_schedule)
    invalid_semantics = checks_module.evaluate_schedule_action_semantics(invalid_schedule)
    result = checks_module.optimization_schedule_numeric_fields_check(invalid_schedule)

    assert invalid_numeric["passed"] is False
    assert invalid_semantics["passed"] is False
    assert result.passed is False
    assert len(checks_module.optimization_schedule_contract_checks) == 6
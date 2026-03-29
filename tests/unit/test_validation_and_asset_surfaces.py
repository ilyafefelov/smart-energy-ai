from __future__ import annotations

import builtins
import importlib.util
import io
import sys
import types
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(module_name: str, relative_path: str, injected_modules: dict[str, object] | None = None):
    module_path = REPO_ROOT / relative_path
    previous = {}
    injected_modules = injected_modules or {}

    for name, module in injected_modules.items():
        previous[name] = sys.modules.get(name)
        sys.modules[name] = module

    try:
        if module_path.name == "__init__.py":
            spec = importlib.util.spec_from_file_location(
                module_name,
                module_path,
                submodule_search_locations=[str(module_path.parent)],
            )
        else:
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


def build_validation_modules():
    injected = {}

    energy_ml_pkg = types.ModuleType("energy_ml")
    energy_ml_pkg.__path__ = [str(REPO_ROOT / "energy_ml")]
    pipeline_mod = types.ModuleType("energy_ml.pipeline")
    pipeline_mod.PipelineOrchestrator = type("PipelineOrchestrator", (), {})

    mlops_pkg = types.ModuleType("energy_ml.mlops")
    mlops_pkg.__path__ = []
    optimization_mod = types.ModuleType("energy_ml.mlops.optimization_engine")
    battery_mod = types.ModuleType("energy_ml.mlops.battery_physics")
    renewable_mod = types.ModuleType("energy_ml.mlops.renewable_forecasting")

    class OptimizationEngine:
        def optimize_decision(self, **kwargs):
            return {"action": "SELL", "confidence": 0.88}

    class BatteryPhysicsEngine:
        def get_battery_physics_data(self, config):
            return {"chemistry": config["battery_type"], "current_state": {"soc_percent": config["battery_soc"]}}

    class RenewableForecaster:
        pass

    optimization_mod.OptimizationEngine = OptimizationEngine
    battery_mod.BatteryPhysicsEngine = BatteryPhysicsEngine
    renewable_mod.RenewableForecaster = RenewableForecaster

    assets_pkg = types.ModuleType("energy_ml.assets")
    assets_pkg.__path__ = []
    assets_pipeline_mod = types.ModuleType("energy_ml.assets.pipeline")
    assets_pipeline_mod.optimization_preferences_asset = object()

    energy_ml_pkg.pipeline = pipeline_mod
    energy_ml_pkg.mlops = mlops_pkg
    energy_ml_pkg.assets = assets_pkg
    mlops_pkg.optimization_engine = optimization_mod
    mlops_pkg.battery_physics = battery_mod
    mlops_pkg.renewable_forecasting = renewable_mod
    assets_pkg.pipeline = assets_pipeline_mod

    injected.update(
        {
            "energy_ml": energy_ml_pkg,
            "energy_ml.pipeline": pipeline_mod,
            "energy_ml.mlops": mlops_pkg,
            "energy_ml.mlops.optimization_engine": optimization_mod,
            "energy_ml.mlops.battery_physics": battery_mod,
            "energy_ml.mlops.renewable_forecasting": renewable_mod,
            "energy_ml.assets": assets_pkg,
            "energy_ml.assets.pipeline": assets_pipeline_mod,
        }
    )
    return injected


def build_asset_dependency_modules():
    dagster_mod = types.ModuleType("dagster")
    dagster_mod.asset = lambda *args, **kwargs: (lambda func: func)
    dagster_mod.repository = lambda func: func
    dagster_mod.AssetIn = lambda asset_key: {"asset_key": asset_key}
    dagster_mod.MetadataValue = object

    class FakePolarsFrame:
        def __init__(self, rows):
            self.rows = rows if isinstance(rows, list) else []

        def to_dicts(self):
            return list(self.rows)

        def __len__(self):
            return len(self.rows)

    polars_mod = types.ModuleType("polars")
    polars_mod.DataFrame = FakePolarsFrame

    mlflow_mod = types.ModuleType("mlflow")
    records = {"params": [], "metrics": [], "tags": [], "uri": None, "runs": []}

    class RunContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    mlflow_mod.set_tracking_uri = lambda uri: records.__setitem__("uri", uri)
    mlflow_mod.start_run = lambda run_name=None: records["runs"].append(run_name) or RunContext()
    mlflow_mod.log_param = lambda name, value: records["params"].append((name, value))
    mlflow_mod.log_metric = lambda name, value: records["metrics"].append((name, value))
    mlflow_mod.set_tag = lambda name, value: records["tags"].append((name, value))
    mlflow_mod._records = records

    numpy_mod = types.ModuleType("numpy")

    return {
        "dagster": dagster_mod,
        "polars": polars_mod,
        "mlflow": mlflow_mod,
        "numpy": numpy_mod,
    }


def build_repository_injected_modules():
    injected = build_asset_dependency_modules()

    src_pkg = types.ModuleType("src")
    assets_pkg = types.ModuleType("src.assets")
    core_pkg = types.ModuleType("src.assets.core")
    benchmarks_pkg = types.ModuleType("src.assets.benchmarks")
    injected.update(
        {
            "src": src_pkg,
            "src.assets": assets_pkg,
            "src.assets.core": core_pkg,
            "src.assets.benchmarks": benchmarks_pkg,
        }
    )

    names = {
        "src.assets.core.market": "market_data_asset",
        "src.assets.core.weather": "weather_asset",
        "src.assets.core.client_state": "client_state_asset",
        "src.assets.core.feature_matrix": "feature_matrix_asset",
        "src.assets.core.price_forecast": "price_forecast_asset",
        "src.assets.core.optimization_schedule": "optimization_schedule_asset",
        "src.assets.core.optimization_schedule_milp": "optimization_schedule_milp_asset",
        "src.assets.benchmarks.performance": [
            "engine_benchmark_asset",
            "accuracy_benchmark_asset",
            "mlflow_tracking_asset",
        ],
    }
    for module_name, attr_names in names.items():
        module = types.ModuleType(module_name)
        if isinstance(attr_names, list):
            for attr in attr_names:
                setattr(module, attr, attr)
        else:
            setattr(module, attr_names, attr_names)
        injected[module_name] = module

    return injected


def test_validation_check_reports_imports_functionality_and_apis(monkeypatch, capsys) -> None:
    module = load_module(
        "scripts.validation_check_under_test",
        "scripts/validation_check.py",
        injected_modules=build_validation_modules(),
    )

    fake_subprocess = types.ModuleType("subprocess")
    fake_subprocess.run = lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout='{"success": true, "strategy": "balanced"}', stderr="")
    monkeypatch.setitem(sys.modules, "subprocess", fake_subprocess)
    monkeypatch.setattr(module.Path, "exists", lambda self: True)
    monkeypatch.setattr(module.Path, "read_text", lambda self: "export default defineEventHandler(() => ({ status: 'ok', message: 'x' * 120 }))" + ("a" * 120))

    imports = module.check_imports()
    functionality = module.check_functionality()
    apis = module.check_dashboard_apis()

    assert imports["PipelineOrchestrator"].startswith("❌ ERROR:")
    assert "energy_ml.energy_ml" in imports["PipelineOrchestrator"]
    assert functionality["Optimization Decision"].startswith("❌ ERROR:")
    assert "energy_ml.energy_ml" in functionality["Optimization Decision"]
    assert functionality["Battery Physics"].startswith("❌ ERROR:")
    assert functionality["API Integration"].startswith("✅")
    assert all(status.startswith("✅") for status in apis.values())

    module.main()
    output = capsys.readouterr().out
    assert "SUMMARY" in output
    assert "MOSTLY WORKING" in output or "SIGNIFICANT ISSUES DETECTED" in output


def test_assets_repository_returns_expected_assets() -> None:
    module = load_module(
        "src.assets",
        "src/assets/__init__.py",
        injected_modules=build_repository_injected_modules(),
    )

    assets = module.assets_repository()

    assert "market_data_asset" in assets
    assert "optimization_schedule_asset" in assets
    assert "mlflow_tracking_asset" in assets
    assert len(assets) == 10


def test_benchmark_performance_helpers_and_tracking(monkeypatch, capsys) -> None:
    injected = build_asset_dependency_modules()
    physics_pkg = types.ModuleType("physics")
    economics_mod = types.ModuleType("physics.economics")

    class BatteryTechnology:
        LFP = "LFP"
        NMC = "NMC"

    class OperationProfile:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class EconomicModel:
        def __init__(self, technology, capacity_kwh):
            self.technology = technology
            self.capacity_kwh = capacity_kwh

        def calculate_lcos(self, profile):
            return {"lcos_usd_per_kwh": 0.08 if self.capacity_kwh == 100.0 else 0.06}

        def calculate_arbitrage_value(self, spreads, profile):
            return {"annual_net_value": 50.0 if self.capacity_kwh == 100.0 else 200.0}

    economics_mod.BatteryTechnology = BatteryTechnology
    economics_mod.OperationProfile = OperationProfile
    economics_mod.EconomicModel = EconomicModel
    injected.update({"physics": physics_pkg, "physics.economics": economics_mod})

    module = load_module(
        "src.assets.benchmarks.performance_under_test",
        "src/assets/benchmarks/performance.py",
        injected_modules=injected,
    )
    monkeypatch.setitem(sys.modules, "physics", physics_pkg)
    monkeypatch.setitem(sys.modules, "physics.economics", economics_mod)

    monkeypatch.setattr(module, "_ensure_src_in_path", lambda: None)

    class Engine:
        def process_energy_features(self, data):
            return [{"row": 1}, {"row": 2}]

    success_metrics = module._benchmark_engine(Engine(), [{"row": 1}], "polars", 1)
    assert success_metrics["success"] is True
    assert success_metrics["output_rows"] == 2

    class BrokenEngine:
        def process_energy_features(self, data):
            raise RuntimeError("boom")

    failure_metrics = module._benchmark_engine(BrokenEngine(), [{"row": 1}], "broken", 1)
    assert failure_metrics["success"] is False
    assert failure_metrics["error_message"] == "boom"

    scenarios = module._create_economic_test_scenarios()
    assert scenarios[0]["name"] == "standard_lfp_system"
    assert len(scenarios) == 3

    engine_frame = module.pl.DataFrame(
        [
            {
                "engine_name": "polars",
                "data_size": 100,
                "processing_time_seconds": 1.2,
                "memory_peak_mb": 30.0,
                "throughput_records_per_second": 83.3,
                "success": True,
                "benchmark_timestamp": datetime(2026, 3, 6, 12, 0, 0),
            }
        ]
    )
    accuracy_frame = module.pl.DataFrame(
        [
            {
                "scenario_name": "standard_lfp_system",
                "metric_type": "lcos",
                "expected_value": 0.08,
                "calculated_value": 0.08,
                "absolute_error": 0.0,
                "relative_error_percent": 0.0,
                "success": True,
                "benchmark_timestamp": datetime(2026, 3, 6, 12, 0, 0),
            }
        ]
    )
    tracking = module.mlflow_tracking_asset(engine_frame, accuracy_frame)
    assert len(tracking) == 2
    assert module.mlflow._records["uri"] == "http://localhost:5000"
    assert module.mlflow._records["runs"] == ["polars_size_100", "standard_lfp_system_lcos"]

    monkeypatch.setattr(module, "engine_benchmark_asset", lambda market, weather: [1, 2])
    monkeypatch.setattr(module, "accuracy_benchmark_asset", lambda market: [1])
    module.test_benchmark_assets()
    output = capsys.readouterr().out
    assert "Benchmark tests complete" in output
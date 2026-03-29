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


def load_dagster_integration_module():
    module_path = Path(__file__).resolve().parents[2] / "energy_ml" / "optimizer" / "dagster_integration.py"
    package = types.ModuleType("energy_ml")
    package.__path__ = [str(module_path.parents[1])]
    optimizer_package = types.ModuleType("energy_ml.optimizer")
    optimizer_package.__path__ = [str(module_path.parent)]
    dagster = types.ModuleType("dagster")
    dagster.op = lambda fn: fn

    sys.modules.setdefault("energy_ml", package)
    sys.modules.setdefault("energy_ml.optimizer", optimizer_package)
    sys.modules["dagster"] = dagster

    return load_module("energy_ml.optimizer.dagster_integration", module_path)


def load_run_optimization_module():
    module_path = Path(__file__).resolve().parents[2] / "energy_ml" / "optimizer" / "run_optimization.py"
    package = types.ModuleType("energy_ml")
    package.__path__ = [str(module_path.parents[1])]
    optimizer_package = types.ModuleType("energy_ml.optimizer")
    optimizer_package.__path__ = [str(module_path.parent)]
    ml_star_optimizer = types.ModuleType("energy_ml.optimizer.ml_star_optimizer")

    class OptimizationConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class MLSTAROptimizer:
        def __init__(self, X, y, config):
            self.X = X
            self.y = y
            self.config = config
            self.final_reports = {
                "comprehensive": {
                    "best_accuracy": 0.84,
                    "improvement_percentage": 15.8,
                    "hyperparameter_search_results": {"best_cv_score": 0.81},
                    "feature_importance": {f"feature_{index}": 1.0 / (index + 1) for index in range(12)},
                }
            }
            self.ablation_study = SimpleNamespace(
                get_ranking=lambda: pd.DataFrame(
                    [{"component": "Voting Ensemble", "accuracy": 0.84}]
                )
            )

        def run_optimization_pipeline(self):
            return {
                "baseline_accuracy": 0.725,
                "best_accuracy": 0.84,
                "improvement_percentage": 15.8,
                "best_model": "voting_soft",
            }

    def generate_sota_report():
        return pd.DataFrame(
            [
                {
                    "rank": 1,
                    "name": "soft voting ensemble",
                    "expected_improvement": "3-5%",
                    "reasoning": "Combines complementary tree models.",
                    "implementation": "Use soft voting across tuned base learners.",
                    "pros": ["stable", "strong accuracy"],
                    "cons": ["more memory"],
                    "inference_time_ms": 15,
                    "memory_mb": 50,
                }
            ]
        )

    ml_star_optimizer.MLSTAROptimizer = MLSTAROptimizer
    ml_star_optimizer.OptimizationConfig = OptimizationConfig
    ml_star_optimizer.SOTA_TECHNIQUES = []
    ml_star_optimizer.generate_sota_report = generate_sota_report

    sys.modules.setdefault("energy_ml", package)
    sys.modules.setdefault("energy_ml.optimizer", optimizer_package)
    sys.modules["energy_ml.optimizer.ml_star_optimizer"] = ml_star_optimizer

    return load_module("energy_ml.optimizer.run_optimization", module_path)


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


dagster_integration_module = load_dagster_integration_module()
run_optimization_module = load_run_optimization_module()
pipeline_module = load_pipeline_module()


def test_initialize_ml_star_optimizer_returns_expected_defaults():
    result = dagster_integration_module.initialize_ml_star_optimizer({"n_trials": 25, "output_dir": "out"})

    assert result["n_trials"] == 25
    assert result["n_splits"] == 5
    assert result["output_dir"] == "out"
    assert result["ensemble_strategies"] == ["voting", "stacking"]
    assert "timestamp" in result


def test_op_load_training_data_rejects_missing_columns(tmp_path):
    dataset_path = tmp_path / "train.csv"
    pd.DataFrame({"feature_a": [1.0], "feature_b": [2.0]}).to_csv(dataset_path, index=False)

    with pytest.raises(ValueError, match="Missing columns"):
        dagster_integration_module.op_load_training_data(str(dataset_path), ["feature_a"], "target")


def test_op_save_optimization_results_writes_summary_files(tmp_path):
    output_paths = dagster_integration_module.op_save_optimization_results(
        baseline_result={"model": {"kind": "baseline"}, "test_accuracy": 0.82, "cv_mean": 0.8, "cv_std": 0.05},
        ensemble_results={"voting": {"model": {"kind": "voting"}, "accuracy": 0.85}},
        safety_results={
            "data_leakage": {"leakage_detected": False},
            "overfitting": {"overfitting_risk": "LOW"},
            "reproducibility": {"status": "OK"},
            "all_passed": True,
        },
        ablation_ranking=pd.DataFrame([{"component": "Voting Ensemble", "accuracy": 0.85}]),
        output_dir=str(tmp_path),
    )

    assert Path(output_paths["baseline_model_path"]).exists()
    assert Path(output_paths["summary_path"]).exists()
    assert Path(output_paths["ablation_path"]).exists()
    assert Path(output_paths["safety_report_path"]).exists()


def test_generate_sample_data_uses_requested_feature_width_and_class_mapping():
    features, labels, class_names = run_optimization_module.generate_sample_data(n_samples=200, n_features=73)

    assert features.shape == (200, 73)
    assert labels.shape == (200,)
    assert labels.value_counts().sum() == 200
    assert features.columns[-1] == "engineered_feature_72"
    assert class_names[3] == "DISCHARGE"


def test_run_optimization_pipeline_returns_report_and_optimizer_instance():
    features, labels, _ = run_optimization_module.generate_sample_data(n_samples=60, n_features=10)

    report, optimizer = run_optimization_module.run_optimization_pipeline(features, labels)

    assert report["best_model"] == "voting_soft"
    assert optimizer.final_reports["comprehensive"]["best_accuracy"] == 0.84


def test_save_all_deliverables_writes_expected_artifacts(tmp_path):
    run_optimization_module.save_all_deliverables(
        sota_report="sota report",
        implementation_code="print('ok')",
        optimization_report={"best_accuracy": 0.84},
        safety_report={"status": "ok"},
        ablation_study=pd.DataFrame([{"component": "Voting Ensemble", "accuracy": 0.84}]),
        output_dir=str(tmp_path),
    )

    assert (tmp_path / "1_SOTA_TECHNIQUES_ANALYSIS.txt").read_text() == "sota report"
    assert (tmp_path / "4_PRODUCTION_IMPLEMENTATION.py").read_text() == "print('ok')"
    assert (tmp_path / "5_SAFETY_VALIDATION_REPORT.json").exists()
    assert (tmp_path / "3_ABLATION_STUDY.csv").exists()


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
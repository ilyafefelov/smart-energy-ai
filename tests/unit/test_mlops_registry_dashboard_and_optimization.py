import importlib.util
import sys
import types
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]


def _ensure_packages() -> None:
    energy_ml = sys.modules.get("energy_ml")
    if energy_ml is None:
        energy_ml = types.ModuleType("energy_ml")
        energy_ml.__path__ = [str(ROOT / "energy_ml")]
        sys.modules["energy_ml"] = energy_ml

    mlops = sys.modules.get("energy_ml.mlops")
    if mlops is None:
        mlops = types.ModuleType("energy_ml.mlops")
        mlops.__path__ = [str(ROOT / "energy_ml" / "mlops")]
        sys.modules["energy_ml.mlops"] = mlops


def _load_module(module_name: str, relative_path: str, injected_modules: dict[str, types.ModuleType] | None = None):
    _ensure_packages()
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


_load_module("energy_ml.config_models", "energy_ml/config_models.py")
USER_CONFIG_MODULE = _load_module("energy_ml.user_config", "energy_ml/user_config.py")
OPTIMIZATION_MODULE = _load_module("energy_ml.mlops.optimization_engine", "energy_ml/mlops/optimization_engine.py")
MODEL_REGISTRY = _load_module("energy_ml.mlops.model_registry", "energy_ml/mlops/model_registry.py")


@dataclass
class FakePerformance:
    mape: float = 9.5
    rmse: float = 1.2
    mae: float = 0.8
    r2_score: float = 0.91
    prediction_count: int = 240
    latency_p95_ms: float = 120.0
    error_rate: float = 1.0
    timestamp: datetime = datetime(2026, 3, 6, 12, 0, 0)


def _load_monitoring_dashboard_module():
    retraining_pipeline_module = types.ModuleType("energy_ml.mlops.retraining_pipeline")
    model_registry_module = types.ModuleType("energy_ml.mlops.model_registry")

    class FakeRegistry:
        def list_model_versions(self, model_name, stage=None):
            if stage == "production":
                return [
                    types.SimpleNamespace(
                        version_id="energy_optimizer-v1",
                        created_at=datetime(2026, 3, 1, 9, 0, 0),
                        health_status="healthy",
                        performance_metrics={"test_mape": 8.5},
                    )
                ]
            if stage == "staging":
                return []
            return []

    class FakeMonitor:
        def __init__(self):
            self.recent_predictions = [1, 2, 3]

        def calculate_performance_metrics(self, version_id):
            return FakePerformance()

    class FakeRetrainingPipeline:
        def __init__(self):
            self.monitor = FakeMonitor()
            self.feature_store = types.SimpleNamespace(feature_views={"energy_features": object()})

        def check_retraining_triggers(self):
            return {
                "should_retrain": False,
                "reasons": [],
                "last_training_age_hours": 12,
                "performance_degraded": False,
                "drift_detected": False,
            }

    class FakeABTestManager:
        def __init__(self):
            self.active_tests = {
                "test-a": {
                    "status": "active",
                    "control_version": "v1",
                    "treatment_version": "v2",
                    "traffic_split": 20,
                    "start_time": "2026-03-01T00:00:00",
                    "end_time": "2026-03-10T00:00:00",
                }
            }

    retraining_pipeline_module.ModelMonitor = object
    retraining_pipeline_module.DriftDetector = object
    retraining_pipeline_module.get_retraining_pipeline = lambda: FakeRetrainingPipeline()
    retraining_pipeline_module.get_ab_test_manager = lambda: FakeABTestManager()
    model_registry_module.get_model_registry = lambda: FakeRegistry()

    return _load_module(
        "energy_ml.mlops.monitoring_dashboard",
        "energy_ml/mlops/monitoring_dashboard.py",
        {
            "energy_ml.mlops.retraining_pipeline": retraining_pipeline_module,
            "energy_ml.mlops.model_registry": model_registry_module,
        },
    )


MONITORING_MODULE = _load_monitoring_dashboard_module()


class DummyRegressor:
    feature_importances_ = np.array([0.7, 0.3])

    def predict(self, X):
        arr = np.asarray(X)
        return arr.sum(axis=1)


def test_model_registry_registers_and_promotes_healthy_model(tmp_path):
    registry = MODEL_REGISTRY.ModelRegistry(registry_path=str(tmp_path / "registry"))
    model = DummyRegressor()
    validation_data = {
        "X": np.array([[1.0, 2.0], [2.0, 3.0]]),
        "y": np.array([3.0, 5.0]),
    }

    version = registry.register_model(
        model=model,
        model_name="energy_optimizer",
        algorithm="dummy",
        performance_metrics={"mape": 0.05},
        feature_schema=["f1", "f2"],
        validation_data=validation_data,
    )

    assert version.health_status == "healthy"
    assert registry.promote_to_staging(version.version_id) is True
    listed = registry.list_model_versions("energy_optimizer")
    assert listed[0].deployment_stage == "staging"


def test_optimization_engine_respects_strategy_constraints(monkeypatch):
    engine = OPTIMIZATION_MODULE.OptimizationEngine()

    class PeakDatetime:
        @staticmethod
        def now():
            return datetime(2026, 3, 6, 12, 0, 0)

    monkeypatch.setattr(OPTIMIZATION_MODULE, "datetime", PeakDatetime)

    result = engine.optimize_decision(
        base_prediction={"action": "SELL", "confidence": 0.6, "reasoning": "base"},
        strategy="max_charge",
        physics_data={"status": "success", "simulation_results": {"current_soc": 50.0}},
        renewable_data=None,
        weights={"earnings": 1.0, "battery_health": 0.0, "charge_availability": 0.0},
    )

    assert result["action"] == "HOLD"
    assert result["constraints_met"] is False
    assert "SOC too low" in result["constraint_message"]


def test_alert_manager_avoids_duplicate_unacknowledged_alerts(tmp_path):
    manager = MONITORING_MODULE.AlertManager(alerts_path=str(tmp_path / "alerts"))
    performance = {"mape": 30.0, "latency_p95_ms": 600.0, "error_rate": 12.0, "model_version": "v1"}

    first = manager.check_alerts(performance)
    second = manager.check_alerts(performance)

    assert len(first) >= 3
    assert second == []
    assert len(manager.get_active_alerts()) == len(first)


def test_monitoring_dashboard_builds_summary_from_stubs():
    dashboard = MONITORING_MODULE.MonitoringDashboard()

    data = dashboard.get_dashboard_data()

    assert data["model_status"]["production"]["version"] == "energy_optimizer-v1"
    assert data["performance_metrics"]["mape"] == 9.5
    assert data["alerts"]["total_active"] == 0
    assert data["system_health"]["overall_status"] == "healthy"


def test_monitor_energy_model_returns_metrics_envelope():
    result = MONITORING_MODULE.monitor_energy_model()

    assert result["retraining_recommended"] is False
    assert result["metrics"]["prediction_accuracy"] == 9.5
    assert "timestamp" in result
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import types


class DummyBatteryPhysicsEngine:
    def __init__(self, *_args, **_kwargs):
        self.current_model = SimpleNamespace(state=SimpleNamespace())


class DummyOptimizationEngine:
    def __init__(self, *_args, **_kwargs):
        pass


class DummyStrategy:
    def __init__(self, value):
        self.value = value


class DummyModelRegistry:
    def get_production_model(self):
        return None

    def list_model_versions(self, *_args, **_kwargs):
        return []


class DummyFeatureStore:
    feature_views = {}


class DummyMonitoringDashboard:
    monitor = SimpleNamespace(log_prediction=lambda **_kwargs: None)


class DummyRetrainingPipeline:
    def check_retraining_triggers(self):
        return {"should_retrain": False, "reasons": []}


def load_serving_api_class():
    module_path = Path(__file__).resolve().parents[2] / "energy_ml" / "mlops" / "serving_api.py"
    package = types.ModuleType("energy_ml")
    package.__path__ = [str(module_path.parents[1])]
    mlops_package = types.ModuleType("energy_ml.mlops")
    mlops_package.__path__ = [str(module_path.parent)]

    sys.modules.setdefault("energy_ml", package)
    sys.modules.setdefault("energy_ml.mlops", mlops_package)

    model_registry = types.ModuleType("energy_ml.mlops.model_registry")
    model_registry.get_model_registry = lambda: DummyModelRegistry()
    feature_store = types.ModuleType("energy_ml.mlops.feature_store")
    feature_store.get_feature_store = lambda: DummyFeatureStore()
    battery_physics = types.ModuleType("energy_ml.mlops.battery_physics")
    battery_physics.BatteryPhysicsEngine = DummyBatteryPhysicsEngine
    optimization_engine = types.ModuleType("energy_ml.mlops.optimization_engine")
    optimization_engine.OptimizationEngine = DummyOptimizationEngine
    optimization_engine.OptimizationStrategy = [DummyStrategy("balanced")]
    monitoring_dashboard = types.ModuleType("energy_ml.mlops.monitoring_dashboard")
    monitoring_dashboard.get_monitoring_dashboard = lambda: DummyMonitoringDashboard()
    monitoring_dashboard.monitor_energy_model = lambda: {}
    retraining_pipeline = types.ModuleType("energy_ml.mlops.retraining_pipeline")
    retraining_pipeline.get_retraining_pipeline = lambda: DummyRetrainingPipeline()
    retraining_pipeline.get_ab_test_manager = lambda: SimpleNamespace(active_tests={})

    sys.modules["energy_ml.mlops.model_registry"] = model_registry
    sys.modules["energy_ml.mlops.feature_store"] = feature_store
    sys.modules["energy_ml.mlops.battery_physics"] = battery_physics
    sys.modules["energy_ml.mlops.optimization_engine"] = optimization_engine
    sys.modules["energy_ml.mlops.monitoring_dashboard"] = monitoring_dashboard
    sys.modules["energy_ml.mlops.retraining_pipeline"] = retraining_pipeline

    spec = importlib.util.spec_from_file_location("energy_ml.mlops.serving_api", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    import asyncio

    original_create_task = asyncio.create_task

    def discard_task(coro):
        coro.close()
        return None

    asyncio.create_task = discard_task
    try:
        spec.loader.exec_module(module)
    finally:
        asyncio.create_task = original_create_task
    return module.MLServingAPI


MLServingAPI = load_serving_api_class()


class ExplodingRegistry:
    def list_model_versions(self, *_args, **_kwargs):
        raise RuntimeError("registry unavailable")


class ExplodingFeatureStore:
    @property
    def feature_views(self):
        raise RuntimeError("feature store unavailable")


def make_api_with_dependencies(model_registry, feature_store):
    api = MLServingAPI.__new__(MLServingAPI)
    api.model_registry = model_registry
    api.feature_store = feature_store
    return api


def test_check_model_registry_returns_false_for_none_versions():
    api = make_api_with_dependencies(
        SimpleNamespace(list_model_versions=lambda *_args, **_kwargs: None),
        SimpleNamespace(feature_views={}),
    )

    assert api._check_model_registry() is False


def test_check_model_registry_returns_false_on_exception():
    api = make_api_with_dependencies(ExplodingRegistry(), SimpleNamespace(feature_views={}))

    assert api._check_model_registry() is False


def test_check_feature_store_returns_false_for_missing_views():
    api = make_api_with_dependencies(
        SimpleNamespace(list_model_versions=lambda *_args, **_kwargs: []),
        SimpleNamespace(),
    )

    assert api._check_feature_store() is False


def test_check_feature_store_returns_false_on_exception():
    api = make_api_with_dependencies(
        SimpleNamespace(list_model_versions=lambda *_args, **_kwargs: []),
        ExplodingFeatureStore(),
    )

    assert api._check_feature_store() is False


def test_health_check_helpers_return_true_when_backends_are_ready():
    api = make_api_with_dependencies(
        SimpleNamespace(list_model_versions=lambda *_args, **_kwargs: ["v1"]),
        SimpleNamespace(feature_views={"energy_features": object()}),
    )

    assert api._check_model_registry() is True
    assert api._check_feature_store() is True
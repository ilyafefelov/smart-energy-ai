import asyncio
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import types

from fastapi import FastAPI
from fastapi.testclient import TestClient


class DummyBatteryPhysicsEngine:
    CHEMISTRY_PARAMS = {"LFP": {}, "Lead-Acid": {}, "VRFB": {}}

    def __init__(self, *_args, **_kwargs):
        pass

    def simulate_battery_behavior(self, *_args, **_kwargs):
        return {
            "chemistry": "LFP",
            "current_state": {"soc_percent": 60.0, "cycles_completed": 1000, "temperature": 25.0},
            "power_limits": {"max_charge_power_kw": 4.0, "max_discharge_power_kw": 5.0},
            "efficiency_model": {"charge_efficiency": 0.95, "discharge_efficiency": 0.9},
            "physics_constraints": {"min_soc_physics": 10.0, "max_soc_physics": 100.0},
            "degradation_model": {},
            "thermal_model": {},
        }


class DummyOptimizationEngine:
    OPTIMIZATION_STRATEGIES = {"balanced": {}, "max_earn": {}, "max_battery_health": {}, "max_charge": {}}

    def __init__(self, *_args, **_kwargs):
        pass

    def optimize_decision(self, base_prediction, strategy, physics_data=None, renewable_data=None, weights=None):
        return {
            **base_prediction,
            "optimization_strategy": strategy,
        }


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
    monitoring_dashboard = types.ModuleType("energy_ml.mlops.monitoring_dashboard")
    monitoring_dashboard.get_monitoring_dashboard = lambda: DummyMonitoringDashboard()
    monitoring_dashboard.monitor_energy_model = lambda: {}
    retraining_pipeline = types.ModuleType("energy_ml.mlops.retraining_pipeline")
    retraining_pipeline.get_retraining_pipeline = lambda: DummyRetrainingPipeline()
    retraining_pipeline.get_ab_test_manager = lambda: SimpleNamespace(
        active_tests={},
        route_prediction=lambda *_args, **_kwargs: "production",
        log_ab_result=lambda **_kwargs: None,
    )

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


def build_route_test_api(cached_model=None, feature_store=None, optimization_engine=None, physics_engine=None, ab_test_manager=None):
    api = MLServingAPI.__new__(MLServingAPI)
    api.app = FastAPI()
    api.model_registry = DummyModelRegistry()
    api.feature_store = feature_store or SimpleNamespace(load_online_features=lambda *_args, **_kwargs: {})
    api.monitoring_dashboard = DummyMonitoringDashboard()
    api.retraining_pipeline = DummyRetrainingPipeline()
    api.ab_test_manager = ab_test_manager or SimpleNamespace(
        active_tests={},
        route_prediction=lambda *_args, **_kwargs: "production",
        log_ab_result=lambda **_kwargs: None,
    )
    api.physics_engines = {
        "LFP": physics_engine or DummyBatteryPhysicsEngine(),
        "Lead-Acid": physics_engine or DummyBatteryPhysicsEngine(),
        "VRFB": physics_engine or DummyBatteryPhysicsEngine(),
    }
    api.optimization_engines = {
        "balanced": optimization_engine or DummyOptimizationEngine(),
        "max_earn": optimization_engine or DummyOptimizationEngine(),
        "max_battery_health": optimization_engine or DummyOptimizationEngine(),
        "max_charge": optimization_engine or DummyOptimizationEngine(),
    }
    api.websocket_connections = []
    api.cached_model = cached_model
    api.cached_model_version = "test-model"
    api._setup_routes()
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


def test_predict_preserves_service_unavailable_status_code():
    api = build_route_test_api(cached_model=None)
    client = TestClient(api.app)

    response = client.post(
        "/predict",
        json={
            "battery_soc": 0.5,
            "grid_price_uah_kwh": 12.0,
            "load_demand_kw": 3.0,
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "No model available for prediction"


def test_predict_uses_current_optimizer_contract_and_returns_stable_shape():
    recorded_calls = []

    class RecordingOptimizationEngine(DummyOptimizationEngine):
        def optimize_decision(self, base_prediction, strategy, physics_data=None, renewable_data=None, weights=None):
            recorded_calls.append((base_prediction, strategy))
            return {
                **base_prediction,
                "action": "SELL",
                "confidence": 0.88,
                "reasoning": "Optimized sell decision.",
                "optimization_strategy": strategy,
            }

    api = build_route_test_api(
        cached_model=SimpleNamespace(predict=lambda *_args, **_kwargs: [1, 0.82]),
        feature_store=SimpleNamespace(load_online_features=lambda *_args, **_kwargs: {"existing_feature": 1.0}),
        optimization_engine=RecordingOptimizationEngine(),
    )
    client = TestClient(api.app)

    response = client.post(
        "/predict",
        json={
            "battery_soc": 0.55,
            "grid_price_uah_kwh": 13.5,
            "solar_generation_kw": 1.0,
            "wind_generation_kw": 0.0,
            "load_demand_kw": 4.0,
            "temperature_celsius": 24.0,
            "strategy": "balanced",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert recorded_calls[0][0]["action"] == "SELL"
    assert recorded_calls[0][1] == "balanced"
    assert payload["action"] == "SELL"
    assert payload["strategy_used"] == "balanced"
    assert payload["model_version"] == "test-model"
    assert payload["power_kw"] == 4.0


def test_simulate_battery_preserves_bad_request_status_code():
    api = build_route_test_api(cached_model=SimpleNamespace(predict=lambda *_args, **_kwargs: [1, 0.8]))
    client = TestClient(api.app)

    response = client.post(
        "/simulate/battery",
        json={
            "battery_type": "Unknown",
            "power_kw": 2.0,
            "duration_h": 1.0,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported battery type: Unknown"


def test_simulate_battery_uses_current_physics_contract():
    class RecordingPhysicsEngine(DummyBatteryPhysicsEngine):
        def simulate_battery_behavior(self, user_config):
            assert user_config.battery_type == "LFP"
            assert user_config.battery_temperature_c == 28.0
            return super().simulate_battery_behavior(user_config)

    api = build_route_test_api(
        cached_model=SimpleNamespace(predict=lambda *_args, **_kwargs: [1, 0.8]),
        physics_engine=RecordingPhysicsEngine(),
    )
    client = TestClient(api.app)

    response = client.post(
        "/simulate/battery",
        json={
            "battery_type": "LFP",
            "power_kw": 5.0,
            "duration_h": 1.5,
            "temperature": 28.0,
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["simulation_params"]["applied_power_kw"] == 4.0
    assert payload["initial_state"]["soc_percent"] == 60.0
    assert payload["final_state"]["soc_percent"] > payload["initial_state"]["soc_percent"]


def test_predict_uses_fallback_prediction_when_model_output_is_not_adaptable():
    api = build_route_test_api(
        cached_model=SimpleNamespace(predict=lambda *_args, **_kwargs: object()),
        feature_store=SimpleNamespace(load_online_features=lambda *_args, **_kwargs: {}),
    )
    client = TestClient(api.app)

    response = client.post(
        "/predict",
        json={
            "battery_soc": 0.55,
            "grid_price_uah_kwh": 14.0,
            "solar_generation_kw": 0.0,
            "wind_generation_kw": 0.0,
            "load_demand_kw": 3.5,
            "temperature_celsius": 24.0,
            "strategy": "unknown-strategy",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["action"] == "SELL"
    assert payload["strategy_used"] == "balanced"
    assert payload["expected_profit_uah"] == 49.0
    assert payload["power_kw"] == 3.5


def test_models_retrain_returns_not_needed_message_without_scheduling_work():
    background_calls = []
    api = build_route_test_api(cached_model=SimpleNamespace(predict=lambda *_args, **_kwargs: [1, 0.8]))
    api.retraining_pipeline = SimpleNamespace(
        check_retraining_triggers=lambda: {"should_retrain": False, "reasons": []}
    )

    async def record_retrain():
        background_calls.append("called")

    api._retrain_model_async = record_retrain
    client = TestClient(api.app)

    response = client.post("/models/retrain")

    assert response.status_code == 200
    assert response.json()["message"] == "Retraining not needed at this time"
    assert background_calls == []


def test_models_retrain_schedules_background_retraining_when_triggers_fire():
    background_calls = []
    api = build_route_test_api(cached_model=SimpleNamespace(predict=lambda *_args, **_kwargs: [1, 0.8]))
    api.retraining_pipeline = SimpleNamespace(
        check_retraining_triggers=lambda: {
            "should_retrain": True,
            "reasons": ["Data drift detected: score 0.991"],
        }
    )

    async def record_retrain():
        background_calls.append("called")

    api._retrain_model_async = record_retrain
    client = TestClient(api.app)

    response = client.post("/models/retrain")

    assert response.status_code == 200
    assert response.json()["message"] == "Model retraining initiated"
    assert response.json()["reasons"] == ["Data drift detected: score 0.991"]
    assert background_calls == ["called"]


def test_broadcast_websocket_update_removes_disconnected_clients():
    delivered_messages = []

    class WorkingSocket:
        async def send_json(self, message):
            delivered_messages.append(message)

    class FailingSocket:
        async def send_json(self, message):
            raise RuntimeError("socket closed")

    api = MLServingAPI.__new__(MLServingAPI)
    working_socket = WorkingSocket()
    failing_socket = FailingSocket()
    api.websocket_connections = [working_socket, failing_socket]

    asyncio.run(api._broadcast_websocket_update({"type": "prediction", "data": {"ok": True}}))

    assert delivered_messages == [{"type": "prediction", "data": {"ok": True}}]
    assert api.websocket_connections == [working_socket]
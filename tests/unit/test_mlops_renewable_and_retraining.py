import importlib.util
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys
import types

import polars as pl


def load_renewable_module():
    module_path = Path(__file__).resolve().parents[2] / "energy_ml" / "mlops" / "renewable_forecasting.py"
    package = types.ModuleType("energy_ml")
    package.__path__ = [str(module_path.parents[1])]
    mlops_package = types.ModuleType("energy_ml.mlops")
    mlops_package.__path__ = [str(module_path.parent)]

    sys.modules.setdefault("energy_ml", package)
    sys.modules.setdefault("energy_ml.mlops", mlops_package)

    spec = importlib.util.spec_from_file_location("energy_ml.mlops.renewable_forecasting", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_retraining_module():
    module_path = Path(__file__).resolve().parents[2] / "energy_ml" / "mlops" / "retraining_pipeline.py"
    package = types.ModuleType("energy_ml")
    package.__path__ = [str(module_path.parents[1])]
    mlops_package = types.ModuleType("energy_ml.mlops")
    mlops_package.__path__ = [str(module_path.parent)]

    sys.modules.setdefault("energy_ml", package)
    sys.modules.setdefault("energy_ml.mlops", mlops_package)

    model_registry = types.ModuleType("energy_ml.mlops.model_registry")
    model_registry.ModelRegistry = object
    model_registry.get_model_registry = lambda: None
    feature_store = types.ModuleType("energy_ml.mlops.feature_store")
    feature_store.FeatureStore = object
    feature_store.get_feature_store = lambda: None
    xgboost = types.ModuleType("xgboost")

    class DummyXGBRegressor:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def fit(self, X, y):
            self.rows_seen = len(X)
            self.target_rows_seen = len(y)

        def predict(self, X):
            return [0.0 for _ in range(len(X))]

    xgboost.XGBRegressor = DummyXGBRegressor

    sys.modules["energy_ml.mlops.model_registry"] = model_registry
    sys.modules["energy_ml.mlops.feature_store"] = feature_store
    sys.modules.setdefault("xgboost", xgboost)

    spec = importlib.util.spec_from_file_location("energy_ml.mlops.retraining_pipeline", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


renewable_module = load_renewable_module()
retraining_module = load_retraining_module()

RenewableForecaster = renewable_module.RenewableForecaster
UserConfigModel = renewable_module.UserConfigModel
DriftDetector = retraining_module.DriftDetector
DriftReport = retraining_module.DriftReport
RetrainingPipeline = retraining_module.RetrainingPipeline
ABTestManager = retraining_module.ABTestManager


class StubRegistry:
    def __init__(self, production_versions):
        self.production_versions = production_versions

    def list_model_versions(self, model_name, stage=None):
        assert model_name == "energy_optimizer"
        if stage == "production":
            return self.production_versions
        return self.production_versions


class StubFeatureStore:
    def __init__(self, frame):
        self.frame = frame

    def load_batch_features(self, feature_view, start_time, end_time):
        assert feature_view == "energy_features"
        return self.frame


def test_live_context_weather_is_sanitized_and_used_first(monkeypatch):
    live_context = {
        "weather_signal": {
            "latitude": 48.5,
            "longitude": 35.1,
            "source": "live_context",
            "current": {
                "shortwave_radiation_w_m2": -15,
                "wind_speed_m_s": "7.5",
                "temperature_c": "18.5",
                "cloud_cover_percent": 135,
            },
            "next24h": [
                {
                    "timestamp": "2026-03-06T01:00:00Z",
                    "shortwave_radiation_w_m2": -1,
                    "wind_speed_m_s": 4.2,
                    "temperature_c": 17,
                },
                {
                    "timestamp": "2026-03-06T02:00:00Z",
                    "shortwave_radiation_w_m2": 125,
                    "wind_speed_m_s": 5.1,
                    "temperature_c": 16,
                },
            ],
        }
    }
    monkeypatch.setenv("ENERGY_ML_LIVE_CONTEXT_JSON", json.dumps(live_context))

    weather = RenewableForecaster()._get_weather_data(50.45, 30.52)

    assert weather["source"] == "live_context"
    assert weather["solar_irradiance_w_m2"] == 0.0
    assert weather["wind_speed_m_s"] == 7.5
    assert weather["temperature_c"] == 18.5
    assert weather["cloud_cover_fraction"] == 1.0
    assert weather["hourly_forecast"]["hour_1"]["solar_irradiance_w_m2"] == 0.0
    assert weather["hourly_forecast"]["hour_2"]["wind_speed_m_s"] == 5.1


def test_generate_forecasts_combines_generation_and_capacity_factors(monkeypatch):
    weather_data = {
        "solar_irradiance_w_m2": 800,
        "wind_speed_m_s": 12,
        "temperature_c": 25,
        "hourly_forecast": {
            "hour_0": {"solar_irradiance_w_m2": 900, "wind_speed_m_s": 12, "temperature_c": 25},
            "hour_1": {"solar_irradiance_w_m2": 0, "wind_speed_m_s": 5, "temperature_c": 20},
        },
    }
    forecaster = RenewableForecaster()
    monkeypatch.setattr(forecaster, "_get_weather_data", lambda *_args: weather_data)

    forecasts = forecaster.generate_forecasts(
        UserConfigModel(solar_capacity_kw=10.0, wind_capacity_kw=5.0, latitude=49.0, longitude=31.0)
    )

    assert forecasts["solar_forecast"]["current_generation_kw"] == 1.6
    assert forecasts["wind_forecast"]["current_generation_kw"] == 5.0
    assert forecasts["total_renewable"]["current_generation_kw"] == 6.6
    assert forecasts["installed_capacity"]["total_kw"] == 15.0
    assert forecasts["capacity_factors"]["solar"] > 0
    assert forecasts["capacity_factors"]["wind"] > 0
    assert forecasts["capacity_factors"]["combined"] > 0


def test_integrate_with_prediction_reduces_grid_buy_when_renewables_are_high():
    next_hour_key = f"hour_{(datetime.now().hour + 1) % 24}"
    renewable_data = {
        "timestamp": datetime.now().isoformat(),
        "total_renewable": {
            "current_generation_kw": 6.5,
            "hourly_generation": {next_hour_key: 7.25},
        },
        "capacity_factors": {"combined": 0.41},
    }

    enhanced = RenewableForecaster().integrate_with_prediction(
        {"action": "BUY", "confidence": 0.6, "reasoning": "Base decision."},
        renewable_data,
    )

    assert enhanced["action"] == "HOLD"
    assert enhanced["confidence"] == 0.7
    assert enhanced["renewable_generation_kw"] == 6.5
    assert enhanced["next_hour_renewable_kw"] == 7.25
    assert enhanced["renewable_capacity_factor"] == 0.41
    assert enhanced["renewable_integration_applied"] is True


def test_drift_detector_reports_shifted_feature_distribution():
    detector = DriftDetector(sensitivity=0.2)
    reference = pl.DataFrame(
        {
            "battery_soc": [0.2, 0.25, 0.3, 0.35],
            "grid_price_uah_kwh": [9.0, 9.5, 10.0, 10.5],
        }
    )
    current = pl.DataFrame(
        {
            "battery_soc": [0.9, 0.92, 0.95, 0.97],
            "grid_price_uah_kwh": [9.0, 9.4, 9.8, 10.2],
        }
    )
    detector.set_reference_data(reference, ["battery_soc", "grid_price_uah_kwh"])

    report = detector.detect_drift(current, ["battery_soc", "grid_price_uah_kwh"])

    assert report.sample_size == 4
    assert report.feature_drifts["battery_soc"] > 0.8
    assert report.drift_threshold == 0.8
    assert report.is_drift_detected is True


def test_retraining_triggers_when_no_production_model_exists(monkeypatch):
    monkeypatch.setattr(RetrainingPipeline, "_initialize_drift_detection", lambda self: None)
    pipeline = RetrainingPipeline(
        model_registry=StubRegistry([]),
        feature_store=StubFeatureStore(pl.DataFrame()),
        monitor=types.SimpleNamespace(calculate_performance_metrics=lambda *_args: None),
    )

    triggers = pipeline.check_retraining_triggers()

    assert triggers["should_retrain"] is True
    assert triggers["reasons"] == ["No production model found"]


def test_retraining_triggers_when_performance_and_drift_exceed_thresholds(monkeypatch):
    monkeypatch.setattr(RetrainingPipeline, "_initialize_drift_detection", lambda self: None)
    version = types.SimpleNamespace(
        version_id="prod-v1",
        created_at=datetime.now() - timedelta(days=3),
        performance_metrics={"test_mape": 11.0},
    )
    pipeline = RetrainingPipeline(
        model_registry=StubRegistry([version]),
        feature_store=StubFeatureStore(pl.DataFrame()),
        monitor=types.SimpleNamespace(calculate_performance_metrics=lambda *_args: types.SimpleNamespace(mape=18.4)),
    )
    monkeypatch.setattr(
        pipeline,
        "_check_data_drift",
        lambda: DriftReport(
            timestamp=datetime.now(),
            drift_score=0.99,
            drift_threshold=0.95,
            is_drift_detected=True,
            feature_drifts={"battery_soc": 0.99},
            sample_size=120,
            reference_period="200 samples",
            detection_method="test",
        ),
    )

    triggers = pipeline.check_retraining_triggers()

    assert triggers["should_retrain"] is True
    assert triggers["performance_degraded"] is True
    assert triggers["drift_detected"] is True
    assert len(triggers["reasons"]) == 2
    assert triggers["last_training_age_hours"] >= 72


def test_check_data_drift_returns_skipped_report_for_small_recent_window(monkeypatch):
    monkeypatch.setattr(RetrainingPipeline, "_initialize_drift_detection", lambda self: None)
    small_recent_window = pl.DataFrame(
        {
            "battery_soc": [0.2, 0.3],
            "grid_price_uah_kwh": [9.0, 10.0],
            "solar_generation_kw": [0.0, 1.0],
            "load_demand_kw": [4.0, 5.0],
            "temperature_celsius": [20.0, 21.0],
        }
    )
    pipeline = RetrainingPipeline(
        model_registry=StubRegistry([]),
        feature_store=StubFeatureStore(small_recent_window),
        monitor=types.SimpleNamespace(calculate_performance_metrics=lambda *_args: None),
    )

    report = pipeline._check_data_drift()

    assert report.is_drift_detected is False
    assert report.sample_size == 2
    assert report.reference_period == "insufficient data"
    assert report.detection_method == "skipped"


def test_ab_test_manager_completes_expired_test_and_analyzes_treatment_winner(tmp_path):
    manager = ABTestManager(ab_config_path=str(tmp_path / "ab_tests.json"))
    manager.active_tests = {
        "expired": {
            "test_name": "expired",
            "control_version": "v1",
            "treatment_version": "v2",
            "traffic_split": 0.5,
            "start_time": (datetime.now() - timedelta(days=2)).isoformat(),
            "end_time": (datetime.now() - timedelta(hours=1)).isoformat(),
            "status": "active",
            "metrics": {
                "control": {"predictions": 0, "errors": 0, "total_mape": 0.0},
                "treatment": {"predictions": 0, "errors": 0, "total_mape": 0.0},
            },
        }
    }

    assert manager.route_prediction("user-1") == "production"
    assert manager.active_tests["expired"]["status"] == "completed"

    manager.create_ab_test("fresh", "v1", "v2", traffic_split=0.5, duration_hours=24)
    for _ in range(120):
        manager.log_ab_result("fresh", "v1", prediction=110.0, actual=100.0, error=False)
        manager.log_ab_result("fresh", "v2", prediction=101.0, actual=100.0, error=False)

    analysis = manager.analyze_ab_test("fresh")

    assert analysis["sample_size_adequate"] is True
    assert analysis["winner"] == "treatment"
    assert analysis["treatment"]["avg_mape"] < analysis["control"]["avg_mape"]
    assert analysis["improvement"]["mape_improvement_percent"] > 0
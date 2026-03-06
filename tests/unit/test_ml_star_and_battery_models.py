import importlib.util
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]


def _ensure_energy_ml_package() -> types.ModuleType:
    package = sys.modules.get("energy_ml")
    if package is None:
        package = types.ModuleType("energy_ml")
        package.__path__ = [str(ROOT / "energy_ml")]
        sys.modules["energy_ml"] = package
    return package


def _load_energy_ml_module(module_name: str, relative_path: str):
    _ensure_energy_ml_package()
    module_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _dagster_stub() -> types.ModuleType:
    module = types.ModuleType("dagster")

    def _identity_decorator(*args, **kwargs):
        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return args[0]

        def decorator(func):
            return func

        return decorator

    class _SimpleArg:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    module.asset = _identity_decorator
    module.op = _identity_decorator
    module.job = _identity_decorator
    module.graph = _identity_decorator
    module.In = _SimpleArg
    module.Out = _SimpleArg
    return module


def _imblearn_stub() -> tuple[types.ModuleType, types.ModuleType]:
    package = types.ModuleType("imblearn")
    oversampling = types.ModuleType("imblearn.over_sampling")

    class SMOTE:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def fit_resample(self, X, y):
            return X, y

    oversampling.SMOTE = SMOTE
    package.over_sampling = oversampling
    return package, oversampling


def _load_asset_module(module_name: str, relative_path: str):
    _ensure_energy_ml_package()
    module_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    previous = sys.modules.get("dagster")
    previous_imblearn = sys.modules.get("imblearn")
    previous_imblearn_oversampling = sys.modules.get("imblearn.over_sampling")
    imblearn_package, imblearn_oversampling = _imblearn_stub()
    sys.modules["dagster"] = _dagster_stub()
    sys.modules["imblearn"] = imblearn_package
    sys.modules["imblearn.over_sampling"] = imblearn_oversampling
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            sys.modules.pop("dagster", None)
        else:
            sys.modules["dagster"] = previous
        if previous_imblearn is None:
            sys.modules.pop("imblearn", None)
        else:
            sys.modules["imblearn"] = previous_imblearn
        if previous_imblearn_oversampling is None:
            sys.modules.pop("imblearn.over_sampling", None)
        else:
            sys.modules["imblearn.over_sampling"] = previous_imblearn_oversampling
    return module


CONFIG_MODELS = _load_energy_ml_module("energy_ml.config_models", "energy_ml/config_models.py")
BATTERY_MODELS = _load_energy_ml_module("energy_ml.battery_degradation", "energy_ml/battery_degradation.py")
ML_STAR_PHASE3 = _load_asset_module("ml_star_phase3_under_test", "energy_ml/assets/ml_star_phase3.py")
ML_STAR_PIPELINE = _load_asset_module(
    "ml_star_optimized_pipeline_under_test",
    "energy_ml/assets/ml_star_optimized_pipeline.py",
)


BatteryConfig = CONFIG_MODELS.BatteryConfig
BatteryModel = BATTERY_MODELS.BatteryModel
LFPModel = BATTERY_MODELS.LFPModel
LeadAcidModel = BATTERY_MODELS.LeadAcidModel
VRFBModel = BATTERY_MODELS.VRFBModel


def _make_battery_config(battery_type: str = "LFP"):
    return BatteryConfig(
        type=battery_type,
        capacity_kwh=20.0,
        efficiency=0.94,
        max_charge_rate_kw=5.0,
        max_discharge_rate_kw=5.0,
    )


class DummyContext:
    def __init__(self):
        self.messages = []
        self.log = self

    def info(self, message):
        self.messages.append(message)


class DummyPredictModel:
    def __init__(self):
        self.seen = None

    def predict(self, X):
        self.seen = list(X.columns)
        return np.array([1] * len(X))

    def predict_proba(self, X):
        self.seen = list(X.columns)
        return np.array([[0.1, 0.7, 0.1, 0.1] for _ in range(len(X))])


def test_battery_degradation_models_produce_consistent_curves():
    lfp_result = LFPModel(_make_battery_config("LFP")).simulate_cycles(cycles=25, dod=0.8, c_rate=0.5)
    lead_result = LeadAcidModel(_make_battery_config("Lead-Acid")).simulate_cycles(cycles=25, dod=0.8, c_rate=0.5)
    vrfb_result = VRFBModel(_make_battery_config("VRFB")).simulate_cycles(cycles=25, dod=0.8, c_rate=0.5)

    assert len(lfp_result.curve) == 25
    assert lead_result.soh < lfp_result.soh
    assert vrfb_result.soh > lfp_result.soh
    assert vrfb_result.degradation_cost >= 0.0


def test_battery_model_soc_segments_cover_midpoints():
    segments = BatteryModel(_make_battery_config()).soc_segments(segments=4)

    assert segments == [0.125, 0.375, 0.625, 0.875]


def test_ml_star_phase3_predictor_selects_expected_columns():
    predictor = ML_STAR_PHASE3.ml_star_production_predictor(
        {"model": DummyPredictModel(), "selected_indices": np.array([0, 2])}
    )
    frame = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0], "c": [5.0, 6.0]})

    prediction = predictor.predict(frame)
    probabilities = predictor.predict_proba(frame)

    assert predictor.model.seen == ["a", "c"]
    assert prediction.tolist() == [1, 1]
    assert probabilities.shape == (2, 4)


def test_ml_star_phase3_metrics_repackages_model_summary():
    metrics = ML_STAR_PHASE3.ml_star_metrics(
        {
            "accuracy": 0.84,
            "f1_score": 0.83,
            "features_used": 36,
            "total_features": 73,
            "improvement_percent": 11.5,
        }
    )

    assert metrics["accuracy"] == 0.84
    assert metrics["baseline_accuracy"] == 0.725
    assert metrics["features_used"] == 36


def test_ml_star_select_top_features_uses_percentile_threshold():
    class FakeEstimator:
        feature_importances_ = np.array([0.1, 0.8, 0.4, 0.9])

    class FakeModel:
        estimators_ = [FakeEstimator()]

    context = DummyContext()
    X_train = pd.DataFrame(np.zeros((3, 4)), columns=["f0", "f1", "f2", "f3"])

    selected_indices, selected_features = ML_STAR_PIPELINE.select_top_features(context, FakeModel(), X_train, top_percentile=50)

    assert selected_indices.tolist() == [1, 3]
    assert selected_features == ["f1", "f3"]
    assert any("Selected 2/4 features" in message for message in context.messages)


def test_ml_star_predictor_reports_confidence_and_labels():
    predictor = ML_STAR_PIPELINE.SmartEnergyAIPredictor(DummyPredictModel(), [0, 2])
    frame = pd.DataFrame({"a": [1.0], "b": [2.0], "c": [3.0]})

    result = predictor.predict_with_confidence(frame)

    assert result["predictions"].tolist() == [1]
    assert result["confidence"].tolist() == [0.7]
    assert result["class_labels"] == ["SELL"]


def test_phase1_voting_ensemble_uses_soft_voting(monkeypatch):
    created = {}

    class FakeVotingClassifier:
        def __init__(self, estimators, voting):
            created["estimators"] = estimators
            created["voting"] = voting

        def fit(self, X_train, y_train):
            created["fit_shape"] = (len(X_train), len(y_train))
            return self

    monkeypatch.setattr(ML_STAR_PIPELINE, "VotingClassifier", FakeVotingClassifier)
    context = DummyContext()
    X_train = pd.DataFrame({"f0": [0.1, 0.2], "f1": [0.3, 0.4]})
    y_train = np.array([0, 1])

    model = ML_STAR_PIPELINE.create_phase1_voting_ensemble(context, X_train, y_train)

    assert isinstance(model, FakeVotingClassifier)
    assert created["voting"] == "soft"
    assert len(created["estimators"]) == 3
    assert created["fit_shape"] == (2, 2)
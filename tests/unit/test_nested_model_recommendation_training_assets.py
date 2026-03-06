import importlib.util
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]


def _dagster_stub() -> types.ModuleType:
    module = types.ModuleType("dagster")

    def asset(*args, **kwargs):
        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return args[0]

        def decorator(func):
            return func

        return decorator

    class Output:
        def __init__(self, value, metadata=None):
            self.value = value
            self.metadata = metadata or {}

        @classmethod
        def __class_getitem__(cls, _item):
            return cls

    class Definitions:
        def __init__(self, assets):
            self.assets = assets

    module.asset = asset
    module.Output = Output
    module.Definitions = Definitions
    return module


def _xgboost_stub() -> types.ModuleType:
    module = types.ModuleType("xgboost")

    class XGBClassifier:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.last_fit = None

        def fit(self, X, y):
            self.last_fit = (X.copy(), np.array(y))
            return self

        def predict(self, X):
            values = X.iloc[:, 0].to_numpy()
            return np.array([0 if value < np.nanmean(values) else 1 for value in values])

        def predict_proba(self, X):
            return np.array([[0.7, 0.2, 0.05, 0.05] for _ in range(len(X))])

        def score(self, X, y):
            predictions = self.predict(X)
            return float((predictions == y).mean())

    module.XGBClassifier = XGBClassifier
    return module


def _load_module(module_name: str, relative_path: str, injected_modules: dict[str, types.ModuleType] | None = None):
    module_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    previous_modules: dict[str, types.ModuleType | None] = {}
    for name, injected in (injected_modules or {}).items():
        previous_modules[name] = sys.modules.get(name)
        sys.modules[name] = injected
    try:
        spec.loader.exec_module(module)
    finally:
        for name, previous in previous_modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    return module


MODELS = _load_module(
    "nested_models_under_test",
    "energy_ml/energy_ml/assets/models.py",
    injected_modules={"dagster": _dagster_stub(), "xgboost": _xgboost_stub()},
)
RECOMMENDATIONS = _load_module(
    "nested_recommendations_under_test",
    "energy_ml/energy_ml/assets/recommendations.py",
    injected_modules={"dagster": _dagster_stub()},
)
TRAINING = _load_module(
    "nested_training_under_test",
    "energy_ml/energy_ml/assets/training.py",
    injected_modules={"dagster": _dagster_stub()},
)


class PredictSequenceModel:
    def __init__(self, sequence):
        self.sequence = np.array(sequence)

    def predict(self, X):
        return self.sequence[: len(X)]

    def predict_proba(self, X):
        return np.array([[0.1, 0.8, 0.05, 0.05] for _ in range(len(X))])


def test_training_data_prepared_strips_timestamp_and_normalizes_numeric_columns():
    feature_matrix = pd.DataFrame(
        {
            "timestamp": [pd.Timestamp("2026-03-06 10:00:00"), pd.Timestamp("2026-03-06 11:00:00")],
            "price_uah_kwh": [10.0, 14.0],
            "all_invalid": [np.inf, np.inf],
        }
    )

    result = TRAINING.training_data_prepared(feature_matrix)

    assert "timestamp" not in result.value.columns
    assert result.metadata["normalized"] is True
    assert result.metadata["missing_after"] == 0
    assert np.isfinite(result.value.to_numpy()).all()
    assert result.value["all_invalid"].tolist() == [0, 0]


def test_backtest_dataset_uses_time_based_split():
    prepared = pd.DataFrame({"value": [1.0]})
    historical = pd.DataFrame({"value": list(range(10))})

    result = TRAINING.backtest_dataset(prepared, historical)

    assert len(result.value["train"]) == 8
    assert len(result.value["test"]) == 2
    assert result.metadata["split_ratio"] == "80/20"


def test_xgboost_trained_model_returns_model_metadata_for_numeric_dataset():
    dataset = {
        "train": pd.DataFrame(
            {
                "price_uah_kwh": [8.0, 10.0, 18.0, 20.0],
                "soc_percent": [30.0, 45.0, 85.0, 70.0],
                "wind_speed_ms": [2.0, 3.0, 4.0, 5.0],
            }
        )
    }

    result = MODELS.xgboost_trained_model(dataset)

    assert result.value["model_type"] == "xgboost"
    assert result.value["n_features"] == 3
    assert result.value["n_samples"] == 4
    assert "training_accuracy" in result.value


def test_backtesting_results_reports_profit_and_signal_counts():
    model_output = {"model": PredictSequenceModel([0, 1, 3, 2])}
    backtest_dataset = {
        "combined": pd.DataFrame(
            {
                "price_uah_kwh": [10.0, 16.0, 20.0, 12.0],
                "soc_percent": [40.0, 50.0, 90.0, 25.0],
                "feature_x": [1.0, 2.0, 3.0, 4.0],
            }
        )
    }

    result = MODELS.backtesting_results(model_output, backtest_dataset)
    values = dict(zip(result.value["metric"], result.value["value"]))

    assert values["total_buy_signals"] == 1
    assert values["total_sell_signals"] == 1
    assert values["total_discharge_signals"] == 1
    assert values["total_hold_signals"] == 1
    assert result.metadata["backtest_days"] == 0


def test_current_recommendation_falls_back_when_model_errors():
    result = RECOMMENDATIONS.current_recommendation(
        {"error": "missing model"},
        pd.DataFrame({"price_uah_kwh": [14.0], "soc_percent": [70.0]}),
    )

    assert result.metadata["status"] == "fallback"
    assert result.value.iloc[0]["recommendation"] == "HOLD"


def test_recommendation_metadata_returns_lineage_rows_instead_of_error():
    current_recommendation = pd.DataFrame(
        {
            "recommendation": ["SELL"],
            "confidence": [0.82],
            "confidence_percent": [82],
            "rationale": ["Price is high"],
            "current_price_uah_kwh": [18.5],
            "current_soc_percent": [77.0],
        }
    )

    result = RECOMMENDATIONS.recommendation_metadata(
        current_recommendation,
        pd.DataFrame({"feature_a": [1.0]}),
        {"model_type": "xgboost"},
    )

    assert result.metadata["data_sources"] == 5
    assert list(result.value["component"]) == [
        "data_provenance",
        "feature_matrix",
        "model_info",
        "recommendation_details",
    ]
    assert result.value["lineage_text"].nunique() == 1


def test_dashboard_api_response_counts_retraining_checks():
    current_recommendation = pd.DataFrame(
        {
            "recommendation": ["DISCHARGE"],
            "confidence": [0.8],
            "confidence_percent": [80],
            "rationale": ["Very high price"],
            "current_price_uah_kwh": [19.2],
            "current_soc_percent": [83.0],
        }
    )
    schedule = pd.DataFrame(
        {
            "recommended_action": ["BUY", "SELL", "DISCHARGE", "HOLD"],
            "expected_profit_uah": [-14.0, 11.0, 12.0, 0.0],
        }
    )
    retraining_triggers = pd.DataFrame(
        {
            "triggered": ["YES", "NO", "YES"],
        }
    )

    result = RECOMMENDATIONS.dashboard_recommendation_api_response(
        current_recommendation,
        schedule,
        pd.DataFrame({"component": ["metadata"]}),
        retraining_triggers,
    )

    assert result.value["status"] == "success"
    assert result.value["monitoring"]["needs_retraining"] is True
    assert result.value["monitoring"]["triggered_checks"] == 2
    assert result.value["schedule_24h"]["total_expected_profit"] == 9.0
"""Support helpers for retraining, drift detection, and A/B testing."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import polars as pl
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
from sklearn.model_selection import train_test_split


def dataclass_to_timestamped_dict(instance, asdict_func) -> Dict[str, Any]:
    payload = asdict_func(instance)
    payload["timestamp"] = instance.timestamp.isoformat()
    return payload


def compute_feature_statistics(reference_df: pl.DataFrame, feature_columns: List[str]) -> Dict[str, Dict[str, float]]:
    statistics: Dict[str, Dict[str, float]] = {}
    for feature in feature_columns:
        if feature not in reference_df.columns:
            continue
        values = reference_df[feature].to_numpy()
        values = values[~np.isnan(values)]
        statistics[feature] = {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "median": float(np.median(values)),
        }
    return statistics


def calculate_ks_drift(feature_statistics: Dict[str, float], current_values: np.ndarray) -> float:
    current_mean = np.mean(current_values)
    current_std = np.std(current_values)
    mean_diff = abs(current_mean - feature_statistics["mean"]) / max(feature_statistics["std"], 0.001)
    std_ratio = current_std / max(feature_statistics["std"], 0.001)
    std_diff = abs(1.0 - std_ratio)
    return min(1.0, (mean_diff * 0.7 + std_diff * 0.3) / 3.0)


def build_drift_report_payload(
    timestamp: datetime,
    overall_drift_score: float,
    sensitivity: float,
    feature_drifts: Dict[str, float],
    sample_size: int,
    reference_sample_size: int,
) -> Dict[str, Any]:
    return {
        "timestamp": timestamp,
        "drift_score": overall_drift_score,
        "drift_threshold": 1.0 - sensitivity,
        "is_drift_detected": overall_drift_score > (1.0 - sensitivity),
        "feature_drifts": feature_drifts,
        "sample_size": sample_size,
        "reference_period": f"{reference_sample_size} samples",
        "detection_method": "KS-approximation",
    }


def build_prediction_log(
    timestamp: datetime,
    model_version: str,
    features: Dict[str, Any],
    prediction: float,
    actual: Optional[float],
    latency_ms: Optional[float],
) -> Dict[str, Any]:
    return {
        "timestamp": timestamp.isoformat(),
        "model_version": model_version,
        "prediction": prediction,
        "actual": actual,
        "latency_ms": latency_ms,
        "features": features,
    }


def trim_recent_predictions(recent_predictions: List[Dict[str, Any]], window_size: int) -> List[Dict[str, Any]]:
    if len(recent_predictions) <= window_size:
        return recent_predictions
    return recent_predictions[-window_size:]


def build_model_performance_payload(model_version: str, model_predictions: Sequence[Dict[str, Any]], timestamp: datetime) -> Optional[Dict[str, Any]]:
    if len(model_predictions) < 10:
        return None

    predictions = [prediction["prediction"] for prediction in model_predictions]
    actuals = [prediction["actual"] for prediction in model_predictions]
    mape = mean_absolute_percentage_error(actuals, predictions) * 100
    rmse = float(np.sqrt(mean_squared_error(actuals, predictions)))
    mae = float(np.mean(np.abs(np.array(predictions) - np.array(actuals))))
    ss_res = np.sum((np.array(actuals) - np.array(predictions)) ** 2)
    ss_tot = np.sum((np.array(actuals) - np.mean(actuals)) ** 2)
    r2_score = float(1 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0
    latencies = [prediction["latency_ms"] for prediction in model_predictions if prediction["latency_ms"] is not None]
    latency_p95 = float(np.percentile(latencies, 95)) if latencies else 0.0
    errors = [abs(prediction - actual) / max(abs(actual), 0.001) > 0.2 for prediction, actual in zip(predictions, actuals)]

    return {
        "timestamp": timestamp,
        "model_version": model_version,
        "mape": float(mape),
        "rmse": rmse,
        "mae": mae,
        "r2_score": r2_score,
        "prediction_count": len(model_predictions),
        "latency_p95_ms": latency_p95,
        "error_rate": float(np.mean(errors) * 100),
    }


def initial_retraining_triggers() -> Dict[str, Any]:
    return {
        "should_retrain": False,
        "reasons": [],
        "performance_degraded": False,
        "drift_detected": False,
        "last_training_age_hours": 0,
    }


def evaluate_retraining_triggers(
    production_versions: Sequence[Any],
    performance: Optional[Any],
    drift_report: Optional[Any],
    performance_threshold_mape: float,
    min_retraining_interval_hours: int,
    now: datetime,
) -> Dict[str, Any]:
    triggers = initial_retraining_triggers()
    if not production_versions:
        triggers["should_retrain"] = True
        triggers["reasons"].append("No production model found")
        return triggers

    current_version = production_versions[0]
    age = now - current_version.created_at
    triggers["last_training_age_hours"] = age.total_seconds() / 3600
    if age < timedelta(hours=min_retraining_interval_hours):
        return triggers

    if performance and performance.mape > performance_threshold_mape:
        triggers["should_retrain"] = True
        triggers["performance_degraded"] = True
        triggers["reasons"].append(
            f"Performance degraded: MAPE {performance.mape:.1f}% > {performance_threshold_mape}%"
        )

    if drift_report and drift_report.is_drift_detected:
        triggers["should_retrain"] = True
        triggers["drift_detected"] = True
        triggers["reasons"].append(f"Data drift detected: score {drift_report.drift_score:.3f}")

    return triggers


def build_training_result(reason: str, started_at: datetime) -> Dict[str, Any]:
    return {
        "started_at": started_at.isoformat(),
        "reason": reason,
        "success": False,
        "new_model_version": None,
        "metrics": {},
        "error": None,
    }


def training_feature_columns() -> List[str]:
    return [
        "battery_soc",
        "grid_price_uah_kwh",
        "solar_generation_kw",
        "load_demand_kw",
        "temperature_celsius",
        "is_peak_hour",
        "day_of_week",
        "hour_of_day",
        "price_ma_24h",
        "load_ma_7d",
    ]


def drift_feature_columns() -> List[str]:
    return [
        "battery_soc",
        "grid_price_uah_kwh",
        "solar_generation_kw",
        "load_demand_kw",
        "temperature_celsius",
    ]


def prepare_training_arrays(training_data: pl.DataFrame, feature_columns: List[str]):
    training_data = training_data.sort("timestamp")
    training_data = training_data.with_columns(pl.col("grid_price_uah_kwh").shift(-1).alias("target_price")).drop_nulls()
    x_values = training_data.select(feature_columns).to_numpy()
    y_values = training_data["target_price"].to_numpy()
    return train_test_split(x_values, y_values, test_size=0.2, random_state=42, shuffle=False)


def build_training_metrics(y_train, y_pred_train, y_test, y_pred_test, train_count: int, test_count: int) -> Dict[str, Any]:
    return {
        "train_mape": mean_absolute_percentage_error(y_train, y_pred_train) * 100,
        "test_mape": mean_absolute_percentage_error(y_test, y_pred_test) * 100,
        "train_rmse": np.sqrt(mean_squared_error(y_train, y_pred_train)),
        "test_rmse": np.sqrt(mean_squared_error(y_test, y_pred_test)),
        "training_samples": train_count,
        "test_samples": test_count,
    }


def build_insufficient_drift_report(timestamp: datetime, drift_threshold: float, sample_size: int) -> Dict[str, Any]:
    return {
        "timestamp": timestamp,
        "drift_score": 0.0,
        "drift_threshold": drift_threshold,
        "is_drift_detected": False,
        "feature_drifts": {},
        "sample_size": sample_size,
        "reference_period": "insufficient data",
        "detection_method": "skipped",
    }


def recent_drift_window(now: datetime) -> Tuple[datetime, datetime]:
    end_time = now
    start_time = end_time - timedelta(days=7)
    return start_time, end_time


def reference_drift_window(now: datetime) -> Tuple[datetime, datetime]:
    end_time = now - timedelta(days=30)
    start_time = end_time - timedelta(days=30)
    return start_time, end_time


def create_ab_test_config(
    test_name: str,
    control_version: str,
    treatment_version: str,
    traffic_split: float,
    duration_hours: int,
    now: datetime,
) -> Dict[str, Any]:
    return {
        "test_name": test_name,
        "control_version": control_version,
        "treatment_version": treatment_version,
        "traffic_split": traffic_split,
        "start_time": now.isoformat(),
        "end_time": (now + timedelta(hours=duration_hours)).isoformat(),
        "status": "active",
        "metrics": {
            "control": {"predictions": 0, "errors": 0, "total_mape": 0.0},
            "treatment": {"predictions": 0, "errors": 0, "total_mape": 0.0},
        },
    }


def route_ab_prediction(active_tests: Dict[str, Dict[str, Any]], user_id: str, now: datetime) -> str:
    for test_name, config in active_tests.items():
        if config["status"] != "active":
            continue
        end_time = datetime.fromisoformat(config["end_time"])
        if now > end_time:
            config["status"] = "completed"
            continue
        user_hash = int(hashlib.md5(f"{user_id}_{test_name}".encode()).hexdigest(), 16)
        if (user_hash % 100) < (config["traffic_split"] * 100):
            return config["treatment_version"]
        return config["control_version"]
    return "production"


def update_ab_metrics(config: Dict[str, Any], version: str, prediction: float, actual: Optional[float], error: bool) -> bool:
    if version == config["control_version"]:
        group = "control"
    elif version == config["treatment_version"]:
        group = "treatment"
    else:
        return False

    metrics = config["metrics"][group]
    metrics["predictions"] += 1
    if error:
        metrics["errors"] += 1
    if actual is not None:
        metrics["total_mape"] += abs(prediction - actual) / max(abs(actual), 0.001)
    return True


def analyze_ab_test_config(test_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
    control_metrics = config["metrics"]["control"]
    treatment_metrics = config["metrics"]["treatment"]
    control_error_rate = control_metrics["errors"] / max(control_metrics["predictions"], 1)
    treatment_error_rate = treatment_metrics["errors"] / max(treatment_metrics["predictions"], 1)
    control_avg_mape = control_metrics["total_mape"] / max(control_metrics["predictions"], 1) * 100
    treatment_avg_mape = treatment_metrics["total_mape"] / max(treatment_metrics["predictions"], 1) * 100
    sample_size_adequate = min(control_metrics["predictions"], treatment_metrics["predictions"]) >= 100

    winner = None
    if sample_size_adequate:
        if treatment_avg_mape < control_avg_mape * 0.95:
            winner = "treatment"
        elif control_avg_mape < treatment_avg_mape * 0.95:
            winner = "control"

    return {
        "test_name": test_name,
        "status": config["status"],
        "sample_size_adequate": sample_size_adequate,
        "winner": winner,
        "control": {
            "version": config["control_version"],
            "predictions": control_metrics["predictions"],
            "error_rate": control_error_rate * 100,
            "avg_mape": control_avg_mape,
        },
        "treatment": {
            "version": config["treatment_version"],
            "predictions": treatment_metrics["predictions"],
            "error_rate": treatment_error_rate * 100,
            "avg_mape": treatment_avg_mape,
        },
        "improvement": {
            "mape_improvement_percent": ((control_avg_mape - treatment_avg_mape) / control_avg_mape) * 100 if control_avg_mape > 0 else 0,
            "error_rate_improvement_percent": ((control_error_rate - treatment_error_rate) / control_error_rate) * 100 if control_error_rate > 0 else 0,
        },
    }


def load_json_file(file_path, logger, label: str) -> Dict[str, Dict[str, Any]]:
    if not file_path.exists():
        return {}
    try:
        with open(file_path) as handle:
            return json.load(handle)
    except Exception as exc:
        logger.error(f"Failed to load {label}: {exc}")
        return {}


def save_json_file(file_path, payload: Dict[str, Dict[str, Any]], logger, label: str) -> None:
    try:
        with open(file_path, "w") as handle:
            json.dump(payload, handle, indent=2)
    except Exception as exc:
        logger.error(f"Failed to save {label}: {exc}")
"""Support helpers for ML prediction validation and response shaping."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Sequence, Tuple

import polars as pl


def validate_feature_frame(
    features: pl.DataFrame,
    expected_features: Sequence[str],
) -> Tuple[bool, List[str]]:
    """Validate feature frame shape, schema, and value bounds."""
    errors: List[str] = []

    if features.shape[0] != 1:
        errors.append(f"Expected 1 row, got {features.shape[0]}")

    feature_cols = set(features.columns)
    expected_cols = set(expected_features)
    missing = expected_cols - feature_cols
    if missing:
        errors.append(f"Missing features: {missing}")

    for column in expected_features:
        if column in feature_cols:
            value = features[column][0]
            if not (0.0 <= value <= 1.0):
                errors.append(f"Feature {column} out of bounds: {value}")

    return len(errors) == 0, errors


def parse_prediction_result(prediction: Any, valid_actions: Sequence[str]) -> Tuple[str, float]:
    """Convert a model output payload into an action and confidence pair."""
    if isinstance(prediction, (list, tuple)):
        if len(prediction) > 0:
            action_idx = int(prediction[0])
            confidence = prediction[1] if len(prediction) > 1 else 0.5
        else:
            return "HOLD", 0.5
    else:
        action_idx = 1
        confidence = 0.5

    action = valid_actions[action_idx % len(valid_actions)]
    return action, max(0.0, min(1.0, float(confidence)))


def get_feature_importance_map(features: pl.DataFrame) -> Dict[str, float]:
    """Build a heuristic feature-importance view for a single feature frame."""
    feature_dict = features.to_dicts()[0]
    importance: Dict[str, float] = {"is_peak_hour": 0.20, "current_tariff_uah_mwh": 0.15, "price_trend": 0.08, "load_forecast_1h": 0.06, "day_of_week": 0.04}

    soc = feature_dict.get("soc_percent", 0.5)
    importance["soc_percent"] = 0.15 if 0.2 < soc < 0.8 else 0.20

    load = feature_dict.get("current_load_kw", 0.5)
    importance["current_load_kw"] = 0.12 if load > 0.2 else 0.08

    health = feature_dict.get("battery_health", 0.8)
    importance["battery_health"] = 0.12 if health < 0.5 else 0.08

    return importance


def generate_reasoning_text(action: str, features: pl.DataFrame, confidence: float) -> str:
    """Generate human-readable reasoning for a prediction."""
    feature_dict = features.to_dicts()[0]
    soc = feature_dict.get("soc_percent", 0.5)
    tariff = feature_dict.get("current_tariff_uah_mwh", 0.5)
    is_peak = feature_dict.get("is_peak_hour", 0.0)
    load = feature_dict.get("current_load_kw", 0.5)
    confidence_pct = int(confidence * 100)

    if action == "BUY":
        reason = f"Charge battery at current tariff level ({tariff:.0%}). "
        if is_peak < 0.5:
            reason += "Off-peak pricing provides favorable charging conditions."
        else:
            reason += "Low tariff relative to peak hours justifies charging."
        return reason + f" Confidence: {confidence_pct}%."

    if action == "SELL":
        reason = f"Discharge battery to supply current load ({load:.0%}). "
        if is_peak > 0.5:
            reason += "Peak hour pricing makes discharge most profitable."
        else:
            reason += "Discharge reduces grid consumption."
        return reason + f" Confidence: {confidence_pct}%."

    reason = "Current market conditions do not justify charging or discharging. "
    if soc < 0.3:
        reason += "Battery SOC is low, preferring charge availability."
    elif soc > 0.8:
        reason += "Battery is well-charged. Avoid additional degradation."
    else:
        reason += "Balance between economic opportunity and battery longevity."
    return reason + f" Confidence: {confidence_pct}%."


def build_prediction_response(
    action: str,
    confidence: float,
    reasoning: str,
    model_version: str,
    feature_importance: Dict[str, float],
    error: str | None = None,
) -> Dict[str, Any]:
    """Build the standard prediction response payload."""
    response: Dict[str, Any] = {
        "action": action,
        "confidence": confidence,
        "reasoning": reasoning,
        "model_version": model_version,
        "timestamp": datetime.now().isoformat(),
        "feature_importance": feature_importance,
    }
    if error is not None:
        response["error"] = error
    return response


def build_mock_prediction(features: pl.DataFrame, model_version: str) -> Dict[str, Any]:
    """Generate the mock prediction payload used when MLflow is unavailable."""
    feature_dict = features.to_dicts()[0]
    soc = feature_dict.get("soc_percent", 0.5)
    tariff = feature_dict.get("current_tariff_uah_mwh", 0.5)
    is_peak = feature_dict.get("is_peak_hour", 0.0)
    health = feature_dict.get("battery_health", 0.8)

    if health < 0.2:
        action = "HOLD"
        confidence = 0.95
    elif is_peak > 0.5 and soc > 0.3:
        action = "SELL"
        confidence = 0.75 + (soc - 0.3) * 0.2
    elif is_peak < 0.5 and soc < 0.8 and tariff < 0.5:
        action = "BUY"
        confidence = 0.70 + (0.8 - soc) * 0.15
    else:
        action = "HOLD"
        confidence = 0.65

    reasoning = f"Mock prediction: {action} (battery SOC: {soc:.0%}, tariff: {tariff:.0%})"
    return build_prediction_response(
        action,
        min(1.0, max(0.0, confidence)),
        reasoning,
        model_version,
        get_feature_importance_map(features),
    )


def build_error_response(error_msg: str, model_version: str) -> Dict[str, Any]:
    """Build the standard HOLD/error response payload."""
    return build_prediction_response(
        "HOLD",
        0.0,
        f"Prediction failed: {error_msg}",
        model_version,
        {},
        error=error_msg,
    )


def build_model_info(
    model_uri: str | None,
    model_version: str,
    mock_mode: bool,
    mlflow_available: bool,
    expected_features: Sequence[str],
    valid_actions: Sequence[str],
) -> Dict[str, Any]:
    """Build the public model-info payload."""
    return {
        "model_uri": model_uri,
        "model_version": model_version,
        "mock_mode": mock_mode,
        "mlflow_available": mlflow_available,
        "expected_features": list(expected_features),
        "valid_actions": list(valid_actions),
    }

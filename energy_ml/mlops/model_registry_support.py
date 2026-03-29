"""Support helpers for model-registry metadata and validation."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error


def generate_version_id(model_name: str, model_bytes: bytes, now: datetime) -> str:
    """Generate a stable model version identifier from timestamp and model hash."""
    model_hash = hashlib.md5(model_bytes).hexdigest()[:8]
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    return f"{model_name}-{timestamp}-{model_hash}"


def model_version_to_dict(model_version) -> Dict[str, Any]:
    """Serialize a model-version object to JSON-safe metadata."""
    return {
        "version_id": model_version.version_id,
        "model_name": model_version.model_name,
        "algorithm": model_version.algorithm,
        "created_at": model_version.created_at.isoformat(),
        "performance_metrics": model_version.performance_metrics,
        "feature_schema": model_version.feature_schema,
        "model_size_bytes": model_version.model_size_bytes,
        "deployment_stage": model_version.deployment_stage,
        "health_status": model_version.health_status,
        "validation_results": model_version.validation_results,
        "artifacts_path": str(model_version.artifacts_path),
    }


def load_model_version_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Hydrate raw JSON metadata into constructor-ready values."""
    hydrated = dict(metadata)
    hydrated["created_at"] = datetime.fromisoformat(hydrated["created_at"])
    hydrated["artifacts_path"] = Path(hydrated["artifacts_path"])
    return hydrated


def build_registry_index_entry(version_id: str, created_at: datetime, health_status: str, performance_metrics: Dict[str, float]) -> Dict[str, Any]:
    """Build the persisted registry-index entry for a model version."""
    return {
        "version_id": version_id,
        "created_at": created_at.isoformat(),
        "stage": "development",
        "health": health_status,
        "metrics": performance_metrics,
    }


def evaluate_model_health(
    model: Any,
    feature_schema: List[str],
    validation_data: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Run model health checks and return status plus validation details."""
    results: Dict[str, Any] = {}

    try:
        if not hasattr(model, "predict"):
            return "failed", {"error": "Model missing predict method"}

        dummy_features = np.random.random((1, len(feature_schema)))
        prediction = model.predict(dummy_features)
        results["dummy_prediction"] = float(prediction[0]) if hasattr(prediction, "__getitem__") else float(prediction)

        if np.isnan(results["dummy_prediction"]) or np.isinf(results["dummy_prediction"]):
            return "failed", {"error": "Model produces invalid predictions", "results": results}

        if hasattr(model, "feature_importances_"):
            importance_dict = {
                feature: float(importance)
                for feature, importance in zip(feature_schema, model.feature_importances_)
            }
            results["feature_importance"] = importance_dict
            zero_importance = [feature for feature, importance in importance_dict.items() if importance == 0]
            if zero_importance:
                results["warnings"] = f"Features with zero importance: {zero_importance}"

        if validation_data:
            x_val = validation_data.get("X")
            y_val = validation_data.get("y")
            if x_val is not None and y_val is not None:
                y_pred = model.predict(x_val)
                results["validation_mape"] = float(mean_absolute_percentage_error(y_val, y_pred))
                results["validation_rmse"] = float(np.sqrt(mean_squared_error(y_val, y_pred)))
                if results["validation_mape"] > 0.15:
                    return "degraded", results

        return "healthy", results
    except Exception as exc:
        return "failed", {"error": str(exc), "results": results}


def validate_staging_criteria(model_version) -> bool:
    """Check whether a model version meets staging deployment criteria."""
    mape = model_version.performance_metrics.get("mape", float("inf"))
    criteria = [
        model_version.health_status == "healthy",
        mape < 0.12,
        model_version.model_size_bytes < 50 * 1024 * 1024,
        len(model_version.feature_schema) > 0,
    ]
    return all(criteria)


def validate_production_criteria(model_version, now: datetime) -> bool:
    """Check whether a model version meets production deployment criteria."""
    mape = model_version.performance_metrics.get("mape", float("inf"))
    age = now - model_version.created_at
    criteria = [
        validate_staging_criteria(model_version),
        mape < 0.10,
        "validation_mape" in model_version.validation_results,
        age < timedelta(days=30),
    ]
    return all(criteria)


def read_json_file(file_path: Path, default: Any) -> Any:
    """Read JSON from disk with a default fallback."""
    if not file_path.exists():
        return default
    with open(file_path) as handle:
        return json.load(handle)


def write_json_file(file_path: Path, payload: Any) -> None:
    """Write JSON payload to disk."""
    with open(file_path, "w") as handle:
        json.dump(payload, handle, indent=2)


def update_registry_index_entry(registry_index: Dict[str, List[Dict[str, Any]]], model_version) -> Dict[str, List[Dict[str, Any]]]:
    """Apply updated stage and health values into the persisted registry index."""
    for model_versions in registry_index.values():
        for version_info in model_versions:
            if version_info["version_id"] == model_version.version_id:
                version_info["stage"] = model_version.deployment_stage
                version_info["health"] = model_version.health_status
                break
    return registry_index

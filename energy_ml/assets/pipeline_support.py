"""Support helpers for Dagster pipeline assets."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, Optional, TypedDict

from energy_ml.user_config import ConfigurationManager, UserConfigPayload, ConfigLoadResult


logger = logging.getLogger(__name__)


class AssetEnvelope(TypedDict, total=False):
    status: str
    timestamp: str
    error: str


class IntegratedPipelineAssetPayload(AssetEnvelope, total=False):
    action: str
    reasoning: str
    confidence: float
    estimated_savings: float
    battery_impact: float
    details: dict[str, Any]


class MLPredictionAssetPayload(AssetEnvelope, total=False):
    action: str
    confidence: float
    reasoning: str
    model_version: str
    feature_importance: dict[str, Any]


class PipelineStatusAssetPayload(AssetEnvelope, total=False):
    pipeline_status: str
    pipeline_action: str
    pipeline_confidence: float
    features_count: int
    features_valid: bool
    ml_status: str
    ml_action: str
    ml_confidence: float
    agreement: float


class OptimizationPreferencesAssetPayload(AssetEnvelope, total=False):
    strategy: str
    weights: dict[str, Any]
    constraints: dict[str, Any]
    preferences: dict[str, Any]


class BatteryPhysicsAssetPayload(AssetEnvelope, total=False):
    chemistry: str
    simulation_results: dict[str, Any]
    charging_curves: dict[str, Any]
    degradation_model: dict[str, Any]
    efficiency_model: dict[str, Any]


class RenewableGenerationAssetPayload(AssetEnvelope, total=False):
    solar_forecast: dict[str, Any]
    wind_forecast: dict[str, Any]
    total_renewable: dict[str, Any]
    weather_data: dict[str, Any]
    capacity_factors: dict[str, Any]
    integration: dict[str, Any]


class EnhancedPredictionAssetPayload(MLPredictionAssetPayload, total=False):
    base_prediction: dict[str, Any]
    optimization_applied: str
    physics_constraints: dict[str, Any]
    renewable_integration: dict[str, Any]
    enhancement_confidence: float


def _resolve_asset_config(user_config_data: Optional[UserConfigPayload]) -> ConfigLoadResult:
    """Resolve asset config without relying on exception-based control flow."""
    config_manager = ConfigurationManager()
    return config_manager.resolve_config(user_config_data)


def _config_error_text(config_result: ConfigLoadResult) -> str:
    return "; ".join(config_result.errors) if config_result.errors else "Configuration could not be loaded"


def _asset_timestamp() -> str:
    return datetime.now().isoformat()


def _with_asset_envelope(
    payload: dict[str, Any],
    *,
    status: str,
    error: Optional[str] = None,
) -> dict[str, Any]:
    envelope = {**payload, "timestamp": _asset_timestamp(), "status": status}
    if error is not None:
        envelope["error"] = error
    return envelope


def _load_asset_config_or_error(
    user_config_data: Optional[UserConfigPayload],
    *,
    error_context: str,
    fallback_payload: dict[str, Any],
) -> tuple[Optional[Any], Optional[dict[str, Any]]]:
    config_result = _resolve_asset_config(user_config_data)
    if not config_result.success or config_result.config is None:
        error_text = _config_error_text(config_result)
        logger.error("%s configuration failed: %s", error_context, error_text)
        return None, _with_asset_envelope(fallback_payload, status="error", error=error_text)
    return config_result.config, None
"""Canonical ML bridge owner for recommendation, forecast, and status operations."""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from energy_ml.features import FeatureEngineer
    from energy_ml.ml_integration import PredictionService
    from energy_ml.mlops.battery_physics import BatteryPhysicsEngine
    from energy_ml.mlops.optimization_engine import OptimizationEngine
    from energy_ml.mlops.renewable_forecasting import RenewableForecaster
    from energy_ml.pipeline import PipelineOrchestrator
    from energy_ml.user_config import ConfigurationManager
except ImportError:
    energy_ml_root = PROJECT_ROOT / "energy_ml"
    if str(energy_ml_root) not in sys.path:
        sys.path.insert(0, str(energy_ml_root))
    from features import FeatureEngineer
    from ml_integration import PredictionService
    from mlops.battery_physics import BatteryPhysicsEngine
    from mlops.optimization_engine import OptimizationEngine
    from mlops.renewable_forecasting import RenewableForecaster
    from pipeline import PipelineOrchestrator
    from user_config import ConfigurationManager

from src.data_pipeline.live_context import (
    build_historical_data,
    build_model_inputs,
    extract_hourly_price_map,
    load_live_context,
    safe_float,
)
from src.data_pipeline.ml_bridge_contracts import (
    build_error_response,
    build_forecast_response,
    build_hourly_forecast,
    build_named_success_response,
    build_recommendation_contract,
    build_recommendation_response,
    build_status_response,
    build_strategy_response,
    build_strategy_update_response,
    label_recommendation_origin,
)


logger = logging.getLogger(__name__)

INCUMBENT_SERVING_MODE = "incumbent"
LEARNED_POLICY_SERVING_MODE = "learned_policy"


def _load_user_config() -> Any:
    config_manager = ConfigurationManager()
    if hasattr(config_manager, "load_config_or_raise"):
        return config_manager.load_config_or_raise()
    return config_manager.load_config()


def _save_user_config(user_config: Any) -> None:
    config_manager = ConfigurationManager()
    result = config_manager.save_config(user_config)
    if not result.success:
        error_text = "; ".join(result.errors) if result.errors else "Configuration could not be saved"
        raise RuntimeError(error_text)


def _normalize_serving_mode(value: Optional[str]) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == LEARNED_POLICY_SERVING_MODE:
        return LEARNED_POLICY_SERVING_MODE
    return INCUMBENT_SERVING_MODE


def _build_prediction_service() -> PredictionService:
    return PredictionService.for_learned_policy(
        model_uri=os.getenv("ENERGY_ML_MODEL_URI"),
        model_name=os.getenv("ENERGY_ML_MODEL_NAME"),
        model_alias=os.getenv("ENERGY_ML_MODEL_ALIAS"),
        model_stage=os.getenv("ENERGY_ML_MODEL_STAGE"),
        tracking_uri=os.getenv("ENERGY_ML_MLFLOW_TRACKING_URI") or os.getenv("MLFLOW_TRACKING_URI"),
    )


def _get_learned_policy_recommendation(
    orchestrator: PipelineOrchestrator,
    user_config: Any,
    live_context: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    try:
        prediction_service = _build_prediction_service()
        model_info = prediction_service.get_model_info()
        if not model_info.get("model_available") and model_info.get("availability_error"):
            return None, model_info

        feature_engineer = FeatureEngineer()
        historical_data = build_historical_data(live_context)
        features = feature_engineer.extract_features(orchestrator, historical_data=historical_data)
        prediction = prediction_service.generate_prediction(
            features,
            user_strategy=getattr(user_config, "optimization_strategy", "balanced"),
        )

        if prediction.get("error") or not model_info.get("model_available"):
            return None, model_info

        learned_policy_recommendation = dict(prediction)
        learned_policy_recommendation.setdefault("estimated_savings", 0.0)
        learned_policy_recommendation.setdefault("battery_impact", 0.0)
        learned_policy_recommendation.setdefault("decision_source", "ml_recommendation")
        learned_policy_recommendation.setdefault("fallback_reason_code", "none")
        return learned_policy_recommendation, model_info
    except Exception as exc:
        logger.warning("Learned-policy adapter failed before inference: %s", exc)
        return None, {
            "serving_mode": LEARNED_POLICY_SERVING_MODE,
            "model_available": False,
            "availability_error": "learned_policy_feature_extraction_failed",
            "availability_message": str(exc),
            "fallback_reason_code": "learned_policy_feature_extraction_failed",
        }


def _apply_live_price_signal(
    recommendation: dict[str, Any],
    status: dict[str, Any],
    live_context: dict[str, Any],
) -> dict[str, Any]:
    adjusted = recommendation.copy()
    price_map = extract_hourly_price_map(live_context)
    current_hour = datetime.now().hour
    current_price = safe_float((live_context.get("price_signal") or {}).get("current_uah_kwh"), default=0.0)
    if current_price <= 0:
        current_price = safe_float(price_map.get(current_hour), default=0.0)

    prices = sorted(price_map.values())
    if current_price <= 0 or len(prices) < 8:
        adjusted["live_signal_applied"] = False
        return adjusted

    p25 = prices[max(0, int(len(prices) * 0.25) - 1)]
    p75 = prices[min(len(prices) - 1, int(len(prices) * 0.75))]

    battery_soc = safe_float((status.get("battery_state") or {}).get("soc_percent"), default=50.0)
    action = str(adjusted.get("action", "HOLD")).upper()
    confidence = safe_float(adjusted.get("confidence"), default=0.5)
    reasoning = str(adjusted.get("reasoning", "")).strip()

    updated = False
    if current_price <= p25 and battery_soc < 85 and action in {"HOLD", "SELL"}:
        action = "BUY"
        confidence = min(0.99, confidence + 0.06)
        reasoning = (
            f"{reasoning} Live price ({current_price:.2f} UAH/kWh) is in lower quartile ({p25:.2f}); "
            "opportunistic charging favored."
        ).strip()
        updated = True
    elif current_price >= p75 and battery_soc > 35 and action in {"HOLD", "BUY"}:
        action = "SELL"
        confidence = min(0.99, confidence + 0.06)
        reasoning = (
            f"{reasoning} Live price ({current_price:.2f} UAH/kWh) is in upper quartile ({p75:.2f}); "
            "discharging/export favored."
        ).strip()
        updated = True

    adjusted.update(
        {
            "action": action,
            "confidence": confidence,
            "reasoning": reasoning,
            "live_signal_applied": updated,
            "live_price_context": {
                "current_price_uah_kwh": current_price,
                "q25_price_uah_kwh": p25,
                "q75_price_uah_kwh": p75,
                "battery_soc_percent": battery_soc,
            },
        }
    )
    return adjusted


def _apply_incumbent_enhancements(
    recommendation: dict[str, Any],
    user_config: Any,
) -> dict[str, Any]:
    updated_recommendation = dict(recommendation)
    try:
        optimization_engine = OptimizationEngine()
        user_preferences = optimization_engine.get_user_strategy(user_config)
        optimized_recommendation = optimization_engine.optimize_decision(
            updated_recommendation,
            user_config.optimization_strategy,
            weights=user_preferences.get("weights", {}),
        )

        physics_engine = BatteryPhysicsEngine()
        physics_data = physics_engine.simulate_battery_behavior(user_config)
        physics_constrained = physics_engine.apply_physics_constraints(
            optimized_recommendation,
            {
                "physics_constraints": physics_data.get("physics_constraints", {}),
                "current_state": physics_data.get("current_state", {}),
                "power_limits": physics_data.get("power_limits", {}),
                "status": "success",
            },
        )

        renewable_forecaster = RenewableForecaster()
        renewable_data = renewable_forecaster.generate_forecasts(user_config)
        return renewable_forecaster.integrate_with_prediction(
            physics_constrained,
            renewable_data,
        )

    except Exception as exc:
        logger.warning("Enhanced recommendation failed, using base: %s", exc)
        return updated_recommendation


def _build_serving_state(requested_mode: str) -> dict[str, Any]:
    return {
        "requested_mode": requested_mode,
        "active_mode": INCUMBENT_SERVING_MODE,
        "adapter": "PredictionService",
        "fallback_used": False,
        "fallback_reason_code": "none",
        "model_info": None,
    }


def _resolve_current_recommendation(
    orchestrator: PipelineOrchestrator,
    user_config: Any,
    live_context: dict[str, Any],
    enhanced: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    serving_mode = _normalize_serving_mode(os.getenv("ENERGY_ML_SERVING_MODE"))
    serving = _build_serving_state(serving_mode)
    learned_policy_recommendation: dict[str, Any] | None = None

    if serving_mode == LEARNED_POLICY_SERVING_MODE:
        learned_policy_recommendation, model_info = _get_learned_policy_recommendation(
            orchestrator,
            user_config,
            live_context,
        )
        serving["model_info"] = model_info

    if learned_policy_recommendation is not None:
        serving["active_mode"] = LEARNED_POLICY_SERVING_MODE
        return learned_policy_recommendation, serving

    current_recommendation = label_recommendation_origin(
        orchestrator.calculate_recommendation(),
        decision_source="python_rule_engine",
        fallback_reason_code=(
            serving["model_info"].get("availability_error")
            if isinstance(serving.get("model_info"), dict)
            else "none"
        )
        or "none",
    )
    if enhanced:
        current_recommendation = _apply_incumbent_enhancements(current_recommendation, user_config)
    current_recommendation = _apply_live_price_signal(
        current_recommendation,
        orchestrator.get_status(),
        live_context,
    )

    if serving_mode == LEARNED_POLICY_SERVING_MODE:
        serving["fallback_used"] = True
        serving["fallback_reason_code"] = current_recommendation["fallback_reason_code"]

    return current_recommendation, serving


def get_recommendation(enhanced: bool = False) -> dict[str, Any]:
    """Get the current recommendation using the canonical bridge service."""

    try:
        live_context = load_live_context()
        user_config = _load_user_config()

        orchestrator = PipelineOrchestrator(user_config)
        if hasattr(orchestrator, "set_live_context"):
            orchestrator.set_live_context(live_context)

        current_recommendation, serving = _resolve_current_recommendation(
            orchestrator=orchestrator,
            user_config=user_config,
            live_context=live_context,
            enhanced=enhanced,
        )

        status = orchestrator.get_status()
        hourly_forecast = build_hourly_forecast(
            forecast_df=orchestrator.get_hourly_forecast(24),
            hourly_price_map=extract_hourly_price_map(live_context),
        )
        contract = build_recommendation_contract(user_config, live_context, current_recommendation)

        return build_recommendation_response(
            user_config=user_config,
            live_context=live_context,
            current_recommendation=current_recommendation,
            status=status,
            hourly_forecast=hourly_forecast,
            contract=contract,
            serving=serving,
            model_inputs=build_model_inputs(user_config, live_context),
        )
    except Exception as exc:
        logger.error("Error getting ML recommendation: %s", exc)
        return build_error_response(exc)


def get_forecast(hours: int = 24) -> dict[str, Any]:
    """Get hourly forecast rows for the requested horizon."""

    try:
        user_config = _load_user_config()
        orchestrator = PipelineOrchestrator(user_config)
        forecast = build_hourly_forecast(orchestrator.get_hourly_forecast(hours))
        return build_forecast_response(hours, forecast)
    except Exception as exc:
        logger.error("Error getting forecast: %s", exc)
        return build_error_response(exc)


def get_pipeline_status() -> dict[str, Any]:
    """Get the current pipeline status payload."""

    try:
        user_config = _load_user_config()
        orchestrator = PipelineOrchestrator(user_config)
        return build_status_response(orchestrator.get_status())
    except Exception as exc:
        logger.error("Error getting pipeline status: %s", exc)
        return build_error_response(exc)


def set_optimization_strategy(
    strategy: str,
    custom_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Persist a new optimization strategy for the active user configuration."""

    try:
        user_config = _load_user_config()
        user_config.optimization_strategy = strategy
        if custom_weights:
            user_config.custom_optimization_weights = custom_weights

        _save_user_config(user_config)

        optimization_engine = OptimizationEngine()
        strategy_info = optimization_engine.get_strategy_info(strategy)
        return build_strategy_update_response(strategy, strategy_info)
    except Exception as exc:
        logger.error("Error setting optimization strategy: %s", exc)
        return build_error_response(exc)


def get_optimization_strategy() -> dict[str, Any]:
    """Get the current optimization strategy metadata."""

    try:
        user_config = _load_user_config()
        optimization_engine = OptimizationEngine()
        strategy_info = optimization_engine.get_strategy_info(user_config.optimization_strategy)
        return build_strategy_response(user_config.optimization_strategy, strategy_info)
    except Exception as exc:
        logger.error("Error getting optimization strategy: %s", exc)
        return build_error_response(exc)


def get_battery_physics() -> dict[str, Any]:
    """Get current battery physics simulation data."""

    try:
        user_config = _load_user_config()
        physics_engine = BatteryPhysicsEngine()
        physics_data = physics_engine.simulate_battery_behavior(user_config)
        return build_named_success_response("physics_data", physics_data)
    except Exception as exc:
        logger.error("Error getting battery physics: %s", exc)
        return build_error_response(exc)


def get_renewable_forecast() -> dict[str, Any]:
    """Get the current renewable forecast payload."""

    try:
        user_config = _load_user_config()
        renewable_forecaster = RenewableForecaster()
        forecast_data = renewable_forecaster.generate_forecasts(user_config)
        return build_named_success_response("forecast_data", forecast_data)
    except Exception as exc:
        logger.error("Error getting renewable forecast: %s", exc)
        return build_error_response(exc)


__all__ = [
    "INCUMBENT_SERVING_MODE",
    "LEARNED_POLICY_SERVING_MODE",
    "_load_user_config",
    "_save_user_config",
    "get_battery_physics",
    "get_forecast",
    "get_optimization_strategy",
    "get_pipeline_status",
    "get_recommendation",
    "get_renewable_forecast",
    "set_optimization_strategy",
]
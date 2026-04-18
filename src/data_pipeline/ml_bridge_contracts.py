"""Normalized contract and response builders for the ML bridge surfaces."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.data_pipeline.live_context import safe_float


def normalize_action(action: Any) -> str:
    """Normalize various action spellings onto the bridge contract vocabulary."""

    normalized = str(action or "HOLD").strip().upper()
    if normalized in {"BUY", "CHARGE"}:
        return "BUY"
    if normalized in {"SELL", "DISCHARGE"}:
        return "SELL"
    return "HOLD"


def map_action_to_execution_command(action: str) -> str:
    """Map a normalized action onto the low-level execution command."""

    if action == "BUY":
        return "charge"
    if action == "SELL":
        return "discharge"
    return "hold"


def build_normalized_action(
    action: Any,
    confidence: Any = None,
    power_kw: Any = None,
    base_action: Any = None,
    strategy_adjusted: bool = False,
    strategy_adjustment_notes: list[str] | None = None,
    power_source: str | None = None,
) -> dict[str, Any]:
    """Build the normalized action payload exposed to dashboard callers."""

    normalized_action = normalize_action(action)
    normalized_base_action = normalize_action(base_action or action)
    execution_command = map_action_to_execution_command(normalized_action)
    confidence_value = safe_float(confidence, default=-1.0)
    normalized_confidence = min(1.0, max(0.0, confidence_value)) if confidence_value >= 0 else None
    numeric_power = safe_float(power_kw, default=float("nan"))

    if execution_command == "hold":
        normalized_power = 0.0
    elif numeric_power == numeric_power:
        normalized_power = round(numeric_power, 3)
    else:
        normalized_power = None

    return {
        "action": normalized_action,
        "base_action": normalized_base_action,
        "execution_command": execution_command,
        "power_kw": normalized_power,
        "power_source": power_source
        or (
            "hold_zero"
            if execution_command == "hold"
            else "not_provided"
            if normalized_power is None
            else "provided"
        ),
        "confidence": normalized_confidence,
        "confidence_percent": round(normalized_confidence * 100) if normalized_confidence is not None else None,
        "strategy_adjusted": bool(strategy_adjusted),
        "strategy_adjustment_notes": strategy_adjustment_notes or [],
    }


def build_recommendation_contract(
    user_config: Any,
    live_context: dict[str, Any],
    recommendation: dict[str, Any],
) -> dict[str, Any]:
    """Build the normalized bridge contract for recommendations and provenance."""

    battery_signal = live_context.get("battery_signal") if isinstance(live_context.get("battery_signal"), dict) else {}
    state_source = str(battery_signal.get("source") or "config_fallback")

    normalized_action = recommendation.get("normalized_action")
    if not isinstance(normalized_action, dict):
        normalized_action = build_normalized_action(
            action=recommendation.get("action"),
            confidence=recommendation.get("confidence"),
            power_kw=recommendation.get("action_kw", recommendation.get("power_kw")),
            base_action=recommendation.get("base_action", recommendation.get("action")),
            strategy_adjusted=bool(recommendation.get("strategy_adjusted", False)),
            strategy_adjustment_notes=recommendation.get("strategy_adjustment_notes", []),
            power_source="python_bridge"
            if recommendation.get("action_kw") is not None or recommendation.get("power_kw") is not None
            else "not_provided",
        )

    return {
        "version": "learned_policy_migration_v1",
        "normalized_action": normalized_action,
        "provenance": {
            "decision_source": str(recommendation.get("decision_source") or "python_rule_engine"),
            "fallback_reason_code": str(recommendation.get("fallback_reason_code") or "none"),
            "fallback_used": str(recommendation.get("fallback_reason_code") or "none") != "none",
            "state_source": state_source,
            "state_source_detail": battery_signal.get("source_detail"),
            "telemetry_classification": "simulated_operational_telemetry"
            if state_source == "simulator_backed_telemetry"
            else "fabricated_training_scaffolding",
        },
        "strategy_context": {
            "optimization_strategy": getattr(user_config, "optimization_strategy", "balanced"),
            "load_profile_type": getattr(user_config, "load_profile_type", "standard"),
            "strategy_source": "tenant_config",
        },
    }


def label_recommendation_origin(
    recommendation: dict[str, Any],
    *,
    decision_source: str,
    fallback_reason_code: str,
) -> dict[str, Any]:
    """Attach bridge provenance onto the raw recommendation payload."""

    labeled = dict(recommendation)
    labeled["decision_source"] = decision_source
    labeled["fallback_reason_code"] = fallback_reason_code
    return labeled


def build_hourly_forecast(
    forecast_df: Any,
    hourly_price_map: dict[int, float] | None = None,
) -> list[dict[str, Any]]:
    """Serialize forecast rows into the bridge response contract."""

    include_price_context = hourly_price_map is not None
    price_map = hourly_price_map or {}
    hourly_forecast: list[dict[str, Any]] = []

    for row in forecast_df.iter_rows(named=True):
        payload = {
            "hour": row["hour"],
            "action": row["action"],
            "confidence": row["confidence"],
            "reasoning": row["reasoning"],
            "savings_estimate": row["savings_estimate"],
            "battery_impact": row["battery_impact"],
        }
        if include_price_context:
            price_uah_kwh = price_map.get(int(row["hour"]))
            payload["price_uah_kwh"] = price_uah_kwh
            payload["price_uah_mwh"] = price_uah_kwh * 1000 if price_uah_kwh is not None else None
        hourly_forecast.append(payload)

    return hourly_forecast


def build_recommendation_response(
    *,
    user_config: Any,
    live_context: dict[str, Any],
    current_recommendation: dict[str, Any],
    status: dict[str, Any],
    hourly_forecast: list[dict[str, Any]],
    contract: dict[str, Any],
    serving: dict[str, Any],
    model_inputs: dict[str, Any],
) -> dict[str, Any]:
    """Build the dashboard-facing recommendation payload."""

    hourly_savings = current_recommendation.get("estimated_savings", 0)
    daily_savings = sum(row["savings_estimate"] for row in hourly_forecast)

    return {
        "success": True,
        "action": current_recommendation["action"],
        "confidence": current_recommendation["confidence"],
        "reasoning": current_recommendation["reasoning"],
        "estimated_savings": hourly_savings,
        "hourly_forecast": hourly_forecast,
        "daily_savings_estimate": daily_savings,
        "monthly_savings_estimate": daily_savings * 30,
        "annual_savings_estimate": daily_savings * 365,
        "battery_impact": {
            "current_soc": status["battery_state"]["soc_percent"],
            "health_loss": current_recommendation.get("battery_impact", 0),
            "cycles_remaining": status["battery_state"]["cycles_remaining"],
        },
        "feature_provenance": {
            "tenant_id": live_context.get("tenant_id"),
            "captured_at": live_context.get("captured_at"),
            "sources": {
                "profile": "tenant_user_config",
                "prices": (live_context.get("price_signal") or {}).get("source", "pipeline_default_tariff"),
                "weather": (live_context.get("weather_signal") or {}).get(
                    "source", "pipeline_internal_weather_model"
                ),
            },
            "used_live_price_signal": bool(current_recommendation.get("live_signal_applied")),
            "used_live_weather_signal": bool((live_context.get("weather_signal") or {}).get("current")),
            "feature_count_estimate": 18,
        },
        "normalized_action": contract["normalized_action"],
        "provenance": contract["provenance"],
        "contract": contract,
        "serving": serving,
        "model_inputs": model_inputs,
        "pipeline_status": status,
        "timestamp": datetime.now().isoformat(),
    }


def build_forecast_response(hours: int, forecast: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the bridge forecast response payload."""

    return {
        "success": True,
        "forecast": forecast,
        "hours": hours,
        "timestamp": datetime.now().isoformat(),
    }


def build_status_response(status: dict[str, Any]) -> dict[str, Any]:
    """Build the bridge status response payload."""

    return {
        "success": True,
        "status": status,
        "timestamp": datetime.now().isoformat(),
    }


def build_strategy_update_response(strategy: str, strategy_info: dict[str, Any]) -> dict[str, Any]:
    """Build the response for optimization strategy updates."""

    return {
        "success": True,
        "strategy": strategy,
        "description": strategy_info.get("description", f"Strategy: {strategy}"),
        "weights": strategy_info.get("weights", {}),
        "constraints": strategy_info.get("constraints", {}),
        "timestamp": datetime.now().isoformat(),
    }


def build_strategy_response(strategy: str, strategy_info: dict[str, Any]) -> dict[str, Any]:
    """Build the response for the current optimization strategy."""

    return {
        "success": True,
        "strategy": strategy,
        "description": strategy_info.get("description", ""),
        "weights": strategy_info.get("weights", {}),
        "constraints": strategy_info.get("constraints", {}),
        "available_strategies": strategy_info.get("available_strategies", []),
        "current_cycles": strategy_info.get("current_cycles", 0),
        "timestamp": datetime.now().isoformat(),
    }


def build_named_success_response(payload_name: str, payload: Any) -> dict[str, Any]:
    """Build a timestamped success payload with a single named body field."""

    return {
        "success": True,
        payload_name: payload,
        "timestamp": datetime.now().isoformat(),
    }


def build_error_response(error: Exception | str) -> dict[str, Any]:
    """Build the standard bridge error payload."""

    return {
        "success": False,
        "error": str(error),
        "timestamp": datetime.now().isoformat(),
    }


__all__ = [
    "build_error_response",
    "build_forecast_response",
    "build_hourly_forecast",
    "build_named_success_response",
    "build_normalized_action",
    "build_recommendation_contract",
    "build_recommendation_response",
    "build_status_response",
    "build_strategy_response",
    "build_strategy_update_response",
    "label_recommendation_origin",
    "map_action_to_execution_command",
    "normalize_action",
]
"""Support helpers for serving API response shaping and simulation adapters."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Sequence


def build_health_components(
    model_registry_ok: bool,
    feature_store_ok: bool,
    physics_engine_count: int,
    optimization_engine_count: int,
    cached_model: Any,
) -> Dict[str, Any]:
    return {
        "model_registry": model_registry_ok,
        "feature_store": feature_store_ok,
        "physics_engines": physics_engine_count > 0,
        "optimization_engines": optimization_engine_count > 0,
        "cached_model": cached_model is not None,
    }


def build_health_response_payload(components: Dict[str, Any], latency_ms: float, timestamp: datetime) -> Dict[str, Any]:
    return {
        "status": "healthy" if all(components.values()) else "degraded",
        "timestamp": timestamp.isoformat(),
        "version": "2.0.0",
        "models_loaded": components.get("cached_model", False),
        "latency_ms": latency_ms,
        "components": components,
    }


def build_feature_vector(features: Dict[str, Any]) -> List[List[float]]:
    return [[
        float(features.get("battery_soc", 0.0)),
        float(features.get("grid_price_uah_kwh", 0.0)),
        float(features.get("solar_generation_kw", 0.0)),
        float(features.get("wind_generation_kw", 0.0)),
        float(features.get("load_demand_kw", 0.0)),
        float(features.get("temperature_celsius", 25.0)),
    ]]


def build_fallback_prediction(features: Dict[str, Any], timestamp: datetime) -> Dict[str, Any]:
    battery_soc = float(features.get("battery_soc", 0.5))
    price = float(features.get("grid_price_uah_kwh", 0.0))
    renewable_supply = float(features.get("solar_generation_kw", 0.0)) + float(features.get("wind_generation_kw", 0.0))
    load_demand = float(features.get("load_demand_kw", 0.0))

    if renewable_supply > load_demand and battery_soc < 0.85:
        action = "BUY"
        confidence = 0.72
        reasoning = "Fallback prediction favors charging because renewable generation exceeds current load."
    elif price >= 10.0 and battery_soc > 0.3:
        action = "SELL"
        confidence = 0.70
        reasoning = "Fallback prediction favors discharge during a high grid-price interval."
    else:
        action = "HOLD"
        confidence = 0.60
        reasoning = "Fallback prediction holds to preserve battery flexibility under mixed conditions."

    return {
        "action": action,
        "confidence": confidence,
        "reasoning": reasoning,
        "timestamp": timestamp.isoformat(),
    }


def coerce_prediction_output(raw_prediction: Any, features: Dict[str, Any], timestamp: datetime) -> Dict[str, Any]:
    if isinstance(raw_prediction, dict):
        prediction = raw_prediction.copy()
        prediction.setdefault("action", "HOLD")
        prediction.setdefault("confidence", 0.5)
        prediction.setdefault("reasoning", "Serving API normalized model output.")
        prediction.setdefault("timestamp", timestamp.isoformat())
        return prediction

    if hasattr(raw_prediction, "tolist"):
        raw_prediction = raw_prediction.tolist()

    if isinstance(raw_prediction, list):
        if raw_prediction and isinstance(raw_prediction[0], list):
            raw_prediction = raw_prediction[0]
        elif len(raw_prediction) == 1:
            raw_prediction = raw_prediction[0]

    if isinstance(raw_prediction, tuple):
        raw_prediction = list(raw_prediction)

    if isinstance(raw_prediction, list):
        if raw_prediction and isinstance(raw_prediction[0], dict):
            return coerce_prediction_output(raw_prediction[0], features, timestamp)

        if raw_prediction:
            try:
                action_idx = int(raw_prediction[0])
                confidence = float(raw_prediction[1]) if len(raw_prediction) > 1 else 0.5
                action = ["BUY", "SELL", "HOLD"][action_idx % 3]
                return {
                    "action": action,
                    "confidence": max(0.0, min(1.0, confidence)),
                    "reasoning": f"Serving API adapted model output to {action}.",
                    "timestamp": timestamp.isoformat(),
                }
            except (TypeError, ValueError):
                pass

    return build_fallback_prediction(features, timestamp)


def estimate_power_kw(action: str, load_demand_kw: float) -> float:
    if action == "HOLD":
        return 0.0
    return min(max(load_demand_kw, 0.0), 5.0)


def estimate_profit_uah(action: str, power_kw: float, duration_h: float, grid_price_uah_kwh: float) -> float:
    direction = 1.0 if action == "SELL" else -1.0 if action == "BUY" else 0.0
    return direction * power_kw * duration_h * grid_price_uah_kwh


def build_prediction_response_payload(
    decision: Dict[str, Any],
    request: Any,
    prediction_id: str,
    model_version: str,
    strategy: str,
    timestamp: datetime,
) -> Dict[str, Any]:
    action = str(decision.get("action", "HOLD"))
    power_kw = float(decision.get("power_kw", estimate_power_kw(action, float(request.load_demand_kw))))
    duration_h = float(decision.get("duration_h", 0.0 if action == "HOLD" else 1.0))
    expected_profit_uah = float(
        decision.get(
            "expected_profit_uah",
            estimate_profit_uah(action, power_kw, duration_h, float(request.grid_price_uah_kwh)),
        )
    )
    health_impact_percent = float(
        decision.get("health_impact_percent", 0.0 if action == "HOLD" else min(100.0, power_kw * duration_h * 0.1))
    )

    return {
        "action": action,
        "power_kw": power_kw,
        "duration_h": duration_h,
        "confidence": float(decision.get("confidence", 0.5)),
        "expected_profit_uah": expected_profit_uah,
        "health_impact_percent": health_impact_percent,
        "reasoning": str(decision.get("reasoning", "Optimization completed.")),
        "strategy_used": str(decision.get("optimization_strategy", strategy)),
        "prediction_id": prediction_id,
        "timestamp": timestamp.isoformat(),
        "model_version": model_version,
    }


def simulate_battery_response(
    physics_data: Dict[str, Any],
    request: Any,
    battery_capacity_kwh: float,
) -> Dict[str, Any]:
    initial_state = dict(physics_data.get("current_state", {}))
    power_limits = physics_data.get("power_limits", {})
    efficiency_model = physics_data.get("efficiency_model", {})
    constraints = physics_data.get("physics_constraints", {})

    if request.power_kw >= 0:
        applied_power_kw = min(float(request.power_kw), float(power_limits.get("max_charge_power_kw", request.power_kw)))
        efficiency = float(efficiency_model.get("charge_efficiency", 1.0))
        energy_delta_kwh = applied_power_kw * request.duration_h * efficiency
    else:
        applied_power_kw = -min(abs(float(request.power_kw)), float(power_limits.get("max_discharge_power_kw", abs(request.power_kw))))
        efficiency = max(float(efficiency_model.get("discharge_efficiency", 1.0)), 1e-6)
        energy_delta_kwh = applied_power_kw * request.duration_h / efficiency

    initial_soc_percent = float(initial_state.get("soc_percent", 50.0))
    soc_delta_percent = (energy_delta_kwh / max(battery_capacity_kwh, 1e-6)) * 100.0
    final_soc_percent = initial_soc_percent + soc_delta_percent
    min_soc = float(constraints.get("min_soc_physics", 0.0))
    max_soc = float(constraints.get("max_soc_physics", 100.0))
    final_soc_percent = min(max(final_soc_percent, min_soc), max_soc)

    final_state = {
        **initial_state,
        "soc_percent": final_soc_percent,
        "temperature": request.temperature,
        "cycles_completed": float(initial_state.get("cycles_completed", 0.0)) + abs(applied_power_kw) * request.duration_h / max(battery_capacity_kwh, 1e-6),
        "estimated_energy_delta_kwh": energy_delta_kwh,
    }

    return {
        "initial_state": initial_state,
        "final_state": final_state,
        "physics_summary": {
            "chemistry": physics_data.get("chemistry", request.battery_type),
            "power_limits": power_limits,
            "efficiency_model": efficiency_model,
            "degradation_model": physics_data.get("degradation_model", {}),
            "thermal_model": physics_data.get("thermal_model", {}),
        },
        "simulation_params": {
            "requested_power_kw": request.power_kw,
            "applied_power_kw": applied_power_kw,
            "duration_h": request.duration_h,
            "temperature": request.temperature,
            "battery_type": request.battery_type,
        },
    }


def summarize_model_versions(production_models: Sequence[Any], staging_models: Sequence[Any], development_models: Sequence[Any]) -> Dict[str, Any]:
    def _serialize(models: Sequence[Any]) -> List[Dict[str, Any]]:
        return [
            {
                "version_id": model.version_id,
                "created_at": model.created_at.isoformat(),
                "performance_mape": model.performance_metrics.get("test_mape", 0),
                "health_status": model.health_status,
            }
            for model in models[:5]
        ]

    return {
        "production": _serialize(production_models),
        "staging": _serialize(staging_models),
        "development": len(development_models),
    }


def prediction_value_from_decision(decision: Dict[str, Any]) -> float:
    return float(decision.get("expected_profit_uah", decision.get("confidence", 0.0)))


def prune_disconnected_websockets(current_connections: Iterable[Any], disconnected: Iterable[Any]) -> List[Any]:
    disconnected_set = set(disconnected)
    return [connection for connection in current_connections if connection not in disconnected_set]
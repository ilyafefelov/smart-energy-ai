"""Support helpers for optimization-engine scoring and response shaping."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def build_strategy_response(
    strategy: str,
    strategy_config: Dict[str, Any],
    custom_weights: Optional[Dict[str, float]],
    timestamp: str,
    *,
    success: bool,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the stable public envelope for strategy lookups."""
    return {
        "strategy": strategy,
        "description": strategy_config["description"],
        "weights": dict(strategy_config["weights"]),
        "constraints": dict(strategy_config["constraints"]),
        "custom_weights": custom_weights,
        "timestamp": timestamp,
        "success": success,
        "error": error,
    }


def resolve_weights(
    strategy: str,
    strategies: Dict[str, Dict[str, Any]],
    weights: Optional[Dict[str, float]],
) -> Dict[str, float]:
    """Resolve either explicit weights or the configured strategy defaults."""
    if weights is not None:
        return dict(weights)
    if strategy in strategies:
        return dict(strategies[strategy]["weights"])
    return dict(strategies["balanced"]["weights"])


def calculate_earnings_score(action: str, renewable_data: Optional[Dict[str, Any]], current_hour: int) -> float:
    """Calculate the earnings potential score for an action."""
    is_peak = 6 <= current_hour < 23
    renewable_available = False
    if renewable_data and renewable_data.get("status") == "success":
        total_renewable = renewable_data.get("total_renewable", {})
        renewable_available = total_renewable.get(f"hour_{current_hour}", 0) > 0

    if action == "SELL":
        return 0.9 + (0.1 if renewable_available else 0) if is_peak else 0.4 + (0.2 if renewable_available else 0)
    if action == "BUY":
        return 0.8 if not is_peak else 0.3
    return 0.5


def calculate_battery_health_score(action: str, physics_data: Optional[Dict[str, Any]]) -> float:
    """Calculate the battery-health score for an action."""
    if physics_data and physics_data.get("status") == "success":
        degradation_model = physics_data.get("degradation_model", {})
        cycle_impact = degradation_model.get("cycle_impact", 0.01)
    else:
        cycle_impact = 0.01 if action in ["BUY", "SELL"] else 0

    if action == "HOLD":
        return 1.0
    if action == "BUY":
        return max(0, 1.0 - cycle_impact * 2)
    return max(0, 1.0 - cycle_impact * 4)


def calculate_charge_availability_score(action: str, physics_data: Optional[Dict[str, Any]]) -> float:
    """Calculate the charge-availability score for an action."""
    current_soc = 60.0
    if physics_data and physics_data.get("status") == "success":
        simulation_results = physics_data.get("simulation_results", {})
        current_soc = simulation_results.get("current_soc", 60.0)

    if action == "BUY":
        return max(0, (100 - current_soc) / 100)
    if action == "SELL":
        return max(0, (current_soc - 20) / 80)
    return 0.7 if 40 <= current_soc <= 80 else 0.4


def calculate_action_score(
    action: str,
    weights: Dict[str, float],
    physics_data: Optional[Dict[str, Any]],
    renewable_data: Optional[Dict[str, Any]],
    current_hour: int,
) -> float:
    """Calculate the weighted optimization score for a candidate action."""
    earnings_score = calculate_earnings_score(action, renewable_data, current_hour)
    battery_health_score = calculate_battery_health_score(action, physics_data)
    charge_availability_score = calculate_charge_availability_score(action, physics_data)
    total_score = (
        earnings_score * weights.get("earnings", 0.33)
        + battery_health_score * weights.get("battery_health", 0.33)
        + charge_availability_score * weights.get("charge_availability", 0.33)
    )
    return min(1.0, max(0.0, total_score))


def calculate_confidence_adjustment(
    base_action: str,
    optimized_action: str,
    optimization_score: float,
) -> float:
    """Calculate confidence adjustment after optimization."""
    if base_action == optimized_action:
        return 0.1 + (optimization_score - 0.5) * 0.2
    if optimization_score > 0.8:
        return 0.05
    if optimization_score > 0.6:
        return 0.0
    return -0.1


def generate_optimization_reasoning(
    base_action: str,
    optimized_action: str,
    strategy_description: str,
    action_scores: Dict[str, float],
) -> str:
    """Generate public optimization reasoning text."""
    if base_action == optimized_action:
        reasoning = f"Base ML prediction aligns with {strategy_description}. "
    else:
        reasoning = f"Optimized from {base_action} to {optimized_action} for {strategy_description}. "

    reasoning += f"Optimization score: {action_scores.get(optimized_action, 0):.2f}. "
    if optimized_action == "BUY":
        return reasoning + "Charging favored to improve charge availability and utilize low prices."
    if optimized_action == "SELL":
        return reasoning + "Discharging favored to capture high prices while maintaining battery health."
    return reasoning + "Holding position to preserve battery health and await better conditions."


def check_constraints(
    action: str,
    strategy: str,
    strategies: Dict[str, Dict[str, Any]],
    daily_cycle_count: int,
    physics_data: Optional[Dict[str, Any]],
) -> Tuple[bool, str]:
    """Check whether a candidate action satisfies the configured strategy constraints."""
    if strategy not in strategies:
        return True, ""

    constraints = strategies[strategy]["constraints"]
    current_soc = 60.0
    if physics_data and physics_data.get("status") == "success":
        simulation_results = physics_data.get("simulation_results", {})
        current_soc = simulation_results.get("current_soc", 60.0)

    min_soc = constraints.get("min_soc", 0)
    if action == "SELL" and current_soc <= min_soc:
        return False, f"SOC too low ({current_soc:.0f}%) for discharge (min: {min_soc}%)."

    max_cycles = constraints.get("max_cycles_per_day", 999)
    if action in ["BUY", "SELL"] and daily_cycle_count >= max_cycles:
        return False, f"Daily cycle limit reached ({daily_cycle_count}/{max_cycles})."

    return True, ""


def build_optimized_prediction(
    base_prediction: Dict[str, Any],
    best_action: str,
    new_confidence: float,
    reasoning: str,
    strategy: str,
    action_scores: Dict[str, float],
    constraints_met: bool,
    constraint_message: str,
    timestamp: str,
) -> Dict[str, Any]:
    """Build the public optimized-prediction payload."""
    return {
        **base_prediction,
        "action": best_action,
        "confidence": new_confidence,
        "reasoning": reasoning,
        "optimization_strategy": strategy,
        "action_scores": action_scores,
        "constraints_met": constraints_met,
        "constraint_message": constraint_message,
        "base_action": base_prediction.get("action", "HOLD"),
        "optimization_applied": True,
        "timestamp": timestamp,
    }


def build_strategy_info(
    strategy: str,
    strategies: Dict[str, Dict[str, Any]],
    daily_cycle_count: int,
) -> Dict[str, Any]:
    """Build the public strategy-info payload."""
    available = list(strategies.keys())
    if strategy in strategies:
        return {
            "strategy": strategy,
            **strategies[strategy],
            "current_cycles": daily_cycle_count,
            "available_strategies": available,
        }
    return {
        "strategy": "unknown",
        "error": f"Strategy {strategy} not found",
        "available_strategies": available,
    }
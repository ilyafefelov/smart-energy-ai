#!/usr/bin/env python3
"""
ML Integration API Bridge for Dashboard
Provides a command-line interface to the Phase 4F ML Pipeline
"""

import sys
import json
import logging
import argparse
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

INCUMBENT_SERVING_MODE = 'incumbent'
LEARNED_POLICY_SERVING_MODE = 'learned_policy'

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    # Try relative imports first
    from .features import FeatureEngineer
    from .ml_integration import PredictionService
    from .pipeline import PipelineOrchestrator
    from .user_config import ConfigurationManager
    from .mlops.optimization_engine import OptimizationEngine
    from .mlops.battery_physics import BatteryPhysicsEngine
    from .mlops.renewable_forecasting import RenewableForecaster
except ImportError:
    # Fallback to absolute imports
    try:
        from features import FeatureEngineer
        from ml_integration import PredictionService
        from pipeline import PipelineOrchestrator
        from user_config import ConfigurationManager
        from mlops.optimization_engine import OptimizationEngine
        from mlops.battery_physics import BatteryPhysicsEngine
        from mlops.renewable_forecasting import RenewableForecaster
    except ImportError as e:
        logging.error(f"Failed to import modules: {e}")
        sys.exit(1)


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def load_user_config() -> Any:
    """Load user config using the shared ConfigurationManager contract."""
    config_manager = ConfigurationManager()
    if hasattr(config_manager, 'load_config_or_raise'):
        return config_manager.load_config_or_raise()
    return config_manager.load_config()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
        if numeric != numeric:
            return default
        return numeric
    except Exception:
        return default


def _load_live_context() -> Dict[str, Any]:
    raw = os.getenv('ENERGY_ML_LIVE_CONTEXT_JSON')
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
        return payload if isinstance(payload, dict) else {}
    except Exception as exc:
        logger.warning('Failed to parse ENERGY_ML_LIVE_CONTEXT_JSON: %s', exc)
        return {}


def _normalize_serving_mode(value: Optional[str]) -> str:
    normalized = str(value or '').strip().lower()
    if normalized == LEARNED_POLICY_SERVING_MODE:
        return LEARNED_POLICY_SERVING_MODE
    return INCUMBENT_SERVING_MODE


def _build_historical_data(live_context: Dict[str, Any]) -> Dict[str, Any]:
    price_signal = live_context.get('price_signal') or {}
    forecast_rows = price_signal.get('forecast_next24h') or []
    tariff_history = []

    current_price = _safe_float(price_signal.get('current_uah_kwh'), default=-1)
    if current_price > 0:
        tariff_history.append(current_price * 1000)

    if isinstance(forecast_rows, list):
        for row in forecast_rows:
            if not isinstance(row, dict):
                continue
            forecast_price = _safe_float(row.get('price'), default=-1)
            if forecast_price > 0:
                tariff_history.append(forecast_price * 1000)

    return {
        'tariff_history': tariff_history,
    }


def _label_recommendation_origin(
    recommendation: Dict[str, Any],
    *,
    decision_source: str,
    fallback_reason_code: str,
) -> Dict[str, Any]:
    labeled = dict(recommendation)
    labeled['decision_source'] = decision_source
    labeled['fallback_reason_code'] = fallback_reason_code
    return labeled


def _build_prediction_service() -> PredictionService:
    return PredictionService.for_learned_policy(
        model_uri=os.getenv('ENERGY_ML_MODEL_URI'),
        model_name=os.getenv('ENERGY_ML_MODEL_NAME'),
        model_alias=os.getenv('ENERGY_ML_MODEL_ALIAS'),
        model_stage=os.getenv('ENERGY_ML_MODEL_STAGE'),
        tracking_uri=os.getenv('ENERGY_ML_MLFLOW_TRACKING_URI') or os.getenv('MLFLOW_TRACKING_URI'),
    )


def _get_learned_policy_recommendation(
    orchestrator: PipelineOrchestrator,
    user_config: Any,
    live_context: Dict[str, Any],
) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    try:
        prediction_service = _build_prediction_service()
        model_info = prediction_service.get_model_info()
        if not model_info.get('model_available') and model_info.get('availability_error'):
            return None, model_info

        feature_engineer = FeatureEngineer()
        features = feature_engineer.extract_features(
            orchestrator,
            historical_data=_build_historical_data(live_context),
        )
        prediction = prediction_service.generate_prediction(
            features,
            user_strategy=getattr(user_config, 'optimization_strategy', 'balanced'),
        )

        if prediction.get('error') or not model_info.get('model_available'):
            return None, model_info

        learned_policy_recommendation = dict(prediction)
        learned_policy_recommendation.setdefault('estimated_savings', 0.0)
        learned_policy_recommendation.setdefault('battery_impact', 0.0)
        learned_policy_recommendation.setdefault('decision_source', 'ml_recommendation')
        learned_policy_recommendation.setdefault('fallback_reason_code', 'none')
        return learned_policy_recommendation, model_info
    except Exception as e:
        logger.warning(f"Learned-policy adapter failed before inference: {e}")
        return None, {
            'serving_mode': LEARNED_POLICY_SERVING_MODE,
            'model_available': False,
            'availability_error': 'learned_policy_feature_extraction_failed',
            'availability_message': str(e),
            'fallback_reason_code': 'learned_policy_feature_extraction_failed',
        }


def _normalize_action(action: Any) -> str:
    normalized = str(action or 'HOLD').strip().upper()
    if normalized in {'BUY', 'CHARGE'}:
        return 'BUY'
    if normalized in {'SELL', 'DISCHARGE'}:
        return 'SELL'
    return 'HOLD'


def _map_action_to_execution_command(action: str) -> str:
    if action == 'BUY':
        return 'charge'
    if action == 'SELL':
        return 'discharge'
    return 'hold'


def _build_normalized_action(
    action: Any,
    confidence: Any = None,
    power_kw: Any = None,
    base_action: Any = None,
) -> Dict[str, Any]:
    normalized_action = _normalize_action(action)
    normalized_base_action = _normalize_action(base_action or action)
    execution_command = _map_action_to_execution_command(normalized_action)
    confidence_value = _safe_float(confidence, default=-1.0)
    normalized_confidence = min(1.0, max(0.0, confidence_value)) if confidence_value >= 0 else None
    numeric_power = _safe_float(power_kw, default=float('nan'))

    if execution_command == 'hold':
        normalized_power = 0.0
    elif numeric_power == numeric_power:
        normalized_power = round(numeric_power, 3)
    else:
        normalized_power = None

    return {
        'action': normalized_action,
        'base_action': normalized_base_action,
        'execution_command': execution_command,
        'power_kw': normalized_power,
        'power_source': 'hold_zero' if execution_command == 'hold' else 'not_provided' if normalized_power is None else 'provided',
        'confidence': normalized_confidence,
        'confidence_percent': round(normalized_confidence * 100) if normalized_confidence is not None else None,
        'strategy_adjusted': False,
        'strategy_adjustment_notes': [],
    }


def _build_recommendation_contract(
    user_config: Any,
    live_context: Dict[str, Any],
    recommendation: Dict[str, Any],
) -> Dict[str, Any]:
    battery_signal = live_context.get('battery_signal') or {}
    state_source = str(battery_signal.get('source') or 'config_fallback')

    return {
        'version': 'learned_policy_migration_v1',
        'normalized_action': _build_normalized_action(
            action=recommendation.get('action'),
            confidence=recommendation.get('confidence'),
            power_kw=recommendation.get('action_kw', recommendation.get('power_kw')),
            base_action=recommendation.get('base_action', recommendation.get('action')),
        ),
        'provenance': {
            'decision_source': str(recommendation.get('decision_source') or 'python_rule_engine'),
            'fallback_reason_code': str(recommendation.get('fallback_reason_code') or 'none'),
            'fallback_used': str(recommendation.get('fallback_reason_code') or 'none') != 'none',
            'state_source': state_source,
            'state_source_detail': battery_signal.get('source_detail'),
            'telemetry_classification': 'simulated_operational_telemetry' if state_source == 'simulator_backed_telemetry' else 'fabricated_training_scaffolding',
        },
        'strategy_context': {
            'optimization_strategy': getattr(user_config, 'optimization_strategy', 'balanced'),
            'load_profile_type': getattr(user_config, 'load_profile_type', 'standard'),
            'strategy_source': 'tenant_config',
        },
    }


def get_recommendation(enhanced: bool = False) -> Dict[str, Any]:
    """Get current ML recommendation using Pipeline Orchestrator."""
    try:
        live_context = _load_live_context()
        # Load user configuration
        user_config = load_user_config()

        # Initialize Pipeline Orchestrator
        orchestrator = PipelineOrchestrator(user_config)
        if hasattr(orchestrator, 'set_live_context'):
            orchestrator.set_live_context(live_context)

        serving_mode = _normalize_serving_mode(os.getenv('ENERGY_ML_SERVING_MODE'))
        serving = {
            'requested_mode': serving_mode,
            'active_mode': INCUMBENT_SERVING_MODE,
            'adapter': 'PredictionService',
            'fallback_used': False,
            'fallback_reason_code': 'none',
            'model_info': None,
        }

        learned_policy_recommendation: Optional[Dict[str, Any]] = None
        if serving_mode == LEARNED_POLICY_SERVING_MODE:
            learned_policy_recommendation, model_info = _get_learned_policy_recommendation(
                orchestrator,
                user_config,
                live_context,
            )
            serving['model_info'] = model_info

        if learned_policy_recommendation is not None:
            current_recommendation = learned_policy_recommendation
            serving['active_mode'] = LEARNED_POLICY_SERVING_MODE
        else:
            current_recommendation = _label_recommendation_origin(
                orchestrator.calculate_recommendation(),
                decision_source='python_rule_engine',
                fallback_reason_code=(
                    serving['model_info'].get('availability_error')
                    if isinstance(serving.get('model_info'), dict)
                    else 'none'
                ) or 'none',
            )

            if enhanced:
                try:
                    optimization_engine = OptimizationEngine()
                    user_preferences = optimization_engine.get_user_strategy(user_config)
                    optimized_recommendation = optimization_engine.optimize_decision(
                        current_recommendation,
                        user_config.optimization_strategy,
                        weights=user_preferences.get("weights", {}),
                    )

                    physics_engine = BatteryPhysicsEngine()
                    physics_data = physics_engine.simulate_battery_behavior(user_config)
                    physics_constrained = physics_engine.apply_physics_constraints(
                        optimized_recommendation,
                        {
                            "physics_constraints": physics_data.get(
                                "physics_constraints", {}
                            ),
                            "current_state": physics_data.get("current_state", {}),
                            "power_limits": physics_data.get("power_limits", {}),
                            "status": "success",
                        },
                    )

                    renewable_forecaster = RenewableForecaster()
                    renewable_data = renewable_forecaster.generate_forecasts(user_config)
                    current_recommendation = renewable_forecaster.integrate_with_prediction(
                        physics_constrained,
                        renewable_data,
                    )

                except Exception as e:
                    logger.warning(f"Enhanced recommendation failed, using base: {e}")

            if serving_mode == LEARNED_POLICY_SERVING_MODE:
                serving['fallback_used'] = True
                serving['fallback_reason_code'] = current_recommendation['fallback_reason_code']

        # Get 24-hour forecast
        forecast_df = orchestrator.get_hourly_forecast(24)

        # Convert forecast to list of dicts
        hourly_forecast = []
        for row in forecast_df.iter_rows(named=True):
            hourly_forecast.append(
                {
                    "hour": row["hour"],
                    "action": row["action"],
                    "confidence": row["confidence"],
                    "reasoning": row["reasoning"],
                    "savings_estimate": row["savings_estimate"],
                    "battery_impact": row["battery_impact"],
                }
            )

        # Get pipeline status for additional context
        status = orchestrator.get_status()

        # Calculate extended savings estimates
        hourly_savings = current_recommendation.get("estimated_savings", 0)
        daily_savings = sum(row["savings_estimate"] for row in hourly_forecast)
        contract = _build_recommendation_contract(user_config, live_context, current_recommendation)

        # Prepare response
        response = {
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
            "normalized_action": contract["normalized_action"],
            "provenance": contract["provenance"],
            "contract": contract,
            "serving": serving,
            "pipeline_status": status,
            "timestamp": datetime.now().isoformat(),
        }

        return response

    except Exception as e:
        logging.error(f"Error getting ML recommendation: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def get_forecast(hours: int = 24) -> Dict[str, Any]:
    """Get hourly forecast for specified number of hours."""
    try:
        user_config = load_user_config()
        orchestrator = PipelineOrchestrator(user_config)

        forecast_df = orchestrator.get_hourly_forecast(hours)

        # Convert to list of dicts
        forecast = []
        for row in forecast_df.iter_rows(named=True):
            forecast.append(
                {
                    "hour": row["hour"],
                    "action": row["action"],
                    "confidence": row["confidence"],
                    "reasoning": row["reasoning"],
                    "savings_estimate": row["savings_estimate"],
                    "battery_impact": row["battery_impact"],
                }
            )

        return {
            "success": True,
            "forecast": forecast,
            "hours": hours,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logging.error(f"Error getting forecast: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def get_pipeline_status() -> Dict[str, Any]:
    """Get current pipeline status."""
    try:
        user_config = load_user_config()
        orchestrator = PipelineOrchestrator(user_config)

        status = orchestrator.get_status()

        return {
            "success": True,
            "status": status,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logging.error(f"Error getting pipeline status: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def set_optimization_strategy(
    strategy: str, custom_weights: Dict[str, float] = None
) -> Dict[str, Any]:
    """Set user optimization strategy."""
    try:
        config_manager = ConfigurationManager()
        user_config = config_manager.load_config_or_raise()

        # Update optimization strategy in user config
        user_config.optimization_strategy = strategy
        if custom_weights:
            user_config.custom_optimization_weights = custom_weights

        # Save updated config
        save_result = config_manager.save_config(user_config)
        if not save_result.success:
            raise RuntimeError('; '.join(save_result.errors) or 'Failed to save user configuration')

        # Get strategy details
        optimization_engine = OptimizationEngine()
        strategy_info = optimization_engine.get_strategy_info(strategy)

        return {
            "success": True,
            "strategy": strategy,
            "description": strategy_info.get("description", f"Strategy: {strategy}"),
            "weights": strategy_info.get("weights", {}),
            "constraints": strategy_info.get("constraints", {}),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logging.error(f"Error setting optimization strategy: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def get_optimization_strategy() -> Dict[str, Any]:
    """Get current optimization strategy."""
    try:
        user_config = load_user_config()

        optimization_engine = OptimizationEngine()
        strategy_info = optimization_engine.get_strategy_info(
            user_config.optimization_strategy
        )

        return {
            "success": True,
            "strategy": user_config.optimization_strategy,
            "description": strategy_info.get("description", ""),
            "weights": strategy_info.get("weights", {}),
            "constraints": strategy_info.get("constraints", {}),
            "available_strategies": strategy_info.get("available_strategies", []),
            "current_cycles": strategy_info.get("current_cycles", 0),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logging.error(f"Error getting optimization strategy: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def get_battery_physics() -> Dict[str, Any]:
    """Get battery physics simulation data."""
    try:
        user_config = load_user_config()

        physics_engine = BatteryPhysicsEngine()
        physics_data = physics_engine.simulate_battery_behavior(user_config)

        return {
            "success": True,
            "physics_data": physics_data,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logging.error(f"Error getting battery physics: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def get_renewable_forecast() -> Dict[str, Any]:
    """Get renewable energy forecast data."""
    try:
        user_config = load_user_config()

        renewable_forecaster = RenewableForecaster()
        forecast_data = renewable_forecaster.generate_forecasts(user_config)

        return {
            "success": True,
            "forecast_data": forecast_data,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logging.error(f"Error getting renewable forecast: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def main():
    """Main entry point for CLI interface."""
    setup_logging()

    parser = argparse.ArgumentParser(description="ML Integration API Bridge")
    parser.add_argument(
        "--action",
        choices=[
            "get_recommendation",
            "get_forecast",
            "get_status",
            "set_optimization_strategy",
            "get_optimization_strategy",
            "get_battery_physics",
            "get_renewable_forecast",
        ],
        default="get_recommendation",
        help="Action to perform",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Number of hours for forecast (default: 24)",
    )
    parser.add_argument(
        "--format", choices=["json", "pretty"], default="json", help="Output format"
    )
    parser.add_argument(
        "--strategy",
        type=str,
        help="Optimization strategy (for set_optimization_strategy)",
    )
    parser.add_argument(
        "--custom_weights", type=str, help="Custom optimization weights as JSON string"
    )
    parser.add_argument(
        "--enhanced",
        type=bool,
        default=False,
        help="Use enhanced recommendation with optimization and physics",
    )

    args = parser.parse_args()

    # Execute the requested action
    if args.action == "get_recommendation":
        result = get_recommendation(enhanced=args.enhanced)
    elif args.action == "get_forecast":
        result = get_forecast(args.hours)
    elif args.action == "get_status":
        result = get_pipeline_status()
    elif args.action == "set_optimization_strategy":
        if not args.strategy:
            result = {
                "success": False,
                "error": "Strategy is required for set_optimization_strategy",
            }
        else:
            custom_weights = None
            if args.custom_weights:
                try:
                    custom_weights = json.loads(args.custom_weights)
                except json.JSONDecodeError:
                    result = {
                        "success": False,
                        "error": "Invalid JSON for custom_weights",
                    }
                    return result
            result = set_optimization_strategy(args.strategy, custom_weights)
    elif args.action == "get_optimization_strategy":
        result = get_optimization_strategy()
    elif args.action == "get_battery_physics":
        result = get_battery_physics()
    elif args.action == "get_renewable_forecast":
        result = get_renewable_forecast()
    else:
        result = {"success": False, "error": f"Unknown action: {args.action}"}

    # Output result
    if args.format == "pretty":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))

    # Exit with error code if operation failed
    sys.exit(0 if result.get("success", False) else 1)


if __name__ == "__main__":
    main()

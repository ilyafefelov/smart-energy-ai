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
from typing import Dict, Any

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from energy_ml.pipeline import PipelineOrchestrator
    from energy_ml.user_config import ConfigurationManager
    from energy_ml.mlops.optimization_engine import OptimizationEngine
    from energy_ml.mlops.battery_physics import BatteryPhysicsEngine
    from energy_ml.mlops.renewable_forecasting import RenewableForecaster
except ImportError:
    # Fallback: try direct imports from the energy_ml directory
    sys.path.insert(0, str(Path(__file__).parent / "energy_ml"))
    from pipeline import PipelineOrchestrator
    from user_config import ConfigurationManager


logger = logging.getLogger(__name__)


def _load_user_config() -> Any:
    config_manager = ConfigurationManager()
    return config_manager.load_config_or_raise()


def _save_user_config(user_config: Any) -> None:
    config_manager = ConfigurationManager()
    result = config_manager.save_config(user_config)
    if not result.success:
        error_text = '; '.join(result.errors) if result.errors else 'Configuration could not be saved'
        raise RuntimeError(error_text)


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
        if numeric != numeric:  # NaN guard
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


def _extract_hourly_price_map(live_context: Dict[str, Any]) -> Dict[int, float]:
    result: Dict[int, float] = {}
    rows = (live_context.get('price_signal') or {}).get('forecast_next24h') or []
    if not isinstance(rows, list):
        return result

    for row in rows:
        if not isinstance(row, dict):
            continue
        hour = row.get('hour')
        price = row.get('price')
        try:
            hour_int = int(hour)
        except Exception:
            continue
        if hour_int < 0 or hour_int > 23:
            continue
        price_float = _safe_float(price, default=-1)
        if price_float <= 0:
            continue
        result[hour_int] = price_float

    return result


def _apply_live_price_signal(
    recommendation: Dict[str, Any],
    status: Dict[str, Any],
    live_context: Dict[str, Any],
) -> Dict[str, Any]:
    adjusted = recommendation.copy()
    price_map = _extract_hourly_price_map(live_context)
    current_hour = datetime.now().hour
    current_price = _safe_float((live_context.get('price_signal') or {}).get('current_uah_kwh'), default=0.0)
    if current_price <= 0:
        current_price = _safe_float(price_map.get(current_hour), default=0.0)

    prices = sorted(price_map.values())
    if current_price <= 0 or len(prices) < 8:
        adjusted['live_signal_applied'] = False
        return adjusted

    p25 = prices[max(0, int(len(prices) * 0.25) - 1)]
    p75 = prices[min(len(prices) - 1, int(len(prices) * 0.75))]

    battery_soc = _safe_float((status.get('battery_state') or {}).get('soc_percent'), default=50.0)
    action = str(adjusted.get('action', 'HOLD')).upper()
    confidence = _safe_float(adjusted.get('confidence'), default=0.5)
    reasoning = str(adjusted.get('reasoning', '')).strip()

    updated = False
    if current_price <= p25 and battery_soc < 85 and action in {'HOLD', 'SELL'}:
        action = 'BUY'
        confidence = min(0.99, confidence + 0.06)
        reasoning = f"{reasoning} Live price ({current_price:.2f} UAH/kWh) is in lower quartile ({p25:.2f}); opportunistic charging favored.".strip()
        updated = True
    elif current_price >= p75 and battery_soc > 35 and action in {'HOLD', 'BUY'}:
        action = 'SELL'
        confidence = min(0.99, confidence + 0.06)
        reasoning = f"{reasoning} Live price ({current_price:.2f} UAH/kWh) is in upper quartile ({p75:.2f}); discharging/export favored.".strip()
        updated = True

    adjusted.update({
        'action': action,
        'confidence': confidence,
        'reasoning': reasoning,
        'live_signal_applied': updated,
        'live_price_context': {
            'current_price_uah_kwh': current_price,
            'q25_price_uah_kwh': p25,
            'q75_price_uah_kwh': p75,
            'battery_soc_percent': battery_soc,
        },
    })
    return adjusted


def _build_model_inputs(user_config: Any, live_context: Dict[str, Any]) -> Dict[str, Any]:
    price_signal = live_context.get('price_signal') or {}
    weather_signal = live_context.get('weather_signal') or {}
    battery_signal = live_context.get('battery_signal') or {}
    return {
        'optimization_strategy': getattr(user_config, 'optimization_strategy', 'balanced'),
        'load_profile_type': getattr(user_config, 'load_profile_type', 'standard'),
        'battery': {
            'type': getattr(user_config, 'battery_type', 'LFP'),
            'capacity_kwh': getattr(user_config, 'battery_capacity_kwh', 0),
            'efficiency': getattr(user_config, 'battery_efficiency', 0),
            'soc_min': getattr(user_config, 'battery_soc_min', None),
            'soc_max': getattr(user_config, 'battery_soc_max', None),
        },
        'generation': {
            'solar_capacity_kw': getattr(user_config, 'solar_capacity_kw', 0),
            'wind_capacity_kw': getattr(user_config, 'wind_capacity_kw', 0),
            'solar_efficiency': getattr(user_config, 'solar_efficiency', None),
            'wind_efficiency': getattr(user_config, 'wind_efficiency', None),
        },
        'location': {
            'latitude': getattr(user_config, 'latitude', None),
            'longitude': getattr(user_config, 'longitude', None),
            'timezone': getattr(user_config, 'timezone', None),
        },
        'live_price_uah_kwh': price_signal.get('current_uah_kwh'),
        'live_weather': weather_signal.get('current'),
        'live_battery_state': {
            'soc_percent': battery_signal.get('soc_percent', battery_signal.get('soc')),
            'health_percent': battery_signal.get('health_percent', battery_signal.get('health')),
            'cycles_remaining': battery_signal.get('cycles_remaining'),
        },
    }


def get_recommendation(enhanced: bool = False) -> Dict[str, Any]:
    """Get current ML recommendation using Pipeline Orchestrator."""
    try:
        live_context = _load_live_context()

        # Load user configuration
        user_config = _load_user_config()
        
        # Initialize Pipeline Orchestrator
        orchestrator = PipelineOrchestrator(user_config)
        if hasattr(orchestrator, 'set_live_context'):
            orchestrator.set_live_context(live_context)
        
        # Get current recommendation
        current_recommendation = orchestrator.calculate_recommendation()
        
        # If enhanced mode, apply optimization and physics
        if enhanced:
            try:
                # Apply optimization engine
                optimization_engine = OptimizationEngine()
                user_preferences = optimization_engine.get_user_strategy(user_config)
                optimized_recommendation = optimization_engine.optimize_decision(
                    current_recommendation,
                    user_config.optimization_strategy,
                    weights=user_preferences.get('weights', {})
                )
                
                # Apply physics constraints
                physics_engine = BatteryPhysicsEngine()
                physics_data = physics_engine.simulate_battery_behavior(user_config)
                physics_constrained = physics_engine.apply_physics_constraints(
                    optimized_recommendation, 
                    {'physics_constraints': physics_data.get('physics_constraints', {}),
                     'current_state': physics_data.get('current_state', {}),
                     'power_limits': physics_data.get('power_limits', {}),
                     'status': 'success'}
                )
                
                # Apply renewable integration
                renewable_forecaster = RenewableForecaster()
                renewable_data = renewable_forecaster.generate_forecasts(user_config)
                final_recommendation = renewable_forecaster.integrate_with_prediction(
                    physics_constrained, renewable_data
                )
                
                current_recommendation = final_recommendation
                
            except Exception as e:
                logger.warning(f"Enhanced recommendation failed, using base: {e}")
        
        # Get pipeline status and apply live price context to the immediate decision.
        status = orchestrator.get_status()
        current_recommendation = _apply_live_price_signal(current_recommendation, status, live_context)

        # Get 24-hour forecast
        forecast_df = orchestrator.get_hourly_forecast(24)
        hourly_price_map = _extract_hourly_price_map(live_context)
        
        # Convert forecast to list of dicts
        hourly_forecast = []
        for row in forecast_df.iter_rows(named=True):
            hourly_forecast.append({
                'hour': row['hour'],
                'action': row['action'],
                'confidence': row['confidence'],
                'reasoning': row['reasoning'],
                'savings_estimate': row['savings_estimate'],
                'battery_impact': row['battery_impact'],
                'price_uah_kwh': hourly_price_map.get(int(row['hour'])),
                'price_uah_mwh': (
                    hourly_price_map.get(int(row['hour'])) * 1000
                    if hourly_price_map.get(int(row['hour'])) is not None
                    else None
                ),
            })
        
        # Calculate extended savings estimates
        hourly_savings = current_recommendation.get('estimated_savings', 0)
        daily_savings = sum(row['savings_estimate'] for row in hourly_forecast)
        
        # Prepare response
        response = {
            'success': True,
            'action': current_recommendation['action'],
            'confidence': current_recommendation['confidence'],
            'reasoning': current_recommendation['reasoning'],
            'estimated_savings': hourly_savings,
            'hourly_forecast': hourly_forecast,
            'daily_savings_estimate': daily_savings,
            'monthly_savings_estimate': daily_savings * 30,
            'annual_savings_estimate': daily_savings * 365,
            'battery_impact': {
                'current_soc': status['battery_state']['soc_percent'],
                'health_loss': current_recommendation.get('battery_impact', 0),
                'cycles_remaining': status['battery_state']['cycles_remaining']
            },
            'feature_provenance': {
                'tenant_id': live_context.get('tenant_id'),
                'captured_at': live_context.get('captured_at'),
                'sources': {
                    'profile': 'tenant_user_config',
                    'prices': (live_context.get('price_signal') or {}).get('source', 'pipeline_default_tariff'),
                    'weather': (live_context.get('weather_signal') or {}).get('source', 'pipeline_internal_weather_model'),
                },
                'used_live_price_signal': bool(current_recommendation.get('live_signal_applied')),
                'used_live_weather_signal': bool((live_context.get('weather_signal') or {}).get('current')),
                'feature_count_estimate': 18,
            },
            'model_inputs': _build_model_inputs(user_config, live_context),
            'pipeline_status': status,
            'timestamp': datetime.now().isoformat()
        }
        
        return response
        
    except Exception as e:
        logging.error(f"Error getting ML recommendation: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def get_forecast(hours: int = 24) -> Dict[str, Any]:
    """Get hourly forecast for specified number of hours."""
    try:
        user_config = _load_user_config()
        orchestrator = PipelineOrchestrator(user_config)
        
        forecast_df = orchestrator.get_hourly_forecast(hours)
        
        # Convert to list of dicts
        forecast = []
        for row in forecast_df.iter_rows(named=True):
            forecast.append({
                'hour': row['hour'],
                'action': row['action'],
                'confidence': row['confidence'],
                'reasoning': row['reasoning'],
                'savings_estimate': row['savings_estimate'],
                'battery_impact': row['battery_impact']
            })
        
        return {
            'success': True,
            'forecast': forecast,
            'hours': hours,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error getting forecast: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def get_pipeline_status() -> Dict[str, Any]:
    """Get current pipeline status."""
    try:
        user_config = _load_user_config()
        orchestrator = PipelineOrchestrator(user_config)
        
        status = orchestrator.get_status()
        
        return {
            'success': True,
            'status': status,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error getting pipeline status: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def set_optimization_strategy(strategy: str, custom_weights: Dict[str, float] = None) -> Dict[str, Any]:
    """Set user optimization strategy."""
    try:
        user_config = _load_user_config()
        
        # Update optimization strategy in user config
        user_config.optimization_strategy = strategy
        if custom_weights:
            user_config.custom_optimization_weights = custom_weights
        
        # Save updated config
        _save_user_config(user_config)
        
        # Get strategy details
        optimization_engine = OptimizationEngine()
        strategy_info = optimization_engine.get_strategy_info(strategy)
        
        return {
            'success': True,
            'strategy': strategy,
            'description': strategy_info.get('description', f'Strategy: {strategy}'),
            'weights': strategy_info.get('weights', {}),
            'constraints': strategy_info.get('constraints', {}),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error setting optimization strategy: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def get_optimization_strategy() -> Dict[str, Any]:
    """Get current optimization strategy."""
    try:
        user_config = _load_user_config()
        
        optimization_engine = OptimizationEngine()
        strategy_info = optimization_engine.get_strategy_info(user_config.optimization_strategy)
        
        return {
            'success': True,
            'strategy': user_config.optimization_strategy,
            'description': strategy_info.get('description', ''),
            'weights': strategy_info.get('weights', {}),
            'constraints': strategy_info.get('constraints', {}),
            'available_strategies': strategy_info.get('available_strategies', []),
            'current_cycles': strategy_info.get('current_cycles', 0),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error getting optimization strategy: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def get_battery_physics() -> Dict[str, Any]:
    """Get battery physics simulation data."""
    try:
        user_config = _load_user_config()
        
        physics_engine = BatteryPhysicsEngine()
        physics_data = physics_engine.simulate_battery_behavior(user_config)
        
        return {
            'success': True,
            'physics_data': physics_data,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error getting battery physics: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def get_renewable_forecast() -> Dict[str, Any]:
    """Get renewable energy forecast data."""
    try:
        user_config = _load_user_config()
        
        renewable_forecaster = RenewableForecaster()
        forecast_data = renewable_forecaster.generate_forecasts(user_config)
        
        return {
            'success': True,
            'forecast_data': forecast_data,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error getting renewable forecast: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def main():
    """Main entry point for CLI interface."""
    setup_logging()
    
    parser = argparse.ArgumentParser(description='ML Integration API Bridge')
    parser.add_argument('--action', 
                       choices=['get_recommendation', 'get_forecast', 'get_status',
                               'set_optimization_strategy', 'get_optimization_strategy',
                               'get_battery_physics', 'get_renewable_forecast'],
                       default='get_recommendation',
                       help='Action to perform')
    parser.add_argument('--hours', type=int, default=24,
                       help='Number of hours for forecast (default: 24)')
    parser.add_argument('--format', choices=['json', 'pretty'], default='json',
                       help='Output format')
    parser.add_argument('--strategy', type=str, 
                       help='Optimization strategy (for set_optimization_strategy)')
    parser.add_argument('--custom_weights', type=str,
                       help='Custom optimization weights as JSON string')
    parser.add_argument('--enhanced', type=bool, default=False,
                       help='Use enhanced recommendation with optimization and physics')
    
    args = parser.parse_args()
    
    # Execute the requested action
    if args.action == 'get_recommendation':
        result = get_recommendation(enhanced=args.enhanced)
    elif args.action == 'get_forecast':
        result = get_forecast(args.hours)
    elif args.action == 'get_status':
        result = get_pipeline_status()
    elif args.action == 'set_optimization_strategy':
        if not args.strategy:
            result = {'success': False, 'error': 'Strategy is required for set_optimization_strategy'}
        else:
            custom_weights = None
            if args.custom_weights:
                try:
                    custom_weights = json.loads(args.custom_weights)
                except json.JSONDecodeError:
                    result = {'success': False, 'error': 'Invalid JSON for custom_weights'}
                    return result
            result = set_optimization_strategy(args.strategy, custom_weights)
    elif args.action == 'get_optimization_strategy':
        result = get_optimization_strategy()
    elif args.action == 'get_battery_physics':
        result = get_battery_physics()
    elif args.action == 'get_renewable_forecast':
        result = get_renewable_forecast()
    else:
        result = {'success': False, 'error': f'Unknown action: {args.action}'}
    
    # Output result
    if args.format == 'pretty':
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))
    
    # Exit with error code if operation failed
    sys.exit(0 if result.get('success', False) else 1)


if __name__ == '__main__':
    main()
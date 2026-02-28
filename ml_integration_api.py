#!/usr/bin/env python3
"""
ML Integration API Bridge for Dashboard
Provides a command-line interface to the Phase 4F ML Pipeline
"""
import sys
import json
import logging
import argparse
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


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def get_recommendation(enhanced: bool = False) -> Dict[str, Any]:
    """Get current ML recommendation using Pipeline Orchestrator."""
    try:
        # Load user configuration
        config_manager = ConfigurationManager()
        user_config = config_manager.load_config()
        
        # Initialize Pipeline Orchestrator
        orchestrator = PipelineOrchestrator(user_config)
        
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
        
        # Get 24-hour forecast
        forecast_df = orchestrator.get_hourly_forecast(24)
        
        # Convert forecast to list of dicts
        hourly_forecast = []
        for row in forecast_df.iter_rows(named=True):
            hourly_forecast.append({
                'hour': row['hour'],
                'action': row['action'],
                'confidence': row['confidence'],
                'reasoning': row['reasoning'],
                'savings_estimate': row['savings_estimate'],
                'battery_impact': row['battery_impact']
            })
        
        # Get pipeline status for additional context
        status = orchestrator.get_status()
        
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
        config_manager = ConfigurationManager()
        user_config = config_manager.load_config()
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
        config_manager = ConfigurationManager()
        user_config = config_manager.load_config()
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
        config_manager = ConfigurationManager()
        user_config = config_manager.load_config()
        
        # Update optimization strategy in user config
        user_config.optimization_strategy = strategy
        if custom_weights:
            user_config.custom_optimization_weights = custom_weights
        
        # Save updated config
        config_manager.save_config(user_config)
        
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
        config_manager = ConfigurationManager()
        user_config = config_manager.load_config()
        
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
        config_manager = ConfigurationManager()
        user_config = config_manager.load_config()
        
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
        config_manager = ConfigurationManager()
        user_config = config_manager.load_config()
        
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
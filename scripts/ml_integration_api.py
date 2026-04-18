#!/usr/bin/env python3
"""
ML Integration API Bridge for Dashboard

CLI and compatibility adapter for the canonical bridge owner in ``src/``.
"""
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Callable, Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Add the project root to Python path
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_pipeline.ml_bridge_service import (
    INCUMBENT_SERVING_MODE,
    LEARNED_POLICY_SERVING_MODE,
    _load_user_config,
    _save_user_config,
    get_battery_physics,
    get_forecast,
    get_optimization_strategy,
    get_pipeline_status,
    get_recommendation,
    get_renewable_forecast,
    set_optimization_strategy,
)


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def _build_cli_parser() -> argparse.ArgumentParser:
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
    return parser


def _parse_custom_weights(raw_custom_weights: Optional[str]) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    if not raw_custom_weights:
        return None, None

    try:
        parsed_weights = json.loads(raw_custom_weights)
    except json.JSONDecodeError:
        return None, {'success': False, 'error': 'Invalid JSON for custom_weights'}

    return parsed_weights, None


def _run_get_recommendation_action(args: argparse.Namespace) -> Dict[str, Any]:
    return get_recommendation(enhanced=args.enhanced)


def _run_get_forecast_action(args: argparse.Namespace) -> Dict[str, Any]:
    return get_forecast(args.hours)


def _run_get_status_action(_args: argparse.Namespace) -> Dict[str, Any]:
    return get_pipeline_status()


def _run_set_optimization_strategy_action(args: argparse.Namespace) -> Dict[str, Any]:
    if not args.strategy:
        return {'success': False, 'error': 'Strategy is required for set_optimization_strategy'}

    custom_weights, error_result = _parse_custom_weights(args.custom_weights)
    if error_result is not None:
        return error_result

    return set_optimization_strategy(args.strategy, custom_weights)


def _run_get_optimization_strategy_action(_args: argparse.Namespace) -> Dict[str, Any]:
    return get_optimization_strategy()


def _run_get_battery_physics_action(_args: argparse.Namespace) -> Dict[str, Any]:
    return get_battery_physics()


def _run_get_renewable_forecast_action(_args: argparse.Namespace) -> Dict[str, Any]:
    return get_renewable_forecast()


CLI_ACTION_HANDLERS: dict[str, Callable[[argparse.Namespace], Dict[str, Any]]] = {
    'get_recommendation': _run_get_recommendation_action,
    'get_forecast': _run_get_forecast_action,
    'get_status': _run_get_status_action,
    'set_optimization_strategy': _run_set_optimization_strategy_action,
    'get_optimization_strategy': _run_get_optimization_strategy_action,
    'get_battery_physics': _run_get_battery_physics_action,
    'get_renewable_forecast': _run_get_renewable_forecast_action,
}


def _run_cli_action(args: argparse.Namespace) -> Dict[str, Any]:
    handler = CLI_ACTION_HANDLERS.get(args.action)
    if handler is None:
        return {'success': False, 'error': f'Unknown action: {args.action}'}
    return handler(args)


def main():
    """Main entry point for CLI interface."""
    setup_logging()
    args = _build_cli_parser().parse_args()
    result = _run_cli_action(args)
    
    # Output result
    if args.format == 'pretty':
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))
    
    # Exit with error code if operation failed
    sys.exit(0 if result.get('success', False) else 1)


if __name__ == '__main__':
    main()
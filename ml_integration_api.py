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


def get_recommendation() -> Dict[str, Any]:
    """Get current ML recommendation using Pipeline Orchestrator."""
    try:
        # Load user configuration
        config_manager = ConfigurationManager()
        user_config = config_manager.load_config()
        
        # Initialize Pipeline Orchestrator
        orchestrator = PipelineOrchestrator(user_config)
        
        # Get current recommendation
        current_recommendation = orchestrator.calculate_recommendation()
        
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


def main():
    """Main entry point for CLI interface."""
    setup_logging()
    
    parser = argparse.ArgumentParser(description='ML Integration API Bridge')
    parser.add_argument('--action', 
                       choices=['get_recommendation', 'get_forecast', 'get_status'],
                       default='get_recommendation',
                       help='Action to perform')
    parser.add_argument('--hours', type=int, default=24,
                       help='Number of hours for forecast (default: 24)')
    parser.add_argument('--format', choices=['json', 'pretty'], default='json',
                       help='Output format')
    
    args = parser.parse_args()
    
    # Execute the requested action
    if args.action == 'get_recommendation':
        result = get_recommendation()
    elif args.action == 'get_forecast':
        result = get_forecast(args.hours)
    elif args.action == 'get_status':
        result = get_pipeline_status()
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
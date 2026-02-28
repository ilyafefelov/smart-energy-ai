#!/usr/bin/env python3
"""
Control System Status Script
Called by dashboard API to get current system status
"""

import sys
import json
from pathlib import Path

# Add energy_ml to path
sys.path.append(str(Path(__file__).parent.parent))

try:
    from control.inverter_controller import get_controller
    
    def main():
        """Get current control system status"""
        try:
            controller = get_controller()
            status = controller.get_status()
            
            # Add additional metadata
            result = {
                **status,
                'physics_enabled': True,
                'connection_status': 'connected',
                'last_command_time': controller.last_command_time.isoformat() if controller.last_command_time else None,
                'system_health': 'good'
            }
            
            print(json.dumps(result, indent=2))
            return 0
            
        except Exception as e:
            error_result = {
                'error': str(e),
                'soc': 50,
                'power_kw': 0,
                'mode': 'automatic',
                'active_command': None,
                'battery_capacity_kwh': 10.0,
                'max_power_kw': 5.0,
                'physics_enabled': False,
                'connection_status': 'error',
                'system_health': 'error'
            }
            print(json.dumps(error_result, indent=2))
            return 1
    
    if __name__ == "__main__":
        sys.exit(main())
        
except ImportError as e:
    # Fallback if control system not available
    fallback_status = {
        'error': f'Control system not available: {e}',
        'soc': 50,
        'power_kw': 0,
        'mode': 'automatic', 
        'active_command': None,
        'battery_capacity_kwh': 10.0,
        'max_power_kw': 5.0,
        'physics_enabled': False,
        'connection_status': 'unavailable',
        'system_health': 'offline'
    }
    print(json.dumps(fallback_status, indent=2))
    sys.exit(1)
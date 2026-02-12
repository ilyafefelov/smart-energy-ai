#!/usr/bin/env python3
"""
Control Command Execution Script
Called by dashboard API to execute battery control commands
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import asyncio

# Add energy_ml to path
sys.path.append(str(Path(__file__).parent.parent))

try:
    from control.inverter_controller import get_controller, ControlCommand, ControlAction
    
    def main():
        """Execute control command"""
        parser = argparse.ArgumentParser(description='Execute battery control command')
        parser.add_argument('--command', required=True, choices=['charge', 'discharge', 'hold', 'auto'],
                          help='Command to execute')
        parser.add_argument('--power', type=float, default=0.0,
                          help='Power in kW (positive=charge, negative=discharge)')
        parser.add_argument('--duration', type=int, default=None,
                          help='Duration in minutes')
        parser.add_argument('--reason', default='API command',
                          help='Reason for command')
        parser.add_argument('--user-id', default='api',
                          help='User ID executing command')
        
        args = parser.parse_args()
        
        try:
            controller = get_controller()
            
            # Create control action
            action = ControlAction(
                command=ControlCommand(args.command),
                power_kw=args.power,
                duration_minutes=args.duration,
                reason=args.reason,
                user_id=args.user_id,
                timestamp=datetime.now()
            )
            
            # Execute command
            result = asyncio.run(controller.execute_command(action))
            
            # Add success metadata
            result.update({
                'executed_at': datetime.now().isoformat(),
                'command_details': {
                    'command': args.command,
                    'power_kw': args.power,
                    'reason': args.reason,
                    'user_id': args.user_id
                }
            })
            
            print(json.dumps(result, indent=2))
            return 0
            
        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e),
                'executed_at': datetime.now().isoformat(),
                'command_details': {
                    'command': args.command,
                    'power_kw': args.power,
                    'reason': args.reason
                }
            }
            print(json.dumps(error_result, indent=2))
            return 1
    
    if __name__ == "__main__":
        sys.exit(main())
        
except ImportError as e:
    # Fallback if control system not available
    error_result = {
        'success': False,
        'error': f'Control system not available: {e}',
        'executed_at': datetime.now().isoformat()
    }
    print(json.dumps(error_result, indent=2))
    sys.exit(1)
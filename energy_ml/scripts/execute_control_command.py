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

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

def _emit(payload):
    print(json.dumps(payload, indent=2))


def _executed_at() -> str:
    return datetime.now().isoformat()


def _parse_args():
    parser = argparse.ArgumentParser(description="Execute battery control command")
    parser.add_argument("--command", required=True, choices=["charge", "discharge", "hold", "auto"], help="Command to execute")
    parser.add_argument("--power", type=float, default=0.0, help="Power in kW (positive=charge, negative=discharge)")
    parser.add_argument("--duration", type=int, default=None, help="Duration in minutes")
    parser.add_argument("--reason", default="API command", help="Reason for command")
    parser.add_argument("--user-id", default="api", help="User ID executing command")
    return parser.parse_args()


def _load_control_runtime():
    from control.inverter_controller import get_controller, ControlCommand, ControlAction

    return get_controller, ControlCommand, ControlAction


def _build_command_details(args, include_user_id=True):
    details = {
        "command": args.command,
        "power_kw": args.power,
        "reason": args.reason,
    }
    if include_user_id:
        details["user_id"] = args.user_id
    return details


def main():
    """Execute control command."""
    args = _parse_args()

    try:
        get_controller, ControlCommand, ControlAction = _load_control_runtime()
    except ImportError as error:
        _emit(
            {
                "success": False,
                "error": f"Control system not available: {error}",
                "executed_at": _executed_at(),
            }
        )
        return 1

    try:
        controller = get_controller()
        action = ControlAction(
            command=ControlCommand(args.command),
            power_kw=args.power,
            duration_minutes=args.duration,
            reason=args.reason,
            user_id=args.user_id,
            timestamp=datetime.now(),
        )
        result = asyncio.run(controller.execute_command(action))
        result.update(
            {
                "executed_at": _executed_at(),
                "command_details": _build_command_details(args),
            }
        )
        _emit(result)
        return 0
    except Exception as error:
        _emit(
            {
                "success": False,
                "error": str(error),
                "executed_at": _executed_at(),
                "command_details": _build_command_details(args, include_user_id=False),
            }
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
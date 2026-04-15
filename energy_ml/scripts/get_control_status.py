#!/usr/bin/env python3
"""
Control System Status Script
Called by dashboard API to get current system status
"""

import sys
import json
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

def _emit(payload):
    print(json.dumps(payload, indent=2))


def _default_status(error_message, connection_status, system_health):
    return {
        "error": error_message,
        "soc": 50,
        "power_kw": 0,
        "mode": "automatic",
        "active_command": None,
        "battery_capacity_kwh": 10.0,
        "max_power_kw": 5.0,
        "physics_enabled": False,
        "connection_status": connection_status,
        "system_health": system_health,
    }


def _load_control_runtime():
    from control.inverter_controller import get_controller

    return get_controller


def main():
    """Get current control system status."""
    try:
        get_controller = _load_control_runtime()
    except ImportError as error:
        _emit(_default_status(f"Control system not available: {error}", "unavailable", "offline"))
        return 1

    try:
        controller = get_controller()
        status = controller.get_status()
        result = {
            **status,
            "physics_enabled": True,
            "connection_status": "connected",
            "last_command_time": controller.last_command_time.isoformat() if controller.last_command_time else None,
            "system_health": "good",
        }
        _emit(result)
        return 0
    except Exception as error:
        _emit(_default_status(str(error), "error", "error"))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
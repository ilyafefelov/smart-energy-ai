#!/usr/bin/env python3
"""
Battery Physics Status Script
Returns current battery physics simulation state as JSON
"""

import json
import sys
import random
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from scripts.get_battery_physics_support import (
    build_actual_payload,
    build_error_payload,
    build_mock_payload,
)


DEFAULT_CAPACITY_KWH = 10.0
DEFAULT_MAX_POWER_KW = 5.0
MOCK_BATTERY_TYPES = [
    {"name": "LFP", "cycles": 8000, "efficiency": 0.95, "weight": 0.7},
    {"name": "LeadAcid", "cycles": 600, "efficiency": 0.85, "weight": 0.2},
    {"name": "VRFB", "cycles": 20000, "efficiency": 0.80, "weight": 0.1},
]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_battery_runtime():
    from simulator.battery_physics import LFPBatteryModel, LeadAcidBatteryModel, VRFBBatteryModel
    from control.inverter_controller import VirtualInverterController

    return LFPBatteryModel, LeadAcidBatteryModel, VRFBBatteryModel, VirtualInverterController


def _build_actual_payload():
    return build_actual_payload(
        load_battery_runtime=_load_battery_runtime,
        rng=random,
        default_capacity_kwh=DEFAULT_CAPACITY_KWH,
        default_max_power_kw=DEFAULT_MAX_POWER_KW,
    )


def _build_mock_payload():
    return build_mock_payload(
        rng=random,
        mock_battery_types=MOCK_BATTERY_TYPES,
        timestamp=_timestamp,
        default_capacity_kwh=DEFAULT_CAPACITY_KWH,
        default_max_power_kw=DEFAULT_MAX_POWER_KW,
    )


def _build_error_payload(error):
    return build_error_payload(
        error=error,
        timestamp=_timestamp,
        default_capacity_kwh=DEFAULT_CAPACITY_KWH,
        default_max_power_kw=DEFAULT_MAX_POWER_KW,
    )

def get_battery_physics():
    """Get current battery physics state from simulator."""
    try:
        return _build_actual_payload()
    except ImportError:
        return _build_mock_payload()


def main():
    try:
        print(json.dumps(get_battery_physics(), indent=2))
        return 0
    except Exception as error:
        print(json.dumps(_build_error_payload(error), indent=2))
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
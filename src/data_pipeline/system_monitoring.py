"""System monitoring helpers for client state generation."""

from __future__ import annotations


def _calculate_system_efficiency(soc: float, temp: float) -> float:
    """Calculate overall system efficiency based on current battery conditions."""
    base_efficiency = 0.92

    if temp > 35:
        temp_factor = 1 - (temp - 35) * 0.01
    elif temp < 10:
        temp_factor = 1 - (10 - temp) * 0.005
    else:
        temp_factor = 1.0

    if soc < 20 or soc > 90:
        soc_factor = 0.98
    else:
        soc_factor = 1.0

    return base_efficiency * temp_factor * soc_factor


def _get_inverter_status(power_flow: float, soc: float) -> str:
    """Map current power flow to a coarse inverter status label."""
    _ = soc
    if abs(power_flow) < 1:
        return "IDLE"
    if power_flow > 0:
        return "CHARGING"
    return "DISCHARGING"


__all__ = [
    "_calculate_system_efficiency",
    "_get_inverter_status",
]
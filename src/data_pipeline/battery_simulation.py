"""Battery simulation helpers shared by client state generation."""

from __future__ import annotations

from typing import Dict, Tuple


def _simulate_battery_behavior(
    config: Dict,
    current_soc: float,
    price: float,
    solar_gen: float,
    load: float,
) -> Tuple[str, float]:
    """Simulate battery charging and discharging behavior."""
    battery_capacity = float(config.get("battery_capacity_kwh", 200.0))

    net_load = load - solar_gen

    low_price_threshold = 40
    high_price_threshold = 70

    max_charge_power = battery_capacity * 0.5
    max_discharge_power = battery_capacity * 0.5

    if net_load < -10:
        available_power = abs(net_load)
        charge_power = min(
            available_power,
            max_charge_power,
            (100 - current_soc) / 100 * battery_capacity,
        )
        return "CHARGE_SOLAR", charge_power

    if price < low_price_threshold and current_soc < 90:
        charge_power = min(max_charge_power, (90 - current_soc) / 100 * battery_capacity)
        return "CHARGE_GRID", charge_power

    if price > high_price_threshold and current_soc > 20:
        discharge_power = min(
            max_discharge_power,
            net_load,
            (current_soc - 20) / 100 * battery_capacity,
        )
        return "DISCHARGE", -discharge_power

    if net_load > 0 and current_soc > 30:
        discharge_power = min(
            max_discharge_power,
            net_load * 0.7,
            (current_soc - 20) / 100 * battery_capacity,
        )
        return "DISCHARGE_LOAD", -discharge_power

    return "IDLE", 0.0


def _update_battery_state(
    current_soc: float,
    current_temp: float,
    power_flow: float,
    config: Dict,
    ambient_temp: float,
) -> Tuple[float, float]:
    """Update battery SoC and temperature based on the last hour of power flow."""
    battery_capacity = float(config.get("battery_capacity_kwh", 200.0))

    efficiency = 0.95 if power_flow > 0 else 1 / 0.95

    soc_change = (power_flow * efficiency) / battery_capacity * 100
    new_soc = max(0, min(100, current_soc + soc_change))

    power_heating = abs(power_flow) * 0.05
    thermal_mass = battery_capacity * 0.5

    temp_rise = power_heating / thermal_mass
    cooling_rate = (current_temp - ambient_temp) * 0.1

    new_temp = current_temp + temp_rise - cooling_rate
    new_temp = max(ambient_temp - 5, min(ambient_temp + 30, new_temp))

    return new_soc, new_temp


def _calculate_battery_voltage(soc: float, battery_type: str) -> float:
    """Calculate battery voltage based on SoC and battery chemistry."""
    if battery_type.startswith("LFP"):
        base_voltage = 3.2
        cells_in_series = 280
        voltage_variation = 0.4 * (soc / 100)
        return (base_voltage + voltage_variation) * cells_in_series

    if battery_type.startswith("NMC"):
        base_voltage = 3.7
        cells_in_series = 150
        voltage_variation = 0.5 * (soc / 100)
        return (base_voltage + voltage_variation) * cells_in_series

    return 800 + (soc / 100) * 100


__all__ = [
    "_calculate_battery_voltage",
    "_simulate_battery_behavior",
    "_update_battery_state",
]
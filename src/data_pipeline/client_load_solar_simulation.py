"""Client load and solar simulation helpers for synthetic state generation."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Dict

import numpy as np


def _calculate_commercial_load_factor(hour: int, day_of_week: int) -> float:
    if day_of_week < 5:
        if 9 <= hour <= 21:
            return 0.7 + 0.3 * np.sin((hour - 9) * np.pi / 12)
        return 0.3

    if 10 <= hour <= 22:
        return 0.9 + 0.1 * np.sin((hour - 10) * np.pi / 12)
    return 0.3


def _calculate_office_load_factor(hour: int, day_of_week: int) -> float:
    if day_of_week >= 5:
        return 0.3
    if 8 <= hour <= 18:
        return 0.8
    if 6 <= hour <= 8 or 18 <= hour <= 20:
        return 0.4
    return 0.2


def _calculate_industrial_load_factor(hour: int, day_of_week: int) -> float:
    if day_of_week >= 5:
        return 0.5
    if 6 <= hour <= 22:
        return 0.85 + 0.1 * np.random.normal(0, 0.1)
    return 0.4


def _calculate_residential_load_factor(hour: int, _day_of_week: int) -> float:
    if 7 <= hour <= 9 or 17 <= hour <= 22:
        return 0.8
    if hour >= 22 or hour <= 6:
        return 0.3
    return 0.5


LOAD_FACTOR_CALCULATORS: dict[str, Callable[[int, int], float]] = {
    "commercial": _calculate_commercial_load_factor,
    "office": _calculate_office_load_factor,
    "industrial": _calculate_industrial_load_factor,
}


def _calculate_profile_load_factor(load_profile: str, hour: int, day_of_week: int) -> float:
    calculator = LOAD_FACTOR_CALCULATORS.get(load_profile, _calculate_residential_load_factor)
    return calculator(hour, day_of_week)


def _calculate_solar_generation(config: Dict, solar_radiation: float, cloudcover: float) -> float:
    """Calculate solar generation based on weather conditions."""
    solar_capacity = float(config.get("solar_capacity_kw", 0.0))

    panel_efficiency = 0.20
    system_efficiency = 0.85
    standard_irradiance = 1000.0

    generation_factor = (
        solar_radiation / standard_irradiance
    ) * panel_efficiency * system_efficiency
    cloud_factor = (100 - cloudcover) / 100 * 0.1 + 0.9
    solar_gen = solar_capacity * generation_factor * cloud_factor

    return max(0.0, solar_gen)


def _calculate_load_consumption(config: Dict, timestamp: datetime) -> float:
    """Calculate load consumption based on time and load profile."""
    base_load = float(config.get("base_load_kw", 30.0))
    peak_load = float(config.get("peak_load_kw", 120.0))
    load_profile = config.get("load_profile", "commercial")

    hour = timestamp.hour
    day_of_week = timestamp.weekday()

    load_factor = _calculate_profile_load_factor(load_profile, hour, day_of_week)

    load_variation = base_load + (peak_load - base_load) * max(0.0, min(1.0, load_factor))
    load_actual = load_variation * (1 + np.random.normal(0, 0.05))

    return max(base_load * 0.5, load_actual)


__all__ = [
    "_calculate_load_consumption",
    "_calculate_solar_generation",
]
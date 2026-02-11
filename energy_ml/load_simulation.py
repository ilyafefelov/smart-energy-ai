"""Core load simulation engine for Phase 4C: Load Profile System.

Provides functions to generate hourly load time series for 365 days
using LoadProfileConfig from config_models.py. Includes seasonal adjustment,
weekly patterns, base load, and simple weather correlation hooks.
"""
from typing import Dict, Tuple, Any
import math
import random
from datetime import datetime, timedelta
import json

from energy_ml.config_models import LoadProfileConfig, UserProfile


def generate_yearly_load(profile: LoadProfileConfig,
                         start_date: datetime = None,
                         seasonal_factor: float = 0.2,
                         weekend_reduction: float = 0.6,
                         random_seed: int = 42) -> Dict[str, Any]:
    """Generate 8760 hourly load values for one non-leap year (365 days).

    Returns a dict with:
    - hourly (list of 8760 floats)
    - daily_stats (list of 365 dicts with average, peak, min)
    - overall stats (dict)
    """
    random.seed(random_seed)
    if start_date is None:
        # start at Jan 1 of current year
        start_date = datetime(datetime.now().year, 1, 1)

    hours = []
    daily_stats = []

    peak_kw = profile.peak_load_kw
    base_coeffs = profile.hourly_coefficients

    # Precompute seasonal multipliers per day (simple sine curve: peak mid-year)
    seasonal = []
    for day in range(365):
        # phase shift so mid-year (day 182) is +1
        angle = 2 * math.pi * (day / 365.0)
        # seasonal between (1 - seasonal_factor) and (1 + seasonal_factor)
        seasonal.append(1.0 + seasonal_factor * math.sin(angle))

    # iterate days
    current = start_date
    for day in range(365):
        day_vals = []
        day_multiplier = seasonal[day]
        is_weekend = current.weekday() >= 5

        for hour in range(24):
            coeff = base_coeffs[hour]
            # ensure base load: 10-20% of peak when coeff is 0
            base_load = (0.15 * peak_kw) * (1.0 if coeff > 0 else 1.0)

            # Operational component scaled by coefficient and peak
            operational = coeff * peak_kw

            # Apply weekend reduction to operational component
            if is_weekend:
                operational *= weekend_reduction

            # Seasonal
            operational *= day_multiplier

            # Small random noise +/-5%
            noise = random.uniform(-0.05, 0.05) * peak_kw

            # Final hourly load, enforce positive and small minimum
            load = max(0.01, base_load + operational + noise)

            # Cap cannot exceed 1.05 * peak_kw (allow small overshoot)
            load = min(load, 1.05 * peak_kw)

            day_vals.append(round(load, 3))
            hours.append(round(load, 3))

        # daily stats
        daily_avg = sum(day_vals) / 24.0
        daily_peak = max(day_vals)
        daily_min = min(day_vals)
        daily_stats.append({"date": current.date().isoformat(),
                            "average_kW": round(daily_avg, 3),
                            "peak_kW": round(daily_peak, 3),
                            "min_kW": round(daily_min, 3)})

        current += timedelta(days=1)

    overall = {
        "annual_energy_kwh": round(sum(hours), 3),
        "annual_peak_kW": round(max(hours), 3),
        "annual_min_kW": round(min(hours), 3),
        "daily_average_kwh": round(sum(hours) / 365.0, 3)
    }

    return {"hourly": hours, "daily_stats": daily_stats, "overall": overall}


def estimate_self_consumption(load_hours: list, generation_hours: list) -> Dict[str, float]:
    """Estimate simple self-consumption percentage given load and generation time series.

    Both lists must be same length.
    Returns dict with self_consumption_pct and potential_peak_shaving_kW.
    """
    if len(load_hours) != len(generation_hours):
        raise ValueError("load_hours and generation_hours must be same length")

    total_load = sum(load_hours)
    used_generation = 0.0
    for l, g in zip(load_hours, generation_hours):
        used_generation += min(l, g)

    pct = 0.0
    if total_load > 0:
        pct = used_generation / total_load * 100.0

    # potential peak shaving estimate: average of top 5% hours where generation < load
    paired = [(l, g) for l, g in zip(load_hours, generation_hours)]
    deficits = [l - g for l, g in paired if l > g]
    deficits_sorted = sorted(deficits, reverse=True)
    top_n = max(1, int(0.05 * len(deficits_sorted)))
    peak_shave = sum(deficits_sorted[:top_n]) / top_n if deficits_sorted else 0.0

    return {"self_consumption_pct": round(pct, 2),
            "estimated_peak_shave_kW": round(peak_shave, 3)}


def simple_generation_hourly(profile: UserProfile, seed: int = 42) -> list:
    """Create a simple solar generation profile (hourly) for 365 days.

    Solar generation is approximated by a bell curve during daylight hours
    scaled by solar_capacity_kw and solar_efficiency in profile.generation.
    """
    random.seed(seed)
    hours = []
    solar_cap = profile.generation.solar_capacity_kw
    eff = profile.generation.solar_efficiency

    # simple day length model: 10 hours daylight average, peak at noon
    for day in range(365):
        for hour in range(24):
            # daylight between 6 and 18 localized
            if 6 <= hour <= 18 and solar_cap > 0:
                # gaussian-like curve centered at 12
                dist = (hour - 12) / 4.0
                value = solar_cap * eff * max(0.0, math.exp(-dist * dist))
                # small daily variability
                value *= random.uniform(0.8, 1.1)
            else:
                value = 0.0
            hours.append(round(value, 3))
    return hours

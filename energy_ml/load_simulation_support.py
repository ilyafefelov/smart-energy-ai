"""Support helpers for load simulation and summary reporting."""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Sequence

from energy_ml.config_models import UserProfile


def apply_seasonal_factor(day: int, factor: float = 0.2) -> float:
    """Apply seasonal variation using a yearly sine curve."""
    angle = 2 * math.pi * ((day - 91) / 365.0)
    return 1.0 + factor * math.sin(angle)


def apply_weekend_reduction(dow: int, coefficient: float, reduction: float = 0.6) -> float:
    """Reduce operational load on weekends."""
    if dow >= 5:
        return coefficient * reduction
    return coefficient


def apply_daily_noise(base_value: float, noise_pct: float = 0.05, seed: int | None = None) -> float:
    """Apply reproducible random variation to a simulated load value."""
    rng = random.Random(seed)
    noise = rng.uniform(-noise_pct, noise_pct) * base_value
    return base_value + noise


def simulate_year_hours(
    get_hourly_coefficient: Callable[[int, int], float],
    peak_load_kw: float,
    base_load_kw: float,
    seasonal_factor: float = 0.2,
    weekend_reduction: float = 0.6,
    random_seed: int = 42,
) -> List[float]:
    """Generate one year of hourly load values using the supplied coefficient function."""
    hours: List[float] = []
    current = datetime(datetime.now().year, 1, 1)

    for day in range(365):
        day_multiplier = apply_seasonal_factor(day, seasonal_factor)
        dow = current.weekday()

        for hour in range(24):
            coefficient = get_hourly_coefficient(hour, day)
            coefficient = apply_weekend_reduction(dow, coefficient, weekend_reduction)
            operational = coefficient * peak_load_kw * day_multiplier
            load = base_load_kw + operational
            load = apply_daily_noise(load, 0.05, random_seed + day * 24 + hour)
            load = max(0.01, load)
            load = min(load, 1.05 * peak_load_kw)
            hours.append(round(load, 3))

        current += timedelta(days=1)

    return hours


def build_daily_stats(hours: Sequence[float], start_date: datetime) -> List[Dict[str, float | str]]:
    """Build daily summary statistics from hourly load values."""
    daily_stats: List[Dict[str, float | str]] = []
    current = start_date

    for day in range(365):
        day_start = day * 24
        day_vals = list(hours[day_start : day_start + 24])
        daily_stats.append(
            {
                "date": current.date().isoformat(),
                "average_kW": round(sum(day_vals) / 24.0, 3),
                "peak_kW": round(max(day_vals), 3),
                "min_kW": round(min(day_vals), 3),
            }
        )
        current += timedelta(days=1)

    return daily_stats


def build_overall_stats(hours: Sequence[float], peak_load_kw: float) -> Dict[str, float]:
    """Build annual summary statistics from hourly load values."""
    return {
        "annual_energy_kwh": round(sum(hours), 3),
        "annual_peak_kW": round(max(hours), 3),
        "annual_min_kW": round(min(hours), 3),
        "daily_average_kwh": round(sum(hours) / 365.0, 3),
        "peak_load_configured_kw": round(peak_load_kw, 3),
        "base_load_estimated_kw": round(min(hours), 3),
    }


def build_yearly_load_report(
    hours: Sequence[float],
    peak_load_kw: float,
    start_date: datetime | None = None,
) -> Dict[str, Any]:
    """Build the public yearly load report shape from generated hours."""
    report_start = start_date or datetime(datetime.now().year, 1, 1)
    return {
        "hourly": list(hours),
        "daily_stats": build_daily_stats(hours, report_start),
        "overall": build_overall_stats(hours, peak_load_kw),
    }


def estimate_self_consumption_metrics(
    load_hours: Sequence[float],
    generation_hours: Sequence[float],
) -> Dict[str, float]:
    """Estimate self-consumption and peak shaving metrics."""
    if len(load_hours) != len(generation_hours):
        raise ValueError("load_hours and generation_hours must be same length")

    total_load = sum(load_hours)
    used_generation = sum(min(load, generation) for load, generation in zip(load_hours, generation_hours))
    pct = (used_generation / total_load * 100.0) if total_load > 0 else 0.0
    deficits = [load - generation for load, generation in zip(load_hours, generation_hours) if load > generation]

    if deficits:
        deficits_sorted = sorted(deficits, reverse=True)
        top_n = max(1, int(0.05 * len(deficits_sorted)))
        peak_shave = sum(deficits_sorted[:top_n]) / top_n
    else:
        peak_shave = 0.0

    return {
        "self_consumption_pct": round(pct, 2),
        "estimated_peak_shave_kW": round(peak_shave, 3),
    }


def simple_generation_series(profile: UserProfile, seed: int = 42) -> List[float]:
    """Create a simple solar generation profile for one year."""
    rng = random.Random(seed)
    hours: List[float] = []
    solar_cap = profile.generation.solar_capacity_kw
    efficiency = profile.generation.solar_efficiency

    for _day in range(365):
        for hour in range(24):
            if 6 <= hour <= 18 and solar_cap > 0:
                dist = (hour - 12) / 4.0
                value = solar_cap * efficiency * max(0.0, math.exp(-(dist * dist)))
                value *= rng.uniform(0.8, 1.1)
            else:
                value = 0.0
            hours.append(round(value, 3))

    return hours
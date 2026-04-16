"""Reusable optimization economics helpers for reconciliation and reporting."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Tuple


def determine_tariff_window(ts: datetime) -> str:
    """Map a timestamp to the repo's tariff window labels."""
    hour = ts.hour
    if 8 <= hour <= 20:
        return "peak"
    if hour in (7, 21):
        return "shoulder"
    return "offpeak"


def _safe_number(value: Any) -> Optional[float]:
    """Coerce a numeric-like value to float while rejecting NaN."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def compute_canonical_costs(
    *,
    predicted_action: int,
    energy_kwh: float,
    unit_price_uah_kwh: float,
    peak_price: Optional[float],
    off_peak_price: Optional[float],
) -> Tuple[float, float]:
    """Calculate baseline and optimized costs from canonical tariff inputs."""
    baseline_cost = max(0.0, energy_kwh * unit_price_uah_kwh)

    peak = peak_price if peak_price is not None else unit_price_uah_kwh
    off_peak = off_peak_price if off_peak_price is not None else unit_price_uah_kwh

    optimized_rate = unit_price_uah_kwh
    if predicted_action == 0:
        optimized_rate = min(unit_price_uah_kwh, off_peak)
    elif predicted_action == 1:
        spread = max(0.0, peak - off_peak)
        optimized_rate = max(0.0, unit_price_uah_kwh - spread)

    optimized_cost = max(0.0, energy_kwh * optimized_rate)
    return baseline_cost, optimized_cost


def _resolve_canonical_prices(
    unit_price: float,
    tariff_window: str,
    derived_window: str,
) -> Tuple[float, float]:
    """Derive canonical peak/off-peak prices when rows do not store both explicitly."""
    peak_price = unit_price if tariff_window == "peak" else (
        unit_price if derived_window == "peak" else unit_price * 1.15
    )
    off_peak_price = unit_price if tariff_window == "offpeak" else (
        unit_price if derived_window == "offpeak" else unit_price * 0.85
    )
    return peak_price, off_peak_price


__all__ = [
    "_resolve_canonical_prices",
    "_safe_number",
    "compute_canonical_costs",
    "determine_tariff_window",
]
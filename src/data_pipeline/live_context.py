"""Shared live-context parsing helpers for ML bridge and pipeline surfaces."""

from __future__ import annotations

import json
import logging
import os
from typing import Any


logger = logging.getLogger(__name__)


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float with a NaN and exception fallback."""

    try:
        numeric = float(value)
        if numeric != numeric:
            return default
        return numeric
    except Exception:
        return default


def load_live_context() -> dict[str, Any]:
    """Load the live-context payload from the bridge environment contract."""

    raw = os.getenv("ENERGY_ML_LIVE_CONTEXT_JSON")
    if not raw:
        return {}

    try:
        payload = json.loads(raw)
    except Exception as exc:
        logger.warning("Failed to parse ENERGY_ML_LIVE_CONTEXT_JSON: %s", exc)
        return {}

    return payload if isinstance(payload, dict) else {}


def parse_live_battery_state(
    battery_signal: Any,
) -> tuple[float | None, float | None, float | None]:
    """Parse optional live battery telemetry fields into a normalized tuple."""

    signal = battery_signal if isinstance(battery_signal, dict) else {}
    soc = safe_float(signal.get("soc_percent", signal.get("soc")), default=-1)
    health = safe_float(signal.get("health_percent", signal.get("health")), default=-1)
    cycles = safe_float(signal.get("cycles_remaining"), default=-1)

    return (
        soc if soc >= 0 else None,
        health if health >= 0 else None,
        cycles if cycles >= 0 else None,
    )


def parse_live_price_signal(price_signal: Any) -> tuple[float | None, dict[int, float]]:
    """Parse the current live price and next-24h hourly price map."""

    signal = price_signal if isinstance(price_signal, dict) else {}
    current_price_kwh: float | None = None
    live_price_map_kwh: dict[int, float] = {}

    current_price = safe_float(signal.get("current_uah_kwh"), default=-1)
    if current_price > 0:
        current_price_kwh = current_price

    forecast_rows = signal.get("forecast_next24h") if isinstance(signal.get("forecast_next24h"), list) else []
    for row in forecast_rows:
        if not isinstance(row, dict):
            continue
        try:
            hour = int(row.get("hour"))
        except Exception:
            logger.debug("Skipping live price row with invalid hour: %r", row.get("hour"))
            continue
        if hour < 0 or hour > 23:
            continue
        price = safe_float(row.get("price"), default=-1)
        if price <= 0:
            continue
        live_price_map_kwh[hour] = price

    return current_price_kwh, live_price_map_kwh


def price_source_for_hour(live_price_map_kwh: dict[int, float], hour: int) -> str:
    """Classify whether a given hour is backed by live market data."""

    return "live_market" if hour in live_price_map_kwh else "tariff_model"


def build_historical_data(live_context: dict[str, Any]) -> dict[str, Any]:
    """Build the historical tariff contract expected by feature extraction."""

    price_signal = live_context.get("price_signal") if isinstance(live_context.get("price_signal"), dict) else {}
    forecast_rows = price_signal.get("forecast_next24h") or []
    tariff_history: list[float] = []

    current_price = safe_float(price_signal.get("current_uah_kwh"), default=-1)
    if current_price > 0:
        tariff_history.append(current_price * 1000)

    if isinstance(forecast_rows, list):
        for row in forecast_rows:
            if not isinstance(row, dict):
                continue
            forecast_price = safe_float(row.get("price"), default=-1)
            if forecast_price > 0:
                tariff_history.append(forecast_price * 1000)

    return {"tariff_history": tariff_history}


def extract_hourly_price_map(live_context: dict[str, Any]) -> dict[int, float]:
    """Return the normalized live hourly price map from the live context."""

    _, live_price_map_kwh = parse_live_price_signal(live_context.get("price_signal"))
    return live_price_map_kwh


def build_model_inputs(user_config: Any, live_context: dict[str, Any]) -> dict[str, Any]:
    """Assemble the runtime model-input payload returned to bridge callers."""

    price_signal = live_context.get("price_signal") if isinstance(live_context.get("price_signal"), dict) else {}
    weather_signal = live_context.get("weather_signal") if isinstance(live_context.get("weather_signal"), dict) else {}
    battery_signal = live_context.get("battery_signal") if isinstance(live_context.get("battery_signal"), dict) else {}

    return {
        "optimization_strategy": getattr(user_config, "optimization_strategy", "balanced"),
        "load_profile_type": getattr(user_config, "load_profile_type", "standard"),
        "battery": {
            "type": getattr(user_config, "battery_type", "LFP"),
            "capacity_kwh": getattr(user_config, "battery_capacity_kwh", 0),
            "efficiency": getattr(user_config, "battery_efficiency", 0),
            "soc_min": getattr(user_config, "battery_soc_min", None),
            "soc_max": getattr(user_config, "battery_soc_max", None),
        },
        "generation": {
            "solar_capacity_kw": getattr(user_config, "solar_capacity_kw", 0),
            "wind_capacity_kw": getattr(user_config, "wind_capacity_kw", 0),
            "solar_efficiency": getattr(user_config, "solar_efficiency", None),
            "wind_efficiency": getattr(user_config, "wind_efficiency", None),
        },
        "location": {
            "latitude": getattr(user_config, "latitude", None),
            "longitude": getattr(user_config, "longitude", None),
            "timezone": getattr(user_config, "timezone", None),
        },
        "live_price_uah_kwh": price_signal.get("current_uah_kwh"),
        "live_weather": weather_signal.get("current"),
        "live_battery_state": {
            "soc_percent": battery_signal.get("soc_percent", battery_signal.get("soc")),
            "health_percent": battery_signal.get("health_percent", battery_signal.get("health")),
            "cycles_remaining": battery_signal.get("cycles_remaining"),
        },
    }


__all__ = [
    "build_historical_data",
    "build_model_inputs",
    "extract_hourly_price_map",
    "load_live_context",
    "parse_live_battery_state",
    "parse_live_price_signal",
    "price_source_for_hour",
    "safe_float",
]
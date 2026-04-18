"""Weather configuration helpers shared by orchestration and pipeline modules.

This module is deprecated - use src.infrastructure.settings.get_weather_coords() instead.
Kept for backward compatibility with existing callers.
"""

from __future__ import annotations

import os
from typing import Tuple

from src.infrastructure.settings import get_weather_coords


def _clamp_coordinate(raw_value: str | None, *, default: float, minimum: float, maximum: float) -> float:
    if raw_value is None:
        return default
    try:
        numeric = float(raw_value)
    except ValueError:
        return default
    return max(minimum, min(maximum, numeric))


def _resolve_weather_location() -> Tuple[float, float, str]:
    """Resolve location and timezone for weather fetches with env override compatibility."""
    default_latitude, default_longitude, default_timezone = get_weather_coords()
    latitude = _clamp_coordinate(
        os.getenv("WEATHER_LATITUDE"),
        default=default_latitude,
        minimum=-90.0,
        maximum=90.0,
    )
    longitude = _clamp_coordinate(
        os.getenv("WEATHER_LONGITUDE"),
        default=default_longitude,
        minimum=-180.0,
        maximum=180.0,
    )
    timezone = os.getenv("WEATHER_TIMEZONE", default_timezone).strip() or default_timezone
    return latitude, longitude, timezone


__all__ = ["_resolve_weather_location"]

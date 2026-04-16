"""Weather configuration helpers shared by orchestration and pipeline modules."""

from __future__ import annotations

import os
from typing import Tuple


def _resolve_weather_location() -> Tuple[float, float, str]:
    """Resolve location and timezone for weather fetches from env with Kyiv fallback."""

    try:
        latitude = float(os.getenv("WEATHER_LATITUDE", "50.45"))
        longitude = float(os.getenv("WEATHER_LONGITUDE", "30.52"))
    except ValueError:
        latitude = 50.45
        longitude = 30.52

    latitude = max(-90.0, min(90.0, latitude))
    longitude = max(-180.0, min(180.0, longitude))
    timezone = os.getenv("WEATHER_TIMEZONE", "Europe/Kiev")
    return latitude, longitude, timezone


__all__ = ["_resolve_weather_location"]
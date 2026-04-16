"""Reusable Open-Meteo fetch helpers.

These helpers intentionally return parsed hourly weather rows or ``None`` on
fetch failures. Callers decide whether to retry, fail, or synthesize fallback
weather data.
"""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Dict, List, Optional

import requests


logger = logging.getLogger(__name__)


def _fetch_openmeteo_data(lat: float, lon: float, timezone: str) -> Optional[List[Dict]]:
    """Fetch weather data from the Open-Meteo API."""

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": [
            "temperature_2m",
            "shortwave_radiation",
            "windspeed_10m",
            "cloudcover",
            "precipitation",
            "surface_pressure",
            "relativehumidity_2m",
        ],
        "forecast_days": 7,
        "timezone": timezone,
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])

        weather_records = []
        for index, time_str in enumerate(times):
            timestamp = datetime.fromisoformat(time_str.replace("T", " "))
            record = {
                "timestamp": timestamp,
                "temperature": hourly.get("temperature_2m", [None])[index] or 20.0,
                "solar_radiation": hourly.get("shortwave_radiation", [None])[index] or 0.0,
                "wind_speed": hourly.get("windspeed_10m", [None])[index] or 5.0,
                "cloudcover": hourly.get("cloudcover", [None])[index] or 50.0,
                "precipitation": hourly.get("precipitation", [None])[index] or 0.0,
                "pressure": hourly.get("surface_pressure", [None])[index] or 1013.0,
                "humidity": hourly.get("relativehumidity_2m", [None])[index] or 60.0,
                "source": "OPEN_METEO",
            }
            weather_records.append(record)

        logger.info("Fetched %s weather records from Open-Meteo", len(weather_records))
        return weather_records
    except Exception as exc:
        logger.error("Open-Meteo API error: %s", exc)
        return None


__all__ = ["_fetch_openmeteo_data"]
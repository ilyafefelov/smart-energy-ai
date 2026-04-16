"""Synthetic weather fallback generation helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

import numpy as np


def _generate_synthetic_weather() -> List[Dict]:
    """Generate synthetic weather data for development and fallback flows."""

    weather_data = []
    base_time = datetime.now().replace(minute=0, second=0, microsecond=0)

    for hour_offset in range(168):
        timestamp = base_time + timedelta(hours=hour_offset)

        month = timestamp.month
        if month in [12, 1, 2]:
            base_temp = -5 + np.random.normal(0, 8)
            max_solar = 200
        elif month in [6, 7, 8]:
            base_temp = 25 + np.random.normal(0, 6)
            max_solar = 800
        else:
            base_temp = 15 + np.random.normal(0, 7)
            max_solar = 500

        hour = timestamp.hour
        temp_adjustment = 5 * np.sin((hour - 6) * np.pi / 12)
        temperature = base_temp + temp_adjustment

        if 6 <= hour <= 18:
            solar_factor = np.sin((hour - 6) * np.pi / 12)
            cloudcover = max(0, min(100, np.random.normal(40, 20)))
            solar_radiation = max_solar * solar_factor * (100 - cloudcover) / 100
        else:
            solar_radiation = 0
            cloudcover = np.random.normal(60, 25)

        cloudcover = max(0, min(100, cloudcover))

        weather_data.append(
            {
                "timestamp": timestamp,
                "temperature": temperature,
                "solar_radiation": max(0, solar_radiation),
                "wind_speed": max(0, np.random.normal(8, 4)),
                "cloudcover": cloudcover,
                "precipitation": max(0, np.random.exponential(0.5) if np.random.random() < 0.1 else 0),
                "pressure": np.random.normal(1013, 10),
                "humidity": max(20, min(100, np.random.normal(65, 15))),
                "source": "SYNTHETIC",
            }
        )

    return weather_data


__all__ = ["_generate_synthetic_weather"]
"""Support helpers for renewable forecasting and generation modeling."""

from __future__ import annotations

import json
import math
import os
from datetime import datetime
from typing import Any, Callable, Dict, Optional

import requests


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float, falling back for invalid or NaN inputs."""
    try:
        numeric = float(value)
        if math.isnan(numeric):
            return default
        return numeric
    except Exception:
        return default


def _season_factor(now: datetime) -> float:
    return math.sin(2 * math.pi * now.timetuple().tm_yday / 365.25)


def build_live_context_weather() -> Optional[Dict[str, Any]]:
    """Build weather data from API-provided live context when available."""
    raw = os.getenv("ENERGY_ML_LIVE_CONTEXT_JSON")
    if not raw:
        return None

    try:
        payload = json.loads(raw)
    except Exception:
        return None

    weather_signal = payload.get("weather_signal") if isinstance(payload, dict) else None
    if not isinstance(weather_signal, dict):
        return None

    current = weather_signal.get("current") if isinstance(weather_signal.get("current"), dict) else {}
    next24 = weather_signal.get("next24h") if isinstance(weather_signal.get("next24h"), list) else []
    if not next24:
        return None

    hourly_forecast: Dict[str, Dict[str, float]] = {}
    for row in next24:
        if not isinstance(row, dict):
            continue
        try:
            hour = datetime.fromisoformat(str(row.get("timestamp")).replace("Z", "+00:00")).hour
        except Exception:
            continue
        hourly_forecast[f"hour_{hour}"] = {
            "solar_irradiance_w_m2": max(0.0, safe_float(row.get("shortwave_radiation_w_m2"))),
            "wind_speed_m_s": max(0.0, safe_float(row.get("wind_speed_m_s"))),
            "temperature_c": safe_float(row.get("temperature_c"), default=15.0),
        }

    if not hourly_forecast:
        return None

    now = datetime.now()
    return {
        "solar_irradiance_w_m2": max(0.0, safe_float(current.get("shortwave_radiation_w_m2"))),
        "wind_speed_m_s": max(0.0, safe_float(current.get("wind_speed_m_s"))),
        "temperature_c": safe_float(current.get("temperature_c"), default=15.0),
        "cloud_cover_fraction": max(0.0, min(1.0, safe_float(current.get("cloud_cover_percent")) / 100.0)),
        "humidity_percent": 60.0,
        "pressure_hpa": 1013.0,
        "visibility_km": 10.0,
        "current_hour": now.hour,
        "season_factor": _season_factor(now),
        "location": f"{safe_float(weather_signal.get('latitude'), 50.45):.2f}°N, {safe_float(weather_signal.get('longitude'), 30.52):.2f}°E",
        "source": weather_signal.get("source", "live_context"),
        "hourly_forecast": hourly_forecast,
    }


def _row_value(hourly: Dict[str, Any], key: str, idx: int, default: float = 0.0) -> float:
    values = hourly.get(key) if isinstance(hourly.get(key), list) else []
    if idx < 0 or idx >= len(values):
        return default
    return safe_float(values[idx], default)


def build_open_meteo_weather(latitude: float, longitude: float, logger) -> Optional[Dict[str, Any]]:
    """Fetch and normalize Open-Meteo weather data."""
    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "hourly": "temperature_2m,shortwave_radiation,wind_speed_10m,cloud_cover",
                "forecast_days": 2,
                "timezone": "auto",
            },
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()

        hourly = payload.get("hourly") if isinstance(payload, dict) else None
        if not isinstance(hourly, dict):
            return None

        times = hourly.get("time") if isinstance(hourly.get("time"), list) else []
        if not times:
            return None

        now_utc = datetime.utcnow()
        current_index = 0
        for idx, item in enumerate(times):
            try:
                timestamp = datetime.fromisoformat(str(item).replace("Z", "+00:00"))
            except Exception:
                continue
            if timestamp >= now_utc:
                current_index = idx
                break

        now = datetime.now()
        hourly_forecast: Dict[str, Dict[str, float]] = {}
        for offset in range(24):
            idx = current_index + offset
            if idx >= len(times):
                break
            timestamp = datetime.fromisoformat(str(times[idx]).replace("Z", "+00:00"))
            hourly_forecast[f"hour_{timestamp.hour}"] = {
                "solar_irradiance_w_m2": max(0.0, _row_value(hourly, "shortwave_radiation", idx)),
                "wind_speed_m_s": max(0.0, _row_value(hourly, "wind_speed_10m", idx)),
                "temperature_c": _row_value(hourly, "temperature_2m", idx, 15.0),
            }

        return {
            "solar_irradiance_w_m2": max(0.0, _row_value(hourly, "shortwave_radiation", current_index)),
            "wind_speed_m_s": max(0.0, _row_value(hourly, "wind_speed_10m", current_index)),
            "temperature_c": _row_value(hourly, "temperature_2m", current_index, 15.0),
            "cloud_cover_fraction": max(0.0, min(1.0, _row_value(hourly, "cloud_cover", current_index) / 100.0)),
            "humidity_percent": 60.0,
            "pressure_hpa": 1013.0,
            "visibility_km": 10.0,
            "current_hour": now.hour,
            "season_factor": _season_factor(now),
            "location": f"{latitude:.2f}°N, {longitude:.2f}°E",
            "source": "open-meteo",
            "hourly_forecast": hourly_forecast,
        }
    except Exception as exc:
        logger.warning("Open-Meteo weather fetch failed, using deterministic fallback: %s", exc)
        return None


def build_deterministic_fallback(latitude: float, longitude: float) -> Dict[str, Any]:
    """Build deterministic synthetic weather when live and API data are unavailable."""
    now = datetime.now()
    current_hour = now.hour
    season_factor = _season_factor(now)

    base_irradiance = 600 + 300 * season_factor
    hour_angle = (current_hour - 12) * math.pi / 6
    daily_factor = max(0.0, math.cos(hour_angle)) if 6 <= current_hour <= 18 else 0.0
    solar_irradiance = base_irradiance * daily_factor

    cloud_cover = 0.45
    solar_irradiance *= 1 - cloud_cover * 0.7
    wind_speed = max(0.0, 5.0 + 1.5 * math.sin((current_hour - 3) * math.pi / 12))
    base_temp = 15 + 15 * season_factor
    temperature = base_temp + 8 * math.sin((current_hour - 6) * math.pi / 12)

    hourly_forecast = {}
    for offset in range(24):
        forecast_hour = (current_hour + offset) % 24
        forecast_angle = (forecast_hour - 12) * math.pi / 6
        solar_daily_factor = max(0.0, math.cos(forecast_angle)) if 6 <= forecast_hour <= 18 else 0.0
        forecast_solar = base_irradiance * solar_daily_factor * (1 - cloud_cover * 0.6)
        forecast_wind = max(0.0, 5.0 + 1.3 * math.sin((forecast_hour - 4) * math.pi / 12))

        hourly_forecast[f"hour_{forecast_hour}"] = {
            "solar_irradiance_w_m2": max(0.0, forecast_solar),
            "wind_speed_m_s": forecast_wind,
            "temperature_c": base_temp + 8 * math.sin((forecast_hour - 6) * math.pi / 12),
        }

    return {
        "solar_irradiance_w_m2": max(0.0, solar_irradiance),
        "wind_speed_m_s": wind_speed,
        "temperature_c": temperature,
        "cloud_cover_fraction": cloud_cover,
        "humidity_percent": 60.0,
        "pressure_hpa": 1013.0,
        "visibility_km": 10.0,
        "current_hour": current_hour,
        "season_factor": season_factor,
        "location": f"{latitude:.2f}°N, {longitude:.2f}°E",
        "source": "deterministic_fallback",
        "hourly_forecast": hourly_forecast,
    }


def combine_forecasts(solar_forecast: Dict[str, Any], wind_forecast: Dict[str, Any]) -> Dict[str, Any]:
    """Combine solar and wind forecasts into a single renewable view."""
    solar_hourly = solar_forecast.get("hourly_generation", {})
    wind_hourly = wind_forecast.get("hourly_generation", {})
    combined_hourly = {
        f"hour_{hour}": solar_hourly.get(f"hour_{hour}", 0) + wind_hourly.get(f"hour_{hour}", 0)
        for hour in range(24)
    }

    return {
        "current_generation_kw": solar_forecast.get("current_generation_kw", 0) + wind_forecast.get("current_generation_kw", 0),
        "hourly_generation": combined_hourly,
        "daily_total_kwh": sum(solar_hourly.values()) + sum(wind_hourly.values()),
        "peak_generation_kw": (max(solar_hourly.values()) if solar_hourly else 0) + (max(wind_hourly.values()) if wind_hourly else 0),
    }


def calculate_capacity_factors(
    solar_forecast: Dict[str, Any],
    wind_forecast: Dict[str, Any],
    solar_capacity: float,
    wind_capacity: float,
) -> Dict[str, float]:
    """Calculate solar, wind, and combined capacity factors."""
    solar = 0.0
    if solar_capacity > 0 and solar_forecast:
        solar_generation = solar_forecast.get("daily_total_kwh", 0)
        solar = solar_generation / (solar_capacity * 24)

    wind = 0.0
    if wind_capacity > 0 and wind_forecast:
        wind_generation = wind_forecast.get("daily_total_kwh", 0)
        wind = wind_generation / (wind_capacity * 24)

    combined = 0.0
    total_capacity = solar_capacity + wind_capacity
    if total_capacity > 0:
        total_generation = solar_forecast.get("daily_total_kwh", 0) + wind_forecast.get("daily_total_kwh", 0)
        combined = total_generation / (total_capacity * 24)

    return {"solar": solar, "wind": wind, "combined": combined}


def integrate_prediction_with_renewables(
    prediction: Dict[str, Any],
    renewable_data: Dict[str, Any],
    next_hour: int,
) -> Dict[str, Any]:
    """Blend renewable generation data into a trading prediction."""
    if not renewable_data or renewable_data.get("timestamp") is None:
        return prediction

    current_generation = renewable_data.get("total_renewable", {}).get("current_generation_kw", 0)
    hourly_generation = renewable_data.get("total_renewable", {}).get("hourly_generation", {})
    action = prediction.get("action", "HOLD")
    confidence = prediction.get("confidence", 0.5)
    reasoning = prediction.get("reasoning", "")

    renewable_enhanced = prediction.copy()
    if current_generation > 5:
        if action == "BUY":
            renewable_enhanced["action"] = "HOLD"
            renewable_enhanced["confidence"] = min(0.9, confidence + 0.1)
            renewable_enhanced["reasoning"] = (
                f"{reasoning} Renewable generation ({current_generation:.1f} kW) reduces grid dependency."
            )
        elif action == "SELL":
            renewable_enhanced["confidence"] = min(1.0, confidence + 0.15)
            renewable_enhanced["reasoning"] = (
                f"{reasoning} High renewable generation ({current_generation:.1f} kW) supports export."
            )

    renewable_enhanced.update(
        {
            "renewable_generation_kw": current_generation,
            "renewable_forecast_available": len(hourly_generation) > 0,
            "next_hour_renewable_kw": hourly_generation.get(f"hour_{next_hour}", 0),
            "renewable_capacity_factor": renewable_data.get("capacity_factors", {}).get("combined", 0),
            "renewable_integration_applied": True,
        }
    )
    return renewable_enhanced


def calculate_panel_efficiency(temperature: float) -> float:
    """Calculate solar panel efficiency with a temperature coefficient model."""
    efficiency = 0.20 * (1 + (-0.004) * (temperature - 25))
    return max(0.10, min(0.25, efficiency))


def generate_solar_forecast(
    capacity_kw: float,
    weather_data: Dict[str, Any],
    panel_efficiency_fn: Callable[[float], float],
) -> Dict[str, Any]:
    """Generate a solar forecast from normalized weather data."""
    try:
        current_irradiance = weather_data.get("solar_irradiance_w_m2", 0)
        temperature = weather_data.get("temperature_c", 25)
        panel_efficiency = panel_efficiency_fn(temperature)
        current_generation_kw = capacity_kw * (current_irradiance / 1000) * panel_efficiency

        hourly_generation: Dict[str, float] = {}
        daily_total = 0.0
        for hour_key, hour_weather in weather_data.get("hourly_forecast", {}).items():
            hour_irradiance = hour_weather.get("solar_irradiance_w_m2", 0)
            hour_temp = hour_weather.get("temperature_c", 25)
            hour_generation = capacity_kw * (hour_irradiance / 1000) * panel_efficiency_fn(hour_temp)
            hourly_generation[hour_key] = max(0.0, hour_generation)
            daily_total += max(0.0, hour_generation)

        return {
            "current_generation_kw": max(0.0, current_generation_kw),
            "hourly_generation": hourly_generation,
            "daily_total_kwh": daily_total,
            "peak_generation_kw": max(hourly_generation.values()) if hourly_generation else 0,
            "panel_efficiency": panel_efficiency,
            "current_irradiance_w_m2": current_irradiance,
            "capacity_kw": capacity_kw,
            "performance_ratio": current_generation_kw / capacity_kw if capacity_kw > 0 else 0,
        }
    except Exception as exc:
        return {"error": str(exc)}


def wind_power_curve(wind_speed_m_s: float, rated_power_kw: float) -> float:
    """Calculate wind output using a typical cubic power curve."""
    if wind_speed_m_s < 3.0 or wind_speed_m_s > 25.0:
        return 0.0
    if wind_speed_m_s >= 12.0:
        return rated_power_kw
    power_ratio = ((wind_speed_m_s - 3.0) / (12.0 - 3.0)) ** 3
    return rated_power_kw * power_ratio


def generate_wind_forecast(
    capacity_kw: float,
    weather_data: Dict[str, Any],
    power_curve_fn: Callable[[float, float], float],
) -> Dict[str, Any]:
    """Generate a wind forecast from normalized weather data."""
    try:
        current_wind_speed = weather_data.get("wind_speed_m_s", 0)
        current_generation_kw = power_curve_fn(current_wind_speed, capacity_kw)

        hourly_generation: Dict[str, float] = {}
        daily_total = 0.0
        for hour_key, hour_weather in weather_data.get("hourly_forecast", {}).items():
            hour_generation = power_curve_fn(hour_weather.get("wind_speed_m_s", 0), capacity_kw)
            hourly_generation[hour_key] = hour_generation
            daily_total += hour_generation

        return {
            "current_generation_kw": current_generation_kw,
            "hourly_generation": hourly_generation,
            "daily_total_kwh": daily_total,
            "peak_generation_kw": max(hourly_generation.values()) if hourly_generation else 0,
            "current_wind_speed_m_s": current_wind_speed,
            "capacity_kw": capacity_kw,
            "capacity_factor": current_generation_kw / capacity_kw if capacity_kw > 0 else 0,
        }
    except Exception as exc:
        return {"error": str(exc)}
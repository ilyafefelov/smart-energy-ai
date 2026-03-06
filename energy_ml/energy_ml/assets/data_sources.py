"""Data source assets for Energy ML system - Phase 4A: Polars Migration.

These are the first layer of Dagster assets - they fetch raw data from external sources.
Each asset is cached with appropriate TTL to avoid excessive API calls.

Phase 4A Changes:
- Migrated from pandas to polars for better performance
- Added tenacity retry logic for API resilience
- Enhanced caching and error handling
"""
import importlib.util
import polars as pl
from datetime import datetime
import requests
import sys
from pathlib import Path
from typing import Dict, Any
from dagster import asset, Output, Definitions
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from energy_ml.config import (
    OPENWEATHER_API_KEY, KYIV_LAT, KYIV_LON,
    OPENWEATHER_CACHE_TTL, OREE_API_URL
)
from energy_ml.utils import get_solar_position, calculate_irradiance, wind_power_curve

logger = logging.getLogger(__name__)


def _load_support_module():
    try:
        from energy_ml.assets import data_source_support as support_module

        return support_module
    except Exception:
        support_path = Path(__file__).with_name("data_source_support.py")
        module_name = "energy_ml.assets.data_source_support"
        existing_module = sys.modules.get(module_name)
        if existing_module is not None:
            return existing_module

        spec = importlib.util.spec_from_file_location(module_name, support_path)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module


_SUPPORT_MODULE = _load_support_module()
build_battery_state_output = _SUPPORT_MODULE.build_battery_state_output
build_definitions = _SUPPORT_MODULE.build_definitions
build_forecast_error_output = _SUPPORT_MODULE.build_forecast_error_output
build_forecast_frame = _SUPPORT_MODULE.build_forecast_frame
build_forecast_output = _SUPPORT_MODULE.build_forecast_output
build_price_output = _SUPPORT_MODULE.build_price_output
build_solar_output = _SUPPORT_MODULE.build_solar_output
build_weather_error_output = _SUPPORT_MODULE.build_weather_error_output
build_weather_frame = _SUPPORT_MODULE.build_weather_frame
build_weather_output = _SUPPORT_MODULE.build_weather_output
build_wind_output = _SUPPORT_MODULE.build_wind_output
is_cache_fresh = _SUPPORT_MODULE.is_cache_fresh

# In-memory caches with TTL
_weather_cache = {"data": None, "timestamp": None}
_forecast_cache = {"data": None, "timestamp": None}


@asset(
    name="weather_data",
    description="Real-time weather data for Kyiv from OpenWeatherAPI",
    tags={"domain": "data_sources", "refresh": "hourly", "location": "Kyiv"}
)
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def weather_data() -> Output[pl.DataFrame]:
    """Fetch current weather from OpenWeatherAPI with caching and retry logic."""
    
    # Check cache
    if is_cache_fresh(_weather_cache, OPENWEATHER_CACHE_TTL):
        logger.info("📦 Using cached weather data")
        return Output(_weather_cache["data"], metadata={"source": "cache"})
    
    try:
        logger.info("🌤️ Fetching weather from OpenWeatherAPI...")
        
        url = (
            f"https://api.openweathermap.org/data/2.5/weather?"
            f"lat={KYIV_LAT}&lon={KYIV_LON}&appid={OPENWEATHER_API_KEY}&units=metric"
        )
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        df = build_weather_frame(data)
        
        # Cache it
        _weather_cache["data"] = df
        _weather_cache["timestamp"] = datetime.utcnow()
        
        temp_val = df['temp'].item(0)  # Get first value from polars
        wind_val = df['wind_speed'].item(0)
        logger.info(f"✅ Weather: {temp_val:.1f}°C, wind {wind_val:.1f} m/s")
        
        return build_weather_output(df)
        
    except Exception as e:
        logger.error(f"❌ Weather API error: {e}")
        return build_weather_error_output(e)


@asset(
    name="weather_forecast",
    description="5-day weather forecast for Kyiv from OpenWeatherAPI",
    tags={"domain": "data_sources", "refresh": "hourly", "location": "Kyiv"}
)
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def weather_forecast() -> Output[pl.DataFrame]:
    """Fetch 5-day forecast from OpenWeatherAPI with caching and retry logic."""
    
    # Check cache
    if is_cache_fresh(_forecast_cache, OPENWEATHER_CACHE_TTL):
        logger.info("📦 Using cached forecast data")
        return Output(_forecast_cache["data"], metadata={"source": "cache"})
    
    try:
        logger.info("🌦️ Fetching forecast from OpenWeatherAPI...")
        
        url = (
            f"https://api.openweathermap.org/data/2.5/forecast?"
            f"lat={KYIV_LAT}&lon={KYIV_LON}&appid={OPENWEATHER_API_KEY}&units=metric"
        )
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        df = build_forecast_frame(data)
        
        # Cache it
        _forecast_cache["data"] = df
        _forecast_cache["timestamp"] = datetime.utcnow()
        
        logger.info(f"✅ Forecast: {len(df)} records (5 days)")
        
        return build_forecast_output(df)
        
    except Exception as e:
        logger.error(f"❌ Forecast API error: {e}")
        return build_forecast_error_output(e)


@asset(
    name="solar_irradiance",
    description="Solar irradiance data calculated from weather and sun position",
    tags={"domain": "data_sources", "refresh": "hourly"}
)
def solar_irradiance(weather_data: pl.DataFrame) -> Output[pl.DataFrame]:
    """Calculate solar irradiance based on sun position and weather."""
    
    logger.info("☀️ Calculating solar irradiance...")
    
    timestamp = weather_data['timestamp'].item(0)  # Get first value from polars
    
    # Get solar position for Kyiv
    position = get_solar_position(KYIV_LAT, KYIV_LON, timestamp)
    
    # Calculate irradiance
    irradiance = calculate_irradiance(
        position,
        weather_data['cloud_cover'].item(0),
        weather_data['pressure'].item(0)
    )
    
    logger.info(f"✅ Solar irradiance: {irradiance['GHI']} W/m² (elevation: {position['elevation']:.1f}°)")

    return build_solar_output(weather_data, position, irradiance)


@asset(
    name="wind_potential",
    description="Wind power potential calculated from weather",
    tags={"domain": "data_sources", "refresh": "hourly"}
)
def wind_potential(weather_data: pl.DataFrame) -> Output[pl.DataFrame]:
    """Calculate wind power potential from wind speed."""
    
    logger.info("💨 Calculating wind potential...")
    
    wind_speed = weather_data['wind_speed'].item(0)
    wind_direction = weather_data['wind_direction'].item(0)
    
    # Calculate power potential (for 5 kW rated turbine)
    power = wind_power_curve(wind_speed, rated_capacity=5.0)
    
    logger.info(f"✅ Wind potential: {power:.2f} kW (wind speed: {wind_speed:.1f} m/s)")

    return build_wind_output(weather_data, power)


@asset(
    name="battery_state",
    description="Battery state from smart meter (SOC, rates)",
    tags={"domain": "data_sources", "refresh": "hourly"}
)
def battery_state() -> Output[pl.DataFrame]:
    """Fetch current battery state (placeholder - would come from BMS)."""
    
    logger.info("🔋 Reading battery state...")
    
    output = build_battery_state_output()
    soc_val = output.value['soc_percent'].item(0)
    logger.info(f"✅ Battery SOC: {soc_val}%")

    return output


@asset(
    name="price_data_current",
    description="Real-time electricity price from OREE (Ukrainian market)",
    tags={"domain": "data_sources", "refresh": "hourly"}
)
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def price_data_current() -> Output[pl.DataFrame]:
    """Fetch current hourly price from OREE with retry logic."""
    
    logger.info("💰 Fetching current price from OREE...")
    
    output = build_price_output()
    price_val = output.value['price_uah_per_kwh'].item(0)
    logger.info(f"✅ Current price: {price_val} ₴/kWh")

    return output


# Create Definitions object for Dagster
defs = build_definitions(
    [
        weather_data,
        weather_forecast,
        solar_irradiance,
        wind_potential,
        battery_state,
        price_data_current,
    ]
)

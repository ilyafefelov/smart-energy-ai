"""Data source assets for Energy ML system.

These are the first layer of Dagster assets - they fetch raw data from external sources.
Each asset is cached with appropriate TTL to avoid excessive API calls.
"""
import pandas as pd
from datetime import datetime, timedelta
import requests
from typing import Dict, Any
from dagster import asset, Output, Definitions
import logging

from energy_ml.config import (
    OPENWEATHER_API_KEY, KYIV_LAT, KYIV_LON,
    OPENWEATHER_CACHE_TTL, OREE_API_URL
)
from energy_ml.utils import get_solar_position, calculate_irradiance, wind_power_curve

logger = logging.getLogger(__name__)

# In-memory caches with TTL
_weather_cache = {"data": None, "timestamp": None}
_forecast_cache = {"data": None, "timestamp": None}


def _is_cache_fresh(cache_dict: Dict, ttl_seconds: int) -> bool:
    """Check if cache is still fresh."""
    if cache_dict["timestamp"] is None:
        return False
    return (datetime.utcnow() - cache_dict["timestamp"]).total_seconds() < ttl_seconds


@asset(
    name="weather_data",
    description="Real-time weather data for Kyiv from OpenWeatherAPI",
    tags={"domain": "data_sources", "refresh": "hourly", "location": "Kyiv"}
)
def weather_data() -> Output[pd.DataFrame]:
    """Fetch current weather from OpenWeatherAPI with caching."""
    
    # Check cache
    if _is_cache_fresh(_weather_cache, OPENWEATHER_CACHE_TTL):
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
        
        df = pd.DataFrame({
            'timestamp': [datetime.utcnow()],
            'temp': [data['main']['temp']],
            'humidity': [data['main']['humidity']],
            'cloud_cover': [data['clouds']['all']],
            'wind_speed': [data['wind']['speed']],
            'wind_direction': [data['wind'].get('deg', 0)],
            'pressure': [data['main']['pressure']],
            'description': [data['weather'][0]['description']],
        })
        
        # Cache it
        _weather_cache["data"] = df
        _weather_cache["timestamp"] = datetime.utcnow()
        
        logger.info(f"✅ Weather: {df['temp'].values[0]:.1f}°C, wind {df['wind_speed'].values[0]:.1f} m/s")
        
        return Output(
            df,
            metadata={
                "rows": len(df),
                "temp_c": float(df['temp'].values[0]),
                "wind_speed_ms": float(df['wind_speed'].values[0]),
                "source": "openweatherapi"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Weather API error: {e}")
        # Return defaults on error
        df = pd.DataFrame({
            'timestamp': [datetime.utcnow()],
            'temp': [15.0],
            'humidity': [60.0],
            'cloud_cover': [50.0],
            'wind_speed': [5.0],
            'wind_direction': [180.0],
            'pressure': [1013.0],
            'description': ['Unknown'],
        })
        return Output(df, metadata={"error": str(e)})


@asset(
    name="weather_forecast",
    description="5-day weather forecast for Kyiv from OpenWeatherAPI",
    tags={"domain": "data_sources", "refresh": "hourly", "location": "Kyiv"}
)
def weather_forecast() -> Output[pd.DataFrame]:
    """Fetch 5-day forecast from OpenWeatherAPI with caching."""
    
    # Check cache
    if _is_cache_fresh(_forecast_cache, OPENWEATHER_CACHE_TTL):
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
        
        records = []
        for item in data.get('list', [])[:40]:  # 5 days
            records.append({
                'timestamp': pd.Timestamp.fromtimestamp(item['dt']),
                'temp': item['main']['temp'],
                'cloud_cover': item['clouds']['all'],
                'wind_speed': item['wind']['speed'],
                'precipitation': item.get('rain', {}).get('3h', 0),
            })
        
        df = pd.DataFrame(records)
        
        # Cache it
        _forecast_cache["data"] = df
        _forecast_cache["timestamp"] = datetime.utcnow()
        
        logger.info(f"✅ Forecast: {len(df)} records (5 days)")
        
        return Output(
            df,
            metadata={
                "rows": len(df),
                "days": len(df) / 8,  # 8 records per day
                "source": "openweatherapi"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Forecast API error: {e}")
        # Return empty dataframe on error
        df = pd.DataFrame({
            'timestamp': pd.date_range(start=datetime.utcnow(), periods=40, freq='3H'),
            'temp': [15.0] * 40,
            'cloud_cover': [50.0] * 40,
            'wind_speed': [5.0] * 40,
            'precipitation': [0.0] * 40,
        })
        return Output(df, metadata={"error": str(e)})


@asset(
    name="solar_irradiance",
    description="Solar irradiance data calculated from weather and sun position",
    tags={"domain": "data_sources", "refresh": "hourly"}
)
def solar_irradiance(weather_data: pd.DataFrame) -> Output[pd.DataFrame]:
    """Calculate solar irradiance based on sun position and weather."""
    
    logger.info("☀️ Calculating solar irradiance...")
    
    timestamp = weather_data['timestamp'].values[0]
    dt = pd.Timestamp(timestamp).to_pydatetime()
    
    # Get solar position for Kyiv
    position = get_solar_position(KYIV_LAT, KYIV_LON, dt)
    
    # Calculate irradiance
    irradiance = calculate_irradiance(
        position,
        weather_data['cloud_cover'].values[0],
        weather_data['pressure'].values[0]
    )
    
    df = pd.DataFrame({
        'timestamp': weather_data['timestamp'],
        'ghi_w_per_m2': [irradiance['GHI']],
        'dni_w_per_m2': [irradiance['DNI']],
        'dhi_w_per_m2': [irradiance['DHI']],
        'elevation_deg': [position['elevation']],
        'azimuth_deg': [position['azimuth']],
        'is_night': [position['is_night']],
    })
    
    logger.info(f"✅ Solar irradiance: {irradiance['GHI']} W/m² (elevation: {position['elevation']:.1f}°)")
    
    return Output(
        df,
        metadata={
            "ghi_w_m2": irradiance['GHI'],
            "elevation_deg": position['elevation'],
            "is_night": position['is_night'],
        }
    )


@asset(
    name="wind_potential",
    description="Wind power potential calculated from weather",
    tags={"domain": "data_sources", "refresh": "hourly"}
)
def wind_potential(weather_data: pd.DataFrame) -> Output[pd.DataFrame]:
    """Calculate wind power potential from wind speed."""
    
    logger.info("💨 Calculating wind potential...")
    
    wind_speed = weather_data['wind_speed'].values[0]
    wind_direction = weather_data['wind_direction'].values[0]
    
    # Calculate power potential (for 5 kW rated turbine)
    power = wind_power_curve(wind_speed, rated_capacity=5.0)
    
    df = pd.DataFrame({
        'timestamp': weather_data['timestamp'],
        'wind_speed_ms': [wind_speed],
        'wind_direction_deg': [wind_direction],
        'power_potential_kw': [power],
    })
    
    logger.info(f"✅ Wind potential: {power:.2f} kW (wind speed: {wind_speed:.1f} m/s)")
    
    return Output(
        df,
        metadata={
            "wind_speed_ms": wind_speed,
            "power_potential_kw": power,
        }
    )


@asset(
    name="battery_state",
    description="Battery state from smart meter (SOC, rates)",
    tags={"domain": "data_sources", "refresh": "hourly"}
)
def battery_state() -> Output[pd.DataFrame]:
    """Fetch current battery state (placeholder - would come from BMS)."""
    
    logger.info("🔋 Reading battery state...")
    
    df = pd.DataFrame({
        'timestamp': [datetime.utcnow()],
        'soc_percent': [72.6],
        'charge_rate_kw': [3.5],
        'discharge_rate_kw': [4.2],
        'capacity_kwh': [13.5],
        'health_percent': [95.0],
    })
    
    logger.info(f"✅ Battery SOC: {df['soc_percent'].values[0]}%")
    
    return Output(
        df,
        metadata={
            "soc_percent": df['soc_percent'].values[0],
            "health_percent": df['health_percent'].values[0],
        }
    )


@asset(
    name="price_data_current",
    description="Real-time electricity price from OREE (Ukrainian market)",
    tags={"domain": "data_sources", "refresh": "hourly"}
)
def price_data_current() -> Output[pd.DataFrame]:
    """Fetch current hourly price from OREE."""
    
    logger.info("💰 Fetching current price from OREE...")
    
    # Placeholder - actual API integration depends on OREE structure
    # For now, use realistic value
    df = pd.DataFrame({
        'timestamp': [datetime.utcnow()],
        'price_uah_per_kwh': [14.26],
        'currency': ['UAH'],
        'market': ['OREE'],
    })
    
    logger.info(f"✅ Current price: {df['price_uah_per_kwh'].values[0]} ₴/kWh")
    
    return Output(
        df,
        metadata={
            "price_uah_kwh": df['price_uah_per_kwh'].values[0],
            "market": "OREE",
        }
    )


# Create Definitions object for Dagster
defs = Definitions(
    assets=[
        weather_data,
        weather_forecast,
        solar_irradiance,
        wind_potential,
        battery_state,
        price_data_current,
    ]
)

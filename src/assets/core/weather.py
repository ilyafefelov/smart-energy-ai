"""
Weather Data Asset - Open-Meteo Integration

Dagster asset for fetching weather forecast data for solar generation modeling.
Integrates with Open-Meteo API for reliable weather data.

Thesis Relevance: Weather data is critical for solar generation forecasting
and energy arbitrage optimization in renewable energy systems.
"""

import polars as pl
from dagster import asset
import logging

from src.data_pipeline.openmeteo_fetch import _fetch_openmeteo_data
from src.data_pipeline.solar_features import _add_solar_features
from src.data_pipeline.synthetic_weather import _generate_synthetic_weather
from src.data_pipeline.weather_config import _resolve_weather_location
from src.data_pipeline.weather_validation import _validate_weather_data

logger = logging.getLogger(__name__)


@asset(
    group_name="weather_data",
    description="Weather forecast data from Open-Meteo API",
    metadata={
        "source": "https://api.open-meteo.com/",
        "update_frequency": "Every 6 hours",
        "forecast_horizon": "7 days"
    }
)
def weather_asset() -> pl.DataFrame:
    """
    Fetch weather forecast data from Open-Meteo API.
    
    Returns:
        Polars DataFrame with columns:
        - timestamp: Hour timestamp
        - temperature: Temperature in °C
        - solar_radiation: Global horizontal irradiance (W/m²)
        - wind_speed: Wind speed in m/s
        - cloudcover: Cloud coverage percentage
        - precipitation: Precipitation in mm
        - pressure: Air pressure in hPa
        - humidity: Relative humidity percentage
        - source: Data source identifier
    """
    logger.info("Starting weather data fetch from Open-Meteo")
    
    latitude, longitude, timezone = _resolve_weather_location()
    
    try:
        # Fetch current conditions + 7-day forecast
        weather_data = _fetch_openmeteo_data(latitude, longitude, timezone)
        
        if not weather_data:
            logger.warning("Open-Meteo API unavailable, generating synthetic data")
            weather_data = _generate_synthetic_weather()
            
        # Convert to Polars DataFrame
        df = pl.DataFrame(weather_data)
        
        # Data quality validation
        df = _validate_weather_data(df)
        
        # Add derived solar features
        df = _add_solar_features(df, latitude)
        
        logger.info(f"Weather asset materialized: {len(df)} hours of data")
        return df
        
    except Exception as e:
        logger.error(f"Failed to fetch weather data: {e}")
        return pl.DataFrame(_generate_synthetic_weather())



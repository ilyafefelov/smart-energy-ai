"""
Weather Data Asset - Open-Meteo Integration

Dagster asset for fetching weather forecast data for solar generation modeling.
Integrates with Open-Meteo API for reliable weather data.

Thesis Relevance: Weather data is critical for solar generation forecasting
and energy arbitrage optimization in renewable energy systems.
"""

import polars as pl
from dagster import asset, MetadataValue
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import requests
import numpy as np

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
    
    # Default location: Kyiv, Ukraine (50.45°N, 30.52°E)
    latitude = 50.45
    longitude = 30.52
    
    try:
        # Fetch current conditions + 7-day forecast
        weather_data = _fetch_openmeteo_data(latitude, longitude)
        
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


def _fetch_openmeteo_data(lat: float, lon: float) -> Optional[List[Dict]]:
    """Fetch weather data from Open-Meteo API."""
    
    # Open-Meteo API endpoint
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
            "relativehumidity_2m"
        ],
        "forecast_days": 7,
        "timezone": "Europe/Kiev"
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract hourly data
        hourly = data.get('hourly', {})
        times = hourly.get('time', [])
        
        weather_records = []
        
        for i, time_str in enumerate(times):
            timestamp = datetime.fromisoformat(time_str.replace('T', ' '))
            
            record = {
                'timestamp': timestamp,
                'temperature': hourly.get('temperature_2m', [None])[i] or 20.0,
                'solar_radiation': hourly.get('shortwave_radiation', [None])[i] or 0.0,
                'wind_speed': hourly.get('windspeed_10m', [None])[i] or 5.0,
                'cloudcover': hourly.get('cloudcover', [None])[i] or 50.0,
                'precipitation': hourly.get('precipitation', [None])[i] or 0.0,
                'pressure': hourly.get('surface_pressure', [None])[i] or 1013.0,
                'humidity': hourly.get('relativehumidity_2m', [None])[i] or 60.0,
                'source': 'OPEN_METEO'
            }
            
            weather_records.append(record)
            
        logger.info(f"Fetched {len(weather_records)} weather records from Open-Meteo")
        return weather_records
        
    except Exception as e:
        logger.error(f"Open-Meteo API error: {e}")
        return None


def _generate_synthetic_weather() -> List[Dict]:
    """Generate synthetic weather data for development/testing."""
    weather_data = []
    base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    
    # Generate 7 days of hourly data
    for hour_offset in range(168):  # 7 * 24 hours
        timestamp = base_time + timedelta(hours=hour_offset)
        
        # Seasonal temperature pattern (simplified)
        month = timestamp.month
        if month in [12, 1, 2]:  # Winter
            base_temp = -5 + np.random.normal(0, 8)
            max_solar = 200
        elif month in [6, 7, 8]:  # Summer
            base_temp = 25 + np.random.normal(0, 6)
            max_solar = 800
        else:  # Spring/Fall
            base_temp = 15 + np.random.normal(0, 7)
            max_solar = 500
            
        # Daily temperature cycle
        hour = timestamp.hour
        temp_adjustment = 5 * np.sin((hour - 6) * np.pi / 12)
        temperature = base_temp + temp_adjustment
        
        # Solar radiation (zero at night, peak at noon)
        if 6 <= hour <= 18:
            solar_factor = np.sin((hour - 6) * np.pi / 12)
            cloudcover = max(0, min(100, np.random.normal(40, 20)))
            solar_radiation = max_solar * solar_factor * (100 - cloudcover) / 100
        else:
            solar_radiation = 0
            cloudcover = np.random.normal(60, 25)
            
        cloudcover = max(0, min(100, cloudcover))
        
        record = {
            'timestamp': timestamp,
            'temperature': temperature,
            'solar_radiation': max(0, solar_radiation),
            'wind_speed': max(0, np.random.normal(8, 4)),
            'cloudcover': cloudcover,
            'precipitation': max(0, np.random.exponential(0.5) if np.random.random() < 0.1 else 0),
            'pressure': np.random.normal(1013, 10),
            'humidity': max(20, min(100, np.random.normal(65, 15))),
            'source': 'SYNTHETIC'
        }
        
        weather_data.append(record)
        
    return weather_data


def _validate_weather_data(df: pl.DataFrame) -> pl.DataFrame:
    """Validate and clean weather data."""
    logger.info(f"Validating weather data: {len(df)} records")
    
    # Clean invalid values
    df = df.with_columns([
        # Temperature bounds (-40°C to 50°C)
        pl.col('temperature').clip(-40, 50).alias('temperature'),
        
        # Solar radiation bounds (0 to 1200 W/m²)
        pl.col('solar_radiation').clip(0, 1200).alias('solar_radiation'),
        
        # Wind speed bounds (0 to 50 m/s)
        pl.col('wind_speed').clip(0, 50).alias('wind_speed'),
        
        # Cloud cover percentage (0-100%)
        pl.col('cloudcover').clip(0, 100).alias('cloudcover'),
        
        # Humidity percentage (0-100%)
        pl.col('humidity').clip(0, 100).alias('humidity'),
        
        # Pressure bounds (950-1050 hPa)
        pl.col('pressure').clip(950, 1050).alias('pressure'),
        
        # Precipitation bounds (0-100 mm/hour)
        pl.col('precipitation').clip(0, 100).alias('precipitation'),
    ])
    
    # Sort by timestamp
    df = df.sort('timestamp')
    
    # Add quality flags
    df = df.with_columns([
        (pl.col('solar_radiation') > 1000).alias('high_solar'),
        (pl.col('wind_speed') > 15).alias('high_wind'),
        (pl.col('precipitation') > 10).alias('heavy_rain'),
        pl.lit(datetime.now()).alias('fetched_at')
    ])
    
    logger.info(f"Weather validation complete: {len(df)} valid records")
    return df


def _add_solar_features(df: pl.DataFrame, latitude: float) -> pl.DataFrame:
    """Add derived solar features for energy modeling."""
    
    df = df.with_columns([
        # Hour of day and day of year for solar calculations
        pl.col('timestamp').dt.hour().alias('hour'),
        pl.col('timestamp').dt.ordinal_day().alias('day_of_year'),
        
        # Solar elevation angle (simplified calculation)
        _calculate_solar_elevation(pl.col('timestamp'), latitude).alias('solar_elevation'),
        
        # Clear sky index (how clear is the sky)
        ((100 - pl.col('cloudcover')) / 100).alias('clear_sky_index'),
        
        # Effective solar radiation (considering clouds)
        (pl.col('solar_radiation') * (100 - pl.col('cloudcover')) / 100).alias('effective_solar'),
        
        # Day/night indicator
        pl.col('timestamp').dt.hour().is_between(6, 18).alias('is_daylight'),
        
        # Season indicator
        pl.when(pl.col('timestamp').dt.month().is_in([12, 1, 2]))
        .then(pl.lit('winter'))
        .when(pl.col('timestamp').dt.month().is_in([3, 4, 5]))
        .then(pl.lit('spring'))
        .when(pl.col('timestamp').dt.month().is_in([6, 7, 8]))
        .then(pl.lit('summer'))
        .otherwise(pl.lit('autumn'))
        .alias('season'),
        
        # Weather condition categories
        pl.when(pl.col('cloudcover') < 25)
        .then(pl.lit('clear'))
        .when(pl.col('cloudcover') < 75)
        .then(pl.lit('partly_cloudy'))
        .otherwise(pl.lit('cloudy'))
        .alias('sky_condition')
    ])
    
    return df


def _calculate_solar_elevation(timestamp_col, latitude: float):
    """Simplified solar elevation calculation for Polars expression."""
    # This is a simplified approximation - would use more complex solar position algorithms in production
    return (
        pl.lit(90) - 
        (timestamp_col.dt.hour() - 12).abs() * pl.lit(15.0 / 90.0) * 90
    ).clip(0, 90)


def get_weather_location_config() -> Dict[str, Tuple[float, float]]:
    """Get predefined weather locations for different clients."""
    return {
        'kyiv': (50.45, 30.52),
        'lviv': (49.84, 24.03), 
        'dnipro': (48.46, 35.04),
        'kharkiv': (49.99, 36.23),
        'odesa': (46.48, 30.73),
        'zaporizhzhia': (47.84, 35.14)
    }


# Test and validation functions
def test_weather_asset():
    """Test weather asset functionality."""
    df = weather_asset()
    
    assert len(df) > 0, "Weather data should contain records"
    assert 'timestamp' in df.columns, "Timestamp column required"
    assert 'temperature' in df.columns, "Temperature column required"
    assert 'solar_radiation' in df.columns, "Solar radiation column required"
    
    # Check data quality
    assert df['solar_radiation'].min() >= 0, "Solar radiation should be non-negative"
    assert df['solar_radiation'].max() <= 1200, "Solar radiation should be realistic"
    assert df['temperature'].min() > -50, "Temperature should be reasonable"
    assert df['temperature'].max() < 60, "Temperature should be reasonable"
    
    print(f"✅ Weather data test passed: {len(df)} records")
    return True


if __name__ == "__main__":
    # Test the asset
    test_weather_asset()
    
    # Sample run
    df = weather_asset()
    print(f"\nWeather Data Sample:")
    print(df.head())
    print(f"\nWeather Statistics:")
    print(f"Temperature - Min: {df['temperature'].min():.1f}°C, Max: {df['temperature'].max():.1f}°C, Avg: {df['temperature'].mean():.1f}°C")
    print(f"Solar Radiation - Min: {df['solar_radiation'].min():.0f} W/m², Max: {df['solar_radiation'].max():.0f} W/m², Avg: {df['solar_radiation'].mean():.0f} W/m²")
    print(f"Wind Speed - Avg: {df['wind_speed'].mean():.1f} m/s, Max: {df['wind_speed'].max():.1f} m/s")
"""
Weather data ingestion from Open-Meteo API
Fetches 24-hour forecast and stores in PostgreSQL
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging

from src.db import SessionLocal
from src.models import WeatherForecast

logger = logging.getLogger(__name__)

OPEN_METEO_API = "https://api.open-meteo.com/v1/forecast"


class WeatherIngester:
    """Fetch and store weather data from Open-Meteo API"""

    def __init__(self, latitude=50.45, longitude=30.52):
        """Initialize with Kyiv coordinates by default"""
        self.latitude = latitude
        self.longitude = longitude
        self.session = SessionLocal()

    def fetch_weather(self) -> dict:
        """Fetch 24-hour weather forecast from Open-Meteo API"""
        try:
            params = {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "hourly": [
                    "temperature_2m",
                    "direct_normal_irradiance",  # Solar radiation
                    "cloudcover",
                    "windspeed_10m",
                    "relative_humidity_2m"
                ],
                "timezone": "Europe/Kiev",
                "forecast_days": 1
            }

            logger.info(f"Fetching weather from Open-Meteo for ({self.latitude}, {self.longitude})")
            response = requests.get(OPEN_METEO_API, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            logger.info("✓ Weather data fetched successfully")
            return data

        except requests.RequestException as e:
            logger.error(f"✗ Failed to fetch weather data: {e}")
            return None

    def parse_weather_data(self, data: dict) -> pd.DataFrame:
        """Parse API response into DataFrame"""
        if not data or 'hourly' not in data:
            logger.error("Invalid weather data format")
            return None

        hourly = data['hourly']
        df = pd.DataFrame({
            'timestamp': pd.to_datetime(hourly['time']),
            'temperature': hourly['temperature_2m'],
            'solar_radiation': hourly['direct_normal_irradiance'],  # W/m²
            'cloudcover': hourly['cloudcover'],  # %
            'wind_speed': hourly['windspeed_10m'],
            'humidity': hourly['relative_humidity_2m']
        })

        logger.info(f"Parsed {len(df)} weather records")
        return df

    def validate_weather_data(self, df: pd.DataFrame) -> bool:
        """Validate weather data for quality issues"""
        issues = []

        # Check for NaN values
        missing_cols = df.columns[df.isnull().any()].tolist()
        if missing_cols:
            issues.append(f"Missing values in: {missing_cols}")

        # Check radiation bounds (0-2000 W/m²)
        bad_radiation = df[df['solar_radiation'].between(0, 2000, inclusive='neither')].shape[0]
        if bad_radiation > 0:
            logger.warning(f"Found {bad_radiation} records with unrealistic radiation values")

        # Check temperature bounds (-50 to 50°C for Earth)
        bad_temp = df[~df['temperature'].between(-50, 50)].shape[0]
        if bad_temp > 0:
            issues.append(f"Invalid temperature in {bad_temp} records")

        # Check cloudcover bounds (0-100%)
        bad_cloud = df[~df['cloudcover'].between(0, 100)].shape[0]
        if bad_cloud > 0:
            issues.append(f"Invalid cloudcover in {bad_cloud} records")

        if issues:
            logger.warning(f"Weather validation warnings: {'; '.join(issues)}")
            return False

        logger.info("✓ Weather data validation passed")
        return True

    def store_weather_data(self, df: pd.DataFrame) -> int:
        """Store weather data in PostgreSQL"""
        count = 0
        try:
            for _, row in df.iterrows():
                # Check if record already exists
                existing = self.session.query(WeatherForecast).filter_by(
                    timestamp=row['timestamp']
                ).first()

                if existing:
                    # Update if it exists
                    existing.temperature = row['temperature']
                    existing.solar_radiation = row['solar_radiation']
                    existing.cloudcover = row['cloudcover']
                    existing.wind_speed = row['wind_speed']
                    existing.humidity = row['humidity']
                    logger.debug(f"Updated weather record for {row['timestamp']}")
                else:
                    # Create new record
                    record = WeatherForecast(
                        timestamp=row['timestamp'],
                        temperature=row['temperature'],
                        solar_radiation=row['solar_radiation'],
                        cloudcover=row['cloudcover'],
                        wind_speed=row['wind_speed'],
                        humidity=row['humidity']
                    )
                    self.session.add(record)
                    logger.debug(f"Inserted weather record for {row['timestamp']}")
                
                count += 1

            self.session.commit()
            logger.info(f"✓ Stored {count} weather records in PostgreSQL")
            return count

        except Exception as e:
            self.session.rollback()
            logger.error(f"✗ Failed to store weather data: {e}")
            return 0

    def run(self) -> bool:
        """Execute full ingestion pipeline"""
        logger.info("Starting weather data ingestion...")

        # Fetch from API
        data = self.fetch_weather()
        if not data:
            return False

        # Parse data
        df = self.parse_weather_data(data)
        if df is None or df.empty:
            return False

        # Validate data
        self.validate_weather_data(df)

        # Store in DB
        count = self.store_weather_data(df)

        self.session.close()
        return count > 0


def ingest_weather(latitude=50.45, longitude=30.52) -> bool:
    """Main entry point for weather ingestion"""
    logging.basicConfig(level=logging.INFO)
    ingester = WeatherIngester(latitude, longitude)
    return ingester.run()


if __name__ == "__main__":
    # Test weather ingestion
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    success = ingest_weather()
    if success:
        print("\n✓ Weather ingestion completed successfully")
    else:
        print("\n✗ Weather ingestion failed")

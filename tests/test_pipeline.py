"""
Unit tests for data pipeline
Tests: database connections, API ingestion, validation
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from src.db import SessionLocal, engine, Base, health_check
from src.models import WeatherForecast, MarketPrice
from src.data_pipeline.ingest_weather import WeatherIngester
from src.data_pipeline.ingest_prices import PriceIngester
from src.data_pipeline.validate import DataValidator, WeatherDataModel, MarketPriceModel


@pytest.fixture
def db_session():
    """Create test database session"""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


class TestDatabase:
    """Test database connectivity and models"""

    def test_health_check(self):
        """Test database health check"""
        result = health_check()
        assert result is True

    def test_create_weather_record(self, db_session):
        """Test creating weather forecast record"""
        record = WeatherForecast(
            timestamp=datetime.now(),
            temperature=5.5,
            solar_radiation=450.0,
            cloudcover=75.0,
            wind_speed=3.2,
            humidity=65.0
        )
        db_session.add(record)
        db_session.commit()

        retrieved = db_session.query(WeatherForecast).first()
        assert retrieved is not None
        assert retrieved.temperature == 5.5
        assert retrieved.cloudcover == 75.0

    def test_create_price_record(self, db_session):
        """Test creating market price record"""
        record = MarketPrice(
            timestamp=datetime.now(),
            price_eur_mwh=7.5,
            price_uah_mwh=262.5
        )
        db_session.add(record)
        db_session.commit()

        retrieved = db_session.query(MarketPrice).first()
        assert retrieved is not None
        assert retrieved.price_eur_mwh == 7.5

    def test_unique_timestamp_constraint(self, db_session):
        """Test unique timestamp constraint"""
        now = datetime.now()
        record1 = WeatherForecast(
            timestamp=now,
            temperature=5.5,
            solar_radiation=450.0,
            cloudcover=75.0
        )
        db_session.add(record1)
        db_session.commit()

        # Try to add duplicate timestamp
        record2 = WeatherForecast(
            timestamp=now,
            temperature=6.0,
            solar_radiation=500.0,
            cloudcover=80.0
        )
        db_session.add(record2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestWeatherValidation:
    """Test Pydantic weather data validation"""

    def test_valid_weather_data(self):
        """Test valid weather record"""
        data = {
            "timestamp": datetime.now(),
            "temperature": 5.5,
            "solar_radiation": 450.0,
            "cloudcover": 75.0,
            "wind_speed": 3.2,
            "humidity": 65.0
        }
        model = WeatherDataModel(**data)
        assert model.temperature == 5.5

    def test_temperature_out_of_bounds(self):
        """Test temperature validation"""
        data = {
            "timestamp": datetime.now(),
            "temperature": -100.0,  # Invalid: < -50
            "solar_radiation": 450.0,
            "cloudcover": 75.0,
            "wind_speed": 3.2
        }
        with pytest.raises(ValueError):
            WeatherDataModel(**data)

    def test_radiation_out_of_bounds(self):
        """Test solar radiation validation"""
        data = {
            "timestamp": datetime.now(),
            "temperature": 5.5,
            "solar_radiation": 3000.0,  # Invalid: > 2000
            "cloudcover": 75.0,
            "wind_speed": 3.2
        }
        with pytest.raises(ValueError):
            WeatherDataModel(**data)

    def test_cloudcover_bounds(self):
        """Test cloudcover percentage validation"""
        data = {
            "timestamp": datetime.now(),
            "temperature": 5.5,
            "solar_radiation": 450.0,
            "cloudcover": 150.0,  # Invalid: > 100
            "wind_speed": 3.2
        }
        with pytest.raises(ValueError):
            WeatherDataModel(**data)


class TestPriceValidation:
    """Test Pydantic price data validation"""

    def test_valid_price_data(self):
        """Test valid price record"""
        data = {
            "timestamp": datetime.now(),
            "price_eur_mwh": 7.5
        }
        model = MarketPriceModel(**data)
        assert model.price_eur_mwh == 7.5

    def test_price_out_of_bounds_high(self):
        """Test price too high"""
        data = {
            "timestamp": datetime.now(),
            "price_eur_mwh": 50.0  # Invalid: > 20
        }
        with pytest.raises(ValueError):
            MarketPriceModel(**data)

    def test_price_out_of_bounds_low(self):
        """Test price too low"""
        data = {
            "timestamp": datetime.now(),
            "price_eur_mwh": 0.1  # Invalid: < 0.5
        }
        with pytest.raises(ValueError):
            MarketPriceModel(**data)

    def test_realistic_ukraine_prices(self):
        """Test realistic Ukraine market prices"""
        prices = [2.5, 5.0, 7.5, 10.0, 15.0]  # All realistic
        for price in prices:
            data = {
                "timestamp": datetime.now(),
                "price_eur_mwh": price
            }
            model = MarketPriceModel(**data)
            assert model.price_eur_mwh == price


class TestDataValidator:
    """Test batch validation service"""

    def test_validate_weather_batch(self):
        """Test batch weather validation"""
        data = [
            {
                "timestamp": datetime.now(),
                "temperature": 5.5,
                "solar_radiation": 450.0,
                "cloudcover": 75.0,
                "wind_speed": 3.2
            },
            {
                "timestamp": datetime.now(),
                "temperature": 3.0,
                "solar_radiation": 200.0,
                "cloudcover": 50.0,
                "wind_speed": 2.0
            }
        ]
        valid, invalid = DataValidator.validate_batch(data, "weather")
        assert valid == 2
        assert invalid == 0

    def test_validate_price_batch(self):
        """Test batch price validation"""
        data = [
            {"timestamp": datetime.now(), "price_eur_mwh": 7.5},
            {"timestamp": datetime.now(), "price_eur_mwh": 5.0},
            {"timestamp": datetime.now(), "price_eur_mwh": 100.0}  # Invalid
        ]
        valid, invalid = DataValidator.validate_batch(data, "price")
        assert valid == 2
        assert invalid == 1


class TestWeatherIngester:
    """Test weather API ingestion"""

    @patch('src.data_pipeline.ingest_weather.requests.get')
    def test_fetch_weather_success(self, mock_get):
        """Test successful weather API call"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'hourly': {
                'time': ['2026-01-29T12:00', '2026-01-29T13:00'],
                'temperature_2m': [5.5, 6.0],
                'direct_normal_irradiance': [450.0, 500.0],
                'cloudcover': [75.0, 70.0],
                'windspeed_10m': [3.2, 3.5],
                'relative_humidity_2m': [65.0, 63.0]
            }
        }
        mock_get.return_value = mock_response

        ingester = WeatherIngester()
        data = ingester.fetch_weather()
        
        assert data is not None
        assert 'hourly' in data

    @patch('src.data_pipeline.ingest_weather.requests.get')
    def test_fetch_weather_api_error(self, mock_get):
        """Test weather API error handling"""
        mock_get.side_effect = Exception("Connection error")
        
        ingester = WeatherIngester()
        data = ingester.fetch_weather()
        
        assert data is None

    def test_parse_weather_data(self):
        """Test parsing weather API response"""
        raw_data = {
            'hourly': {
                'time': ['2026-01-29T12:00'],
                'temperature_2m': [5.5],
                'direct_normal_irradiance': [450.0],
                'cloudcover': [75.0],
                'windspeed_10m': [3.2],
                'relative_humidity_2m': [65.0]
            }
        }
        
        ingester = WeatherIngester()
        df = ingester.parse_weather_data(raw_data)
        
        assert df is not None
        assert len(df) == 1
        assert df['temperature'].iloc[0] == 5.5


class TestPriceIngester:
    """Test price API ingestion"""

    def test_price_ingester_init(self):
        """Test price ingester initialization"""
        ingester = PriceIngester()
        assert ingester is not None

    def test_fallback_price_data(self):
        """Test fallback price data generation"""
        ingester = PriceIngester()
        df = ingester._parse_price_html(None)
        
        assert df is not None
        assert len(df) == 24  # 24 hours
        assert 'price_eur_mwh' in df.columns


# Integration tests
class TestPipelineIntegration:
    """Test full pipeline integration"""

    def test_weather_to_db_flow(self, db_session):
        """Test complete weather ingestion flow"""
        # Create test data
        record = WeatherForecast(
            timestamp=datetime.now(),
            temperature=5.5,
            solar_radiation=450.0,
            cloudcover=75.0,
            wind_speed=3.2
        )
        db_session.add(record)
        db_session.commit()

        # Retrieve and validate
        retrieved = db_session.query(WeatherForecast).first()
        is_valid, error = DataValidator.validate_weather({
            'timestamp': retrieved.timestamp,
            'temperature': retrieved.temperature,
            'solar_radiation': retrieved.solar_radiation,
            'cloudcover': retrieved.cloudcover,
            'wind_speed': retrieved.wind_speed
        })
        
        assert is_valid is True

    def test_24_hour_forecast_validation(self):
        """Test 24-hour forecast dataset validation"""
        now = datetime.now()
        data_list = []
        
        for hour in range(24):
            data_list.append({
                'timestamp': now.replace(hour=hour),
                'temperature': 5.0 + (hour % 10) * 0.1,
                'solar_radiation': 450.0 + (hour - 12) ** 2,
                'cloudcover': 50.0 + (hour % 5) * 5,
                'wind_speed': 3.0
            })
        
        valid, invalid = DataValidator.validate_batch(data_list, "weather")
        assert valid == 24
        assert invalid == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

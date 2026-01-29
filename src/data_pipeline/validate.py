"""
Data quality validation layer for Smart Energy AI
Validates incoming data before storage
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WeatherDataModel(BaseModel):
    """Pydantic model for weather data validation"""
    timestamp: datetime
    temperature: float = Field(..., ge=-50, le=50)  # -50 to 50°C
    solar_radiation: float = Field(..., ge=0, le=2000)  # 0 to 2000 W/m²
    cloudcover: float = Field(..., ge=0, le=100)  # 0 to 100%
    wind_speed: float = Field(..., ge=0, le=50)  # 0 to 50 m/s
    humidity: Optional[float] = Field(None, ge=0, le=100)  # 0 to 100%

    @validator('temperature')
    def validate_temperature(cls, v):
        if v < -50 or v > 50:
            raise ValueError(f"Temperature {v}°C is outside realistic bounds")
        return v

    @validator('solar_radiation')
    def validate_radiation(cls, v):
        if v < 0 or v > 2000:
            raise ValueError(f"Solar radiation {v} W/m² is outside realistic bounds")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-01-29T12:00:00",
                "temperature": 5.5,
                "solar_radiation": 450.0,
                "cloudcover": 75.0,
                "wind_speed": 3.2,
                "humidity": 65.0
            }
        }


class MarketPriceModel(BaseModel):
    """Pydantic model for market price validation"""
    timestamp: datetime
    price_eur_mwh: float = Field(..., ge=0.5, le=20)  # 0.5 to 20 EUR/MWh
    price_uah_mwh: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None

    @validator('price_eur_mwh')
    def validate_price(cls, v):
        if v < 0.5 or v > 20:
            raise ValueError(f"Price {v} EUR/MWh is outside realistic bounds for Ukraine")
        return v

    @validator('min_price')
    def validate_min_price(cls, v):
        if v is not None and (v < 0 or v > 20):
            raise ValueError(f"Min price {v} is unrealistic")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-01-29T12:00:00",
                "price_eur_mwh": 7.5,
                "price_uah_mwh": 262.5,
                "min_price": 7.1,
                "max_price": 7.9
            }
        }


class OptimizationActionModel(BaseModel):
    """Pydantic model for RL optimization actions"""
    timestamp: datetime
    action: int = Field(..., ge=0, le=4)  # 0=charge, 1=discharge, 2=sell, 3=buy, 4=idle
    confidence: float = Field(..., ge=0, le=1)  # 0 to 1
    estimated_cost_savings: Optional[float] = None

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-01-29T12:00:00",
                "action": 1,  # discharge
                "confidence": 0.85,
                "estimated_cost_savings": 150.0
            }
        }


class DataValidator:
    """Central validation service"""

    @staticmethod
    def validate_weather(data: dict) -> tuple[bool, Optional[str]]:
        """Validate weather data"""
        try:
            WeatherDataModel(**data)
            return True, None
        except Exception as e:
            logger.error(f"Weather validation failed: {e}")
            return False, str(e)

    @staticmethod
    def validate_price(data: dict) -> tuple[bool, Optional[str]]:
        """Validate market price data"""
        try:
            MarketPriceModel(**data)
            return True, None
        except Exception as e:
            logger.error(f"Price validation failed: {e}")
            return False, str(e)

    @staticmethod
    def validate_action(data: dict) -> tuple[bool, Optional[str]]:
        """Validate optimization action"""
        try:
            OptimizationActionModel(**data)
            return True, None
        except Exception as e:
            logger.error(f"Action validation failed: {e}")
            return False, str(e)

    @staticmethod
    def validate_batch(data_list: List[dict], data_type: str) -> tuple[int, int]:
        """
        Validate a batch of records
        Returns: (valid_count, invalid_count)
        """
        valid = 0
        invalid = 0

        for record in data_list:
            if data_type == "weather":
                is_valid, _ = DataValidator.validate_weather(record)
            elif data_type == "price":
                is_valid, _ = DataValidator.validate_price(record)
            else:
                is_valid = False

            if is_valid:
                valid += 1
            else:
                invalid += 1

        logger.info(f"Batch validation ({data_type}): {valid} valid, {invalid} invalid")
        return valid, invalid


if __name__ == "__main__":
    # Test validation
    logging.basicConfig(level=logging.INFO)

    test_weather = {
        "timestamp": datetime.now(),
        "temperature": 5.5,
        "solar_radiation": 450.0,
        "cloudcover": 75.0,
        "wind_speed": 3.2,
        "humidity": 65.0
    }

    is_valid, error = DataValidator.validate_weather(test_weather)
    print(f"Weather validation: {is_valid}")
    if error:
        print(f"  Error: {error}")

    test_price = {
        "timestamp": datetime.now(),
        "price_eur_mwh": 7.5
    }

    is_valid, error = DataValidator.validate_price(test_price)
    print(f"Price validation: {is_valid}")
    if error:
        print(f"  Error: {error}")

"""
Centralized Settings for Smart Energy AI

Uses Pydantic Settings for environment variable validation and management.
All configuration flows through this module - no scattered os.getenv calls.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    # Primary URL (overrides individual settings)
    database_url: Optional[str] = Field(
        default=None,
        description="Full database URL (postgresql://user:pass@host:port/db)",
    )

    # Individual components (used when database_url is not set)
    db_host: str = Field(default="localhost", description="Database host")
    db_port: int = Field(default=5432, description="Database port")
    db_user: str = Field(default="dagster", description="Database username")
    db_password: str = Field(default="dagster", description="Database password")
    db_name: str = Field(default="dagster", description="Database name")

    # Legacy compatibility: DATABASE_URL from .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )

    def get_url(self) -> str:
        """Get database URL, building from components if not set directly."""
        if self.database_url:
            return self.database_url
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


class WeatherSettings(BaseSettings):
    """Weather API settings (Open-Meteo)."""

    api_url: str = Field(
        default="https://api.open-meteo.com/v1/forecast",
        description="Open-Meteo API URL",
    )
    latitude: float = Field(default=50.45, description="Location latitude (Kyiv)")
    longitude: float = Field(default=30.52, description="Location longitude (Kyiv)")
    timezone: str = Field(default="Europe/Kiev", description="Timezone for weather data")

    model_config = SettingsConfigDict(env_prefix="WEATHER_", extra="ignore")

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if not -90 <= v <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if not -180 <= v <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return v


class OreeSettings(BaseSettings):
    """OREE Ukraine market data API settings."""

    api_url: str = Field(
        default="https://www.oree.com.ua/",
        description="OREE Ukraine API base URL",
    )
    timeout_seconds: int = Field(default=30, description="Request timeout")

    model_config = SettingsConfigDict(env_prefix="OREE_", extra="ignore")


class S3Settings(BaseSettings):
    """S3 storage settings for IO manager."""

    bucket: str = Field(default="", description="S3 bucket name")
    key_prefix: str = Field(
        default="smart-energy-ai/assets",
        description="S3 key prefix for assets",
    )
    region: Optional[str] = Field(default=None, description="AWS region")
    max_retries: int = Field(default=3, description="Max retry attempts")

    model_config = SettingsConfigDict(
        env_prefix="S3_IO_MANAGER_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @property
    def is_configured(self) -> bool:
        """Check if S3 is configured (bucket is set)."""
        return bool(self.bucket.strip())


class MLflowSettings(BaseSettings):
    """MLflow tracking server settings."""

    tracking_uri: Optional[str] = Field(
        default=None,
        description="MLflow tracking server URI",
    )

    # Model serving
    serving_mode: str = Field(
        default="heuristic",
        description="ML serving mode: 'heuristic', 'learned_policy', 'ensemble'",
    )
    model_name: str = Field(
        default="battery-optimizer",
        description="Registered model name in MLflow",
    )
    model_alias: str = Field(
        default="champion",
        description="Model version alias",
    )

    model_config = SettingsConfigDict(env_prefix="ENERGY_ML_", extra="ignore")


class DagsterSettings(BaseSettings):
    """Dagster orchestration settings."""

    home: Path = Field(
        default=Path("data/dagster_home"),
        description="Dagster home directory",
    )
    host: str = Field(default="0.0.0.0", description="Dagster host")
    port: int = Field(default=3000, description="Dagster port")
    log_level: str = Field(default="INFO", description="Log level")

    model_config = SettingsConfigDict(env_prefix="DAGSTER_", extra="ignore")


class AppSettings(BaseSettings):
    """
    Root settings that aggregates all sub-settings.
    
    Usage:
        from src.infrastructure.settings import get_settings
        
        settings = get_settings()
        db_url = settings.database.get_url()
        weather_lat = settings.weather.latitude
    """

    # Sub-settings domains
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    weather: WeatherSettings = Field(default_factory=WeatherSettings)
    oree: OreeSettings = Field(default_factory=OreeSettings)
    s3: S3Settings = Field(default_factory=S3Settings)
    mlflow: MLflowSettings = Field(default_factory=MLflowSettings)
    dagster: DagsterSettings = Field(default_factory=DagsterSettings)

    # App-wide settings
    log_level: str = Field(default="INFO", description="Application log level")
    debug: bool = Field(default=False, description="Debug mode")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Global singleton
_settings: Optional[AppSettings] = None


@lru_cache
def get_settings() -> AppSettings:
    """
    Get the global settings singleton.
    
    Uses lru_cache so settings are parsed once per process.
    """
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings


def reload_settings() -> AppSettings:
    """Force reload settings (clears cache)."""
    global _settings
    _settings = None
    get_settings.cache_clear()
    return get_settings()


# Convenience accessors for common patterns
def get_database_url() -> str:
    """Get the configured database URL."""
    return get_settings().database.get_url()


def get_weather_coords() -> tuple[float, float, str]:
    """Get weather coordinates as (latitude, longitude, timezone)."""
    s = get_settings().weather
    return s.latitude, s.longitude, s.timezone


def is_s3_configured() -> bool:
    """Check if S3 IO manager is configured."""
    return get_settings().s3.is_configured


if __name__ == "__main__":
    # Quick validation
    import logging

    logging.basicConfig(level=logging.INFO)

    settings = get_settings()
    print("=" * 60)
    print("Smart Energy AI - Settings Validation")
    print("=" * 60)

    print("\n📊 Database:")
    print(f"   URL: {settings.database.get_url()}")

    print("\n🌤️  Weather (Open-Meteo):")
    print(f"   Location: {settings.weather.latitude}, {settings.weather.longitude}")
    print(f"   Timezone: {settings.weather.timezone}")

    print("\n⚡ OREE Market Data:")
    print(f"   API: {settings.oree.api_url}")

    print("\n🪣 S3 Storage:")
    print(f"   Configured: {settings.s3.is_configured}")
    if settings.s3.is_configured:
        print(f"   Bucket: {settings.s3.bucket}")
        print(f"   Region: {settings.s3.region}")

    print("\n🤖 MLflow:")
    print(f"   Tracking URI: {settings.mlflow.tracking_uri}")
    print(f"   Serving Mode: {settings.mlflow.serving_mode}")
    print(f"   Model: {settings.mlflow.model_name}:{settings.mlflow.model_alias}")

    print("\n🐙 Dagster:")
    print(f"   Home: {settings.dagster.home}")
    print(f"   Port: {settings.dagster.port}")

    print("\n" + "=" * 60)
    print("✅ Settings loaded successfully")

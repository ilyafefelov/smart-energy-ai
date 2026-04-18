"""Infrastructure layer for Smart Energy AI.

This package contains database connections, configuration management,
and external API clients - the infrastructure plumbing that supports
the domain logic and orchestration layers.
"""

from .db import Base, SessionLocal, engine, get_db, init_db, health_check
from .config import SystemConfig, get_config
from .settings import (
    AppSettings,
    DatabaseSettings,
    WeatherSettings,
    OreeSettings,
    S3Settings,
    MLflowSettings,
    DagsterSettings,
    get_settings,
    get_database_url,
    get_weather_coords,
    is_s3_configured,
    reload_settings,
)

__all__ = [
    # Database
    "Base",
    "SessionLocal",
    "engine",
    "get_db",
    "init_db",
    "health_check",
    # Config (legacy)
    "SystemConfig",
    "get_config",
    # Settings (new centralized)
    "AppSettings",
    "DatabaseSettings",
    "WeatherSettings",
    "OreeSettings",
    "S3Settings",
    "MLflowSettings",
    "DagsterSettings",
    "get_settings",
    "get_database_url",
    "get_weather_coords",
    "is_s3_configured",
    "reload_settings",
]

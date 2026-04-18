"""Weather data ingestion command.

Wraps the existing WeatherIngester from src/data_pipeline/ingest_weather.py
into a CLI-command-compatible function with proper logging and error handling.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)


def ingest_weather_command(
    latitude: float = 50.45,
    longitude: float = 30.52,
    log_level: str = "INFO",
) -> bool:
    """Execute weather data ingestion as a CLI command.

    Args:
        latitude: Location latitude (default: Kyiv)
        longitude: Location longitude (default: Kyiv)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        True if ingestion succeeded, False otherwise
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info(f"Starting weather ingestion for ({latitude}, {longitude})")

    try:
        from src.data_pipeline.ingest_weather import WeatherIngester

        ingester = WeatherIngester(latitude=latitude, longitude=longitude)
        success = ingester.run()

        if success:
            logger.info("✅ Weather ingestion completed successfully")
            return True
        else:
            logger.error("❌ Weather ingestion failed")
            return False

    except Exception as e:
        logger.exception(f"Unexpected error during weather ingestion: {e}")
        return False


def main(args: Optional[list[str]] = None) -> int:
    """CLI entry point for the ingest-weather command."""
    parser = argparse.ArgumentParser(description="Ingest weather data from Open-Meteo API")
    parser.add_argument(
        "--latitude",
        type=float,
        default=50.45,
        help="Location latitude (default: Kyiv 50.45)",
    )
    parser.add_argument(
        "--longitude",
        type=float,
        default=30.52,
        help="Location longitude (default: Kyiv 30.52)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    parsed = parser.parse_args(args)
    success = ingest_weather_command(
        latitude=parsed.latitude,
        longitude=parsed.longitude,
        log_level=parsed.log_level,
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
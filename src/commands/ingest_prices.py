"""Price data ingestion command.

Wraps the existing PriceIngester from src/data_pipeline/ingest_prices.py
into a CLI-command-compatible function with proper logging and error handling.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)


def ingest_prices_command(
    log_level: str = "INFO",
) -> bool:
    """Execute price data ingestion from OREE Ukraine as a CLI command.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        True if ingestion succeeded, False otherwise
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Starting price ingestion from OREE Ukraine")

    try:
        from src.data_pipeline.ingest_prices import PriceIngester

        ingester = PriceIngester()
        success = ingester.run()

        if success:
            logger.info("✅ Price ingestion completed successfully")
            return True
        else:
            logger.error("❌ Price ingestion failed")
            return False

    except Exception as e:
        logger.exception(f"Unexpected error during price ingestion: {e}")
        return False


def main(args: Optional[list[str]] = None) -> int:
    """CLI entry point for the ingest-prices command."""
    parser = argparse.ArgumentParser(description="Ingest electricity prices from OREE Ukraine")
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    parsed = parser.parse_args(args)
    success = ingest_prices_command(log_level=parsed.log_level)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
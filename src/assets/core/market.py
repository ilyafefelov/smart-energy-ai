"""
Core Market Data Asset - OREE Price Integration

Dagster asset for fetching Ukrainian electricity market prices from OREE.
Migrated from V1 OREE scraper with enhanced error handling and metadata.

Thesis Relevance: Demonstrates real-time market data integration in 
Software-Defined Assets architecture.
"""

import polars as pl
from dagster import asset, AssetMaterialization, MetadataValue
from datetime import datetime, timedelta
import logging
from typing import Optional

from src.data_pipeline.oree_fetch import (
    _extract_oree_price_rows,
    _extract_prices_from_data_view_content,
    _fetch_oree_data_view_prices,
    _fetch_oree_prices,
    _parse_decimal,
    _parse_hour_value,
)
from src.data_pipeline.market_validation import _validate_market_data
from src.data_pipeline.synthetic_market import _generate_synthetic_prices

logger = logging.getLogger(__name__)


@asset(
    group_name="market_data",
    description="Ukrainian electricity market prices from OREE",
    metadata={
        "source": "https://www.oree.com.ua/",
        "update_frequency": "Daily at 15:00 UTC",
        "data_retention": "30 days"
    }
)
def market_data_asset() -> pl.DataFrame:
    """
    Fetch hourly electricity prices from OREE (Ukrainian market operator).
    
    Returns:
        Polars DataFrame with columns:
        - timestamp: Hour timestamp
        - price_eur_mwh: Price in EUR/MWh
        - price_uah_mwh: Price in UAH/MWh
        - volume_mwh: Traded volume
        - source: Data source identifier
    """
    logger.info("Starting OREE market data fetch")
    
    try:
        # Fetch current day + next day prices
        current_prices = _fetch_oree_prices(datetime.now().date())
        next_day_prices = _fetch_oree_prices(datetime.now().date() + timedelta(days=1))
        
        # Combine datasets
        all_prices = []
        if current_prices:
            all_prices.extend(current_prices)
        if next_day_prices:
            all_prices.extend(next_day_prices)
            
        if not all_prices:
            # Fallback to synthetic data for development
            logger.warning("No OREE data available, generating synthetic data")
            all_prices = _generate_synthetic_prices()
            
        # Convert to Polars DataFrame
        df = pl.DataFrame(all_prices)
        
        # Data quality checks
        df = _validate_market_data(df)
        
        # Log metadata for Dagster
        logger.info(f"Market data asset materialized: {len(df)} hours of data")
        
        return df
        
    except Exception as e:
        logger.error(f"Failed to fetch market data: {e}")
        # Return synthetic data as failsafe
        return pl.DataFrame(_generate_synthetic_prices())

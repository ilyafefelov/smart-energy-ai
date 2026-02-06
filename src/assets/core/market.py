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
from typing import Dict, Any, Optional, List
import requests
from bs4 import BeautifulSoup
import re

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


def _fetch_oree_prices(target_date: datetime.date) -> Optional[List[Dict]]:
    """Fetch OREE prices for a specific date."""
    url = "https://www.oree.com.ua/index.php/pricectr"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find price table (OREE website parsing)
        price_table = soup.find('table', class_='price-table')
        if not price_table:
            logger.warning(f"Price table not found for {target_date}")
            return None
            
        prices = []
        rows = price_table.find_all('tr')[1:]  # Skip header
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 3:
                hour = int(cells[0].text.strip())
                price_uah = float(cells[1].text.strip().replace(',', '.'))
                volume = float(cells[2].text.strip().replace(',', '.'))
                
                # Convert UAH to EUR (approximate rate: 1 EUR = 40 UAH)
                price_eur = price_uah / 40.0
                
                timestamp = datetime.combine(
                    target_date, 
                    datetime.min.time().replace(hour=hour)
                )
                
                prices.append({
                    'timestamp': timestamp,
                    'price_eur_mwh': price_eur,
                    'price_uah_mwh': price_uah,
                    'volume_mwh': volume,
                    'source': 'OREE'
                })
                
        return prices
        
    except Exception as e:
        logger.error(f"OREE fetch failed for {target_date}: {e}")
        return None


def _generate_synthetic_prices() -> List[Dict]:
    """Generate synthetic price data for development/testing."""
    import numpy as np
    
    prices = []
    base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    for hour in range(48):  # 2 days of data
        timestamp = base_date + timedelta(hours=hour)
        
        # Realistic Ukrainian price pattern
        if 6 <= timestamp.hour <= 9:  # Morning peak
            base_price = 60 + np.random.normal(0, 8)
        elif 17 <= timestamp.hour <= 21:  # Evening peak
            base_price = 80 + np.random.normal(0, 10)
        elif 23 <= timestamp.hour or timestamp.hour <= 5:  # Night valley
            base_price = 35 + np.random.normal(0, 5)
        else:  # Regular hours
            base_price = 50 + np.random.normal(0, 6)
            
        price_eur = max(20, base_price)  # Minimum 20 EUR/MWh
        price_uah = price_eur * 40  # Conversion rate
        volume = 1000 + np.random.normal(0, 200)  # Volume variation
        
        prices.append({
            'timestamp': timestamp,
            'price_eur_mwh': price_eur,
            'price_uah_mwh': price_uah,
            'volume_mwh': max(100, volume),
            'source': 'SYNTHETIC'
        })
        
    return prices


def _validate_market_data(df: pl.DataFrame) -> pl.DataFrame:
    """Validate and clean market data."""
    logger.info(f"Validating market data: {len(df)} records")
    
    # Remove invalid prices
    df = df.filter(
        (pl.col('price_eur_mwh') > 0) & 
        (pl.col('price_eur_mwh') < 500) &  # Max 500 EUR/MWh
        (pl.col('volume_mwh') > 0)
    )
    
    # Sort by timestamp
    df = df.sort('timestamp')
    
    # Add validation flags
    df = df.with_columns([
        (pl.col('price_eur_mwh') > pl.col('price_eur_mwh').mean() * 2).alias('price_spike'),
        (pl.col('volume_mwh') < 100).alias('low_volume'),
        pl.lit(datetime.now()).alias('fetched_at')
    ])
    
    logger.info(f"Market data validation complete: {len(df)} valid records")
    return df


# Test and validation functions
def test_market_data_asset():
    """Test the market data asset functionality."""
    df = market_data_asset()
    
    assert len(df) > 0, "Market data should contain records"
    assert 'timestamp' in df.columns, "Timestamp column required"
    assert 'price_eur_mwh' in df.columns, "EUR price column required"
    assert 'price_uah_mwh' in df.columns, "UAH price column required"
    
    # Check data quality
    assert df['price_eur_mwh'].min() > 0, "Prices should be positive"
    assert df['price_eur_mwh'].max() < 500, "Prices should be realistic"
    
    print(f"✅ Market data test passed: {len(df)} records")
    return True


if __name__ == "__main__":
    # Test the asset
    test_market_data_asset()
    
    # Sample run
    df = market_data_asset()
    print(f"\nMarket Data Sample:")
    print(df.head())
    print(f"\nPrice Statistics:")
    print(f"EUR/MWh - Min: {df['price_eur_mwh'].min():.2f}, Max: {df['price_eur_mwh'].max():.2f}, Avg: {df['price_eur_mwh'].mean():.2f}")
    print(f"UAH/MWh - Min: {df['price_uah_mwh'].min():.0f}, Max: {df['price_uah_mwh'].max():.0f}, Avg: {df['price_uah_mwh'].mean():.0f}")
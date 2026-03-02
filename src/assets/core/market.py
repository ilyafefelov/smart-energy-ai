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
UAH_PER_EUR = 40.0


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
    url = "https://www.oree.com.ua/index.php/pricectr?lang=english"
    
    try:
        data_view_prices = _fetch_oree_data_view_prices(target_date)
        if data_view_prices:
            return data_view_prices

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        prices = _extract_oree_price_rows(soup, target_date)
        if not prices:
            logger.warning(f"No parseable OREE rows found for {target_date}")
            return None

        return prices
        
    except Exception as e:
        logger.error(f"OREE fetch failed for {target_date}: {e}")
        return None


def _fetch_oree_data_view_prices(target_date: datetime.date) -> Optional[List[Dict]]:
    """Fetch OREE prices from dynamic data_view endpoint used by the official web page."""
    try:
        response = requests.post(
            "https://www.oree.com.ua/index.php/pricectr/data_view",
            data={
                "date": target_date.strftime("%m.%Y"),
                "market": "DAM",
                "zone": "IPS",
            },
            timeout=30,
        )
        response.raise_for_status()

        payload = response.json()
        content = payload.get("content", "") if isinstance(payload, dict) else ""
        if not content:
            return None

        prices = _extract_prices_from_data_view_content(content, target_date)
        if prices:
            logger.info(f"Parsed {len(prices)} OREE rows from data_view endpoint for {target_date}")
        return prices or None
    except Exception as e:
        logger.warning(f"OREE data_view fetch failed for {target_date}: {e}")
        return None


def _extract_prices_from_data_view_content(content_html: str, target_date: datetime.date) -> List[Dict]:
    """Extract hourly prices from OREE data_view HTML table for a specific date."""
    soup = BeautifulSoup(content_html, "html.parser")
    table = soup.find("table")
    if table is None:
        return []

    rows = table.find_all("tr")
    if len(rows) < 2:
        return []

    target_date_label = target_date.strftime("%d.%m.%Y")
    for row in rows[1:]:
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
        if not cells:
            continue
        if cells[0] != target_date_label:
            continue

        parsed_rows: List[Dict] = []
        # OREE columns are 1..24; map to 00:00..23:00 for this day.
        for hour_idx, price_text in enumerate(cells[1:25], start=1):
            price_uah = _parse_decimal(price_text)
            if price_uah is None or price_uah <= 0:
                continue

            timestamp = datetime.combine(target_date, datetime.min.time().replace(hour=hour_idx - 1))
            parsed_rows.append(
                {
                    "timestamp": timestamp,
                    "price_eur_mwh": float(price_uah / UAH_PER_EUR),
                    "price_uah_mwh": float(price_uah),
                    "volume_mwh": 1000.0,
                    "source": "OREE_DATA_VIEW",
                }
            )

        return parsed_rows

    return []


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
        price_uah = price_eur * UAH_PER_EUR  # Conversion rate
        volume = 1000 + np.random.normal(0, 200)  # Volume variation
        
        prices.append({
            'timestamp': timestamp,
            'price_eur_mwh': price_eur,
            'price_uah_mwh': price_uah,
            'volume_mwh': max(100, volume),
            'source': 'SYNTHETIC'
        })
        
    return prices


def _extract_oree_price_rows(soup: BeautifulSoup, target_date: datetime.date) -> List[Dict]:
    """Extract hourly price rows from any parseable OREE table layout."""
    preferred_tables = soup.find_all('table', class_='price-table')
    tables = preferred_tables or soup.find_all('table')
    if not tables:
        logger.warning("No tables found on OREE page")
        return []

    best_candidate: List[Dict] = []
    for table in tables:
        parsed = _parse_table_rows(table, target_date)
        if len(parsed) > len(best_candidate):
            best_candidate = parsed

    if best_candidate:
        logger.info(f"Parsed {len(best_candidate)} OREE rows from HTML tables")
    return best_candidate


def _parse_table_rows(table: Any, target_date: datetime.date) -> List[Dict]:
    """Parse one table into hourly rows when hour/price columns can be identified."""
    rows = table.find_all('tr')
    if not rows:
        return []

    parsed_rows: List[Dict] = []
    seen_hours = set()

    for row in rows:
        cells = row.find_all(['td', 'th'])
        if len(cells) < 2:
            continue

        cell_text = [cell.get_text(" ", strip=True) for cell in cells]
        hour = _parse_hour_value(cell_text[0])
        if hour is None or hour in seen_hours:
            continue

        price_raw = _parse_decimal(cell_text[1])
        if price_raw is None:
            continue

        volume = _parse_decimal(cell_text[2]) if len(cell_text) > 2 else None
        if volume is None:
            volume = 1000.0

        # OREE values are usually UAH/MWh; keep support for EUR/MWh if page format changes.
        if price_raw > 500:
            price_uah = price_raw
            price_eur = price_raw / UAH_PER_EUR
        else:
            price_eur = price_raw
            price_uah = price_raw * UAH_PER_EUR

        if not (0 < price_eur < 500):
            continue

        timestamp = datetime.combine(target_date, datetime.min.time().replace(hour=hour))
        parsed_rows.append(
            {
                'timestamp': timestamp,
                'price_eur_mwh': float(price_eur),
                'price_uah_mwh': float(price_uah),
                'volume_mwh': float(max(0.0, volume)),
                'source': 'OREE',
            }
        )
        seen_hours.add(hour)

    return sorted(parsed_rows, key=lambda row: row['timestamp'])


def _parse_hour_value(text: str) -> Optional[int]:
    """Parse hour from values like '0', '00:00', or '00:00-01:00'."""
    if not text:
        return None

    for match in re.findall(r"(\d{1,2})(?::\d{2})?", text):
        hour = int(match)
        if 0 <= hour <= 23:
            return hour
    return None


def _parse_decimal(text: str) -> Optional[float]:
    """Parse decimal number from localized numeric text with separators and units."""
    if not text:
        return None

    cleaned = text.replace("\xa0", " ").replace(" ", "")
    number_match = re.search(r"[-+]?\d+[\d.,]*", cleaned)
    if not number_match:
        return None

    raw = number_match.group(0)
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")

    try:
        return float(raw)
    except ValueError:
        return None


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
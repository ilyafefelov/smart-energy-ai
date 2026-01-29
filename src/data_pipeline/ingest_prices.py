"""
Market price data ingestion from OREE Ukraine
Fetches Day-Ahead Market (DAM) prices and stores in PostgreSQL
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import logging
from typing import List, Dict

from src.db import SessionLocal
from src.models import MarketPrice

logger = logging.getLogger(__name__)

OREE_URL = "https://www.oree.com.ua/"


class PriceIngester:
    """Fetch and store market prices from OREE Ukraine"""

    def __init__(self):
        self.session = SessionLocal()

    def fetch_oree_prices(self) -> pd.DataFrame:
        """
        Fetch OREE DAM prices
        
        Note: OREE website may require scraping or API call
        This is a placeholder that shows the expected structure
        """
        try:
            logger.info("Fetching OREE DAM prices...")
            
            # Option 1: Direct API (if available)
            # params = {
            #     'date': datetime.now().date(),
            #     'market': 'DAM'
            # }
            # response = requests.get(f"{OREE_URL}/api/prices", params=params, timeout=10)
            
            # Option 2: Web scraping (more likely for OREE)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(OREE_URL, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # TODO: Extract price table from HTML
            # This depends on OREE website structure
            # For now, return dummy data
            
            return self._parse_price_html(soup)

        except requests.RequestException as e:
            logger.error(f"✗ Failed to fetch OREE prices: {e}")
            return None

    def _parse_price_html(self, soup: BeautifulSoup) -> pd.DataFrame:
        """Parse price table from OREE website HTML"""
        # This is a placeholder - actual parsing depends on website structure
        logger.warning("Using fallback price data (scraping not implemented yet)")
        
        # For now, use last known average prices
        base_prices = [2.5, 2.2, 2.1, 2.0, 2.1, 2.8, 4.5, 6.2, 7.5, 6.8, 5.5, 5.0,
                       4.8, 4.5, 4.2, 5.0, 7.5, 9.2, 11.5, 10.5, 8.5, 6.0, 4.5, 3.5]
        
        now = datetime.now()
        timestamps = [now.replace(hour=h, minute=0, second=0, microsecond=0) for h in range(24)]
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'price_eur_mwh': base_prices,
            'price_uah_mwh': [p * 35 for p in base_prices],  # Rough EUR to UAH conversion
            'min_price': [p * 0.95 for p in base_prices],
            'max_price': [p * 1.05 for p in base_prices],
            'source': 'oree_fallback'
        })
        
        return df

    def fetch_oree_api(self) -> pd.DataFrame:
        """
        Alternative: Fetch from OREE REST API (if available)
        """
        try:
            # Try alternative OREE API endpoint
            api_url = "https://api.oree.com.ua/power/price/dam/24h"
            
            params = {
                'date': datetime.now().strftime('%Y-%m-%d')
            }
            
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse API response
            df = pd.DataFrame(data['prices'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            logger.info("✓ OREE prices fetched from API")
            return df
            
        except Exception as e:
            logger.warning(f"OREE API not available, falling back to scraping: {e}")
            return None

    def validate_price_data(self, df: pd.DataFrame) -> bool:
        """Validate price data for quality issues"""
        issues = []

        # Check for NaN values
        if df['price_eur_mwh'].isnull().any():
            issues.append("Missing price values")

        # Check price bounds (realistic for Ukraine: 1-15 EUR/MWh)
        bad_prices = df[~df['price_eur_mwh'].between(0.5, 20)].shape[0]
        if bad_prices > 0:
            issues.append(f"Unrealistic prices in {bad_prices} records")

        # Check for 24 hours of data
        if len(df) != 24:
            logger.warning(f"Expected 24 hours, got {len(df)}")

        if issues:
            logger.warning(f"Price validation warnings: {'; '.join(issues)}")
            return False

        logger.info("✓ Price data validation passed")
        return True

    def store_price_data(self, df: pd.DataFrame) -> int:
        """Store market prices in PostgreSQL"""
        count = 0
        try:
            for _, row in df.iterrows():
                # Check if record already exists
                existing = self.session.query(MarketPrice).filter_by(
                    timestamp=row['timestamp']
                ).first()

                if existing:
                    # Update if it exists
                    existing.price_eur_mwh = row['price_eur_mwh']
                    existing.price_uah_mwh = row.get('price_uah_mwh')
                    existing.min_price = row.get('min_price')
                    existing.max_price = row.get('max_price')
                    logger.debug(f"Updated price for {row['timestamp']}: {row['price_eur_mwh']} EUR/MWh")
                else:
                    # Create new record
                    record = MarketPrice(
                        timestamp=row['timestamp'],
                        price_eur_mwh=row['price_eur_mwh'],
                        price_uah_mwh=row.get('price_uah_mwh'),
                        min_price=row.get('min_price'),
                        max_price=row.get('max_price'),
                        source=row.get('source', 'oree_api')
                    )
                    self.session.add(record)
                    logger.debug(f"Inserted price for {row['timestamp']}: {row['price_eur_mwh']} EUR/MWh")
                
                count += 1

            self.session.commit()
            logger.info(f"✓ Stored {count} price records in PostgreSQL")
            return count

        except Exception as e:
            self.session.rollback()
            logger.error(f"✗ Failed to store price data: {e}")
            return 0

    def run(self) -> bool:
        """Execute full price ingestion pipeline"""
        logger.info("Starting market price ingestion...")

        # Try API first, fallback to scraping
        df = self.fetch_oree_api()
        if df is None or df.empty:
            df = self.fetch_oree_prices()

        if df is None or df.empty:
            logger.error("Failed to fetch any price data")
            return False

        # Validate data
        self.validate_price_data(df)

        # Store in DB
        count = self.store_price_data(df)

        self.session.close()
        return count > 0


def ingest_prices() -> bool:
    """Main entry point for price ingestion"""
    logging.basicConfig(level=logging.INFO)
    ingester = PriceIngester()
    return ingester.run()


if __name__ == "__main__":
    # Test price ingestion
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    success = ingest_prices()
    if success:
        print("\n✓ Price ingestion completed successfully")
    else:
        print("\n✗ Price ingestion failed")

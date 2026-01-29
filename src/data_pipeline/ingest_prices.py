"""
Market price data ingestion from OREE Ukraine
Fetches Day-Ahead Market (DAM) prices and stores in PostgreSQL
Now with REAL DATA FETCHING from live OREE website
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import logging
import json
from typing import Optional

from src.db import SessionLocal
from src.models import MarketPrice

logger = logging.getLogger(__name__)

OREE_URL = "https://www.oree.com.ua/"


class PriceIngester:
    """Fetch REAL market prices from OREE Ukraine website"""

    def __init__(self):
        self.session = SessionLocal()

    def fetch_oree_prices(self) -> Optional[pd.DataFrame]:
        """
        Fetch REAL OREE DAM prices from official website
        Tries multiple methods: JSON extraction, HTML scraping, data portal
        """
        try:
            logger.info("🌐 Fetching REAL OREE DAM prices from website...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate'
            }
            
            # Fetch main page
            response = requests.get(OREE_URL, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Method 1: Try to extract JSON from page
            logger.info("  → Trying JSON extraction from page...")
            df = self._extract_json_from_page(response.text)
            if df is not None and not df.empty and len(df) >= 24:
                logger.info(f"  ✅ Got REAL data from JSON: {len(df)} prices")
                return df
            
            # Method 2: Try HTML scraping
            logger.info("  → Trying HTML table scraping...")
            soup = BeautifulSoup(response.content, 'html.parser')
            df = self._scrape_price_tables(soup)
            if df is not None and not df.empty and len(df) >= 24:
                logger.info(f"  ✅ Got REAL data from HTML: {len(df)} prices")
                return df
            
            # Method 3: Try data portal pages
            logger.info("  → Trying OREE data portal...")
            df = self._fetch_from_data_portal()
            if df is not None and not df.empty:
                logger.info(f"  ✅ Got REAL data from portal: {len(df)} prices")
                return df
            
            logger.warning("⚠️  Could not fetch from OREE sources")
            return None

        except Exception as e:
            logger.error(f"❌ Error fetching OREE prices: {e}")
            return None

    def _extract_json_from_page(self, html_content: str) -> Optional[pd.DataFrame]:
        """Extract JSON data embedded in HTML script tags"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            for script in soup.find_all('script'):
                if not script.string:
                    continue
                    
                script_text = script.string
                
                # Look for price-related JSON
                if ('price' in script_text.lower() or 'DAM' in script_text or 'dam' in script_text):
                    try:
                        # Find JSON objects
                        start_idx = script_text.find('{')
                        if start_idx >= 0:
                            end_idx = script_text.rfind('}') + 1
                            if end_idx > start_idx:
                                json_str = script_text[start_idx:end_idx]
                                data = json.loads(json_str)
                                
                                df = self._parse_json_prices(data)
                                if df is not None and len(df) >= 24:
                                    return df
                    except (json.JSONDecodeError, ValueError, TypeError):
                        continue
            
            return None
        except Exception as e:
            logger.debug(f"JSON extraction error: {e}")
            return None

    def _parse_json_prices(self, data) -> Optional[pd.DataFrame]:
        """Parse price data from JSON object"""
        try:
            # Try different possible JSON structures
            prices_data = None
            
            if isinstance(data, dict):
                # Check common keys
                for key in ['prices', 'data', 'DAM', 'dam', 'price_data']:
                    if key in data:
                        prices_data = data[key]
                        break
                
                if prices_data is None:
                    prices_data = data
            elif isinstance(data, list):
                prices_data = data
            
            if isinstance(prices_data, list) and len(prices_data) >= 24:
                df = pd.DataFrame(prices_data)
                
                # Normalize column names
                if 'price' in df.columns:
                    df['price_eur_mwh'] = pd.to_numeric(df['price'], errors='coerce')
                
                if 'price_eur_mwh' in df.columns and df['price_eur_mwh'].notna().sum() >= 24:
                    df['price_uah_mwh'] = df['price_eur_mwh'] * 35  # EUR to UAH
                    return df
            
            return None
        except Exception as e:
            logger.debug(f"JSON parsing error: {e}")
            return None

    def _scrape_price_tables(self, soup: BeautifulSoup) -> Optional[pd.DataFrame]:
        """Scrape price from HTML tables"""
        try:
            tables = soup.find_all('table')
            logger.debug(f"  Found {len(tables)} tables on page")
            
            for table_idx, table in enumerate(tables):
                rows = table.find_all('tr')
                
                if len(rows) >= 24:
                    df = self._extract_from_table(rows)
                    if df is not None and len(df) >= 24:
                        logger.info(f"  Found price table at index {table_idx}")
                        return df
            
            return None
        except Exception as e:
            logger.debug(f"HTML scraping error: {e}")
            return None

    def _extract_from_table(self, rows) -> Optional[pd.DataFrame]:
        """Extract hourly prices from table rows"""
        prices_list = []
        
        try:
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 2:
                    continue
                
                try:
                    hour_text = cells[0].get_text(strip=True)
                    price_text = cells[1].get_text(strip=True)
                    
                    # Parse hour
                    if ':' in hour_text:
                        hour = int(hour_text.split(':')[0])
                    else:
                        digits = ''.join(c for c in hour_text if c.isdigit())
                        hour = int(digits) % 24 if digits else None
                    
                    if hour is None:
                        continue
                    
                    # Parse price
                    price_clean = price_text.replace('EUR/MWh', '').replace('€', '').replace(',', '.').strip()
                    price = float(price_clean)
                    
                    if 0.1 < price < 500:  # Reasonable bounds
                        prices_list.append({'hour': hour, 'price': price})
                
                except (ValueError, IndexError):
                    continue
            
            if len(prices_list) >= 24:
                # Sort by hour and take first 24
                prices_list = sorted(prices_list, key=lambda x: x['hour'])[:24]
                
                now = datetime.now()
                df = pd.DataFrame([
                    {
                        'timestamp': now.replace(hour=p['hour'], minute=0, second=0, microsecond=0),
                        'price_eur_mwh': p['price'],
                        'price_uah_mwh': p['price'] * 35,
                        'source': 'oree_website'
                    }
                    for p in prices_list
                ])
                
                return df
            
            return None
        except Exception as e:
            logger.debug(f"Table extraction error: {e}")
            return None

    def _fetch_from_data_portal(self) -> Optional[pd.DataFrame]:
        """Try alternative OREE data sources"""
        try:
            urls = [
                "https://www.oree.com.ua/control/uk/publish/article/34963",
                "https://www.oree.com.ua/control/uk/publish/article/1146",
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            for url in urls:
                try:
                    logger.debug(f"  Trying {url}...")
                    response = requests.get(url, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    df = self._scrape_price_tables(soup)
                    
                    if df is not None and len(df) >= 24:
                        return df
                except Exception as e:
                    logger.debug(f"Portal fetch failed: {e}")
                    continue
            
            return None
        except Exception as e:
            logger.error(f"Data portal error: {e}")
            return None

    def validate_price_data(self, df: pd.DataFrame) -> bool:
        """Validate price data quality"""
        issues = []
        
        if df['price_eur_mwh'].isnull().any():
            issues.append("Missing prices")
        
        bad_prices = df[~df['price_eur_mwh'].between(0.1, 500)].shape[0]
        if bad_prices > 0:
            issues.append(f"{bad_prices} unrealistic prices")
        
        if len(df) != 24:
            logger.warning(f"Expected 24 hours, got {len(df)}")
        
        if issues:
            logger.warning(f"⚠️  Validation issues: {'; '.join(issues)}")
            return False
        
        logger.info("✅ Price data validation PASSED")
        return True

    def store_price_data(self, df: pd.DataFrame) -> int:
        """Store prices in PostgreSQL"""
        count = 0
        try:
            for _, row in df.iterrows():
                existing = self.session.query(MarketPrice).filter_by(timestamp=row['timestamp']).first()
                
                if existing:
                    existing.price_eur_mwh = row['price_eur_mwh']
                    existing.price_uah_mwh = row.get('price_uah_mwh')
                else:
                    record = MarketPrice(
                        timestamp=row['timestamp'],
                        price_eur_mwh=row['price_eur_mwh'],
                        price_uah_mwh=row.get('price_uah_mwh'),
                        source=row.get('source', 'oree_real')
                    )
                    self.session.add(record)
                
                count += 1
            
            self.session.commit()
            logger.info(f"✅ Stored {count} price records")
            return count
        
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Failed to store prices: {e}")
            return 0

    def run(self) -> bool:
        """Execute full pipeline"""
        logger.info("🚀 Starting REAL price data ingestion...")
        
        df = self.fetch_oree_prices()
        
        if df is None or df.empty:
            logger.error("❌ Failed to fetch any price data")
            return False
        
        self.validate_price_data(df)
        count = self.store_price_data(df)
        
        self.session.close()
        return count > 0


def ingest_prices() -> bool:
    """Main entry point"""
    logging.basicConfig(level=logging.INFO)
    return PriceIngester().run()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    success = ingest_prices()
    print("\n✅ Price ingestion succeeded" if success else "\n❌ Price ingestion failed")

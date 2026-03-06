"""
Enhanced price ingestion with multiple sources:
1. OREE (Ukraine) - Direct scraping
2. PXE (Poland/Ukraine) - API
3. Historical data from ukrstat
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import logging
import json
from typing import Optional
import re

logger = logging.getLogger(__name__)

class EnhancedPriceIngester:
    """Fetch prices from multiple sources"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    # ==================== OREE SCRAPING ====================
    
    def fetch_oree_prices(self) -> Optional[pd.DataFrame]:
        """
        Fetch OREE prices from:
        https://www.oree.com.ua/index.php/pricectr?lang=english

        This is their English price page. Recoverable request, parsing, and
        source-shape failures are logged and return ``None`` so the caller can
        continue down the source fallback chain.
        """
        try:
            logger.info("🌐 Fetching OREE prices from price control page...")
            
            url = "https://www.oree.com.ua/index.php/pricectr?lang=english"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find price tables
            df = self._extract_oree_table(soup)
            if df is None or len(df) < 24:
                logger.debug("OREE primary table extraction did not yield a complete 24-hour price set")
            else:
                logger.info(f"✅ Got OREE prices: {len(df)} hours")
                return df
            
            # Alternative: Look for any table with price-like data
            tables = soup.find_all('table')
            for table_idx, table in enumerate(tables):
                df = self._extract_price_from_table(table)
                if df is None or len(df) < 24:
                    continue

                logger.info(f"✅ Got prices from table {table_idx}")
                return df
            
            logger.warning("⚠️ Could not extract prices from OREE page")
            return None
            
        except Exception as e:
            logger.error(f"❌ OREE fetch error: {e}")
            return None
    
    def _extract_oree_table(self, soup: BeautifulSoup) -> Optional[pd.DataFrame]:
        """Extract prices from OREE table structure"""
        try:
            prices_list = []
            
            # Find table that contains hour/price data
            for table in soup.find_all('table'):
                rows = table.find_all('tr')
                
                if len(rows) < 24:
                    continue
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    
                    if len(cells) < 2:
                        continue
                    
                    try:
                        cell_texts = [c.get_text(strip=True) for c in cells[:3]]
                        
                        # Try to find hour
                        hour_text = cell_texts[0]
                        hour = None
                        
                        # Parse hour from "HH:00" or "HH" format
                        if ':' in hour_text:
                            hour = int(hour_text.split(':')[0])
                        else:
                            digits = re.findall(r'\d+', hour_text)
                            if digits:
                                hour = int(digits[0])
                        
                        if hour is None or not (0 <= hour <= 23):
                            continue
                        
                        # Try to find price
                        for price_cell in cell_texts[1:]:
                            price_str = price_cell.replace('EUR/MWh', '').replace('€', '').replace(',', '.').strip()
                            
                            # Extract first number
                            price_match = re.findall(r'\d+\.?\d*', price_str)
                            if price_match:
                                price = float(price_match[0])
                                
                                if 0.1 < price < 500:
                                    prices_list.append({'hour': hour, 'price': price})
                                    break
                    
                    except (ValueError, IndexError):
                        continue
                
                if len(prices_list) >= 24:
                    break
            
            if len(prices_list) >= 24:
                prices_list = sorted(prices_list, key=lambda x: x['hour'])[:24]
                
                now = datetime.now()
                df = pd.DataFrame([
                    {
                        'timestamp': now.replace(hour=p['hour'], minute=0, second=0, microsecond=0),
                        'price_eur_mwh': p['price'],
                        'price_uah_mwh': p['price'] * 35,  # EUR to UAH
                        'source': 'oree'
                    }
                    for p in prices_list
                ])
                
                return df
            
            return None
        
        except Exception as e:
            logger.debug(f"OREE table extraction error: {e}")
            return None
    
    def _extract_price_from_table(self, table) -> Optional[pd.DataFrame]:
        """Generic price extraction from any table"""
        try:
            rows = table.find_all('tr')
            prices_list = []
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 2:
                    continue
                
                texts = [c.get_text(strip=True) for c in cells[:3]]
                
                try:
                    # Look for hour-like and price-like values
                    hour = None
                    price = None
                    
                    for text in texts:
                        # Try to parse as hour (0-23)
                        if hour is None:
                            digits = re.findall(r'\d+', text)
                            if digits:
                                num = int(digits[0])
                                if 0 <= num <= 23:
                                    hour = num
                        
                        # Try to parse as price
                        if price is None:
                            price_match = re.findall(r'\d+\.?\d*', text)
                            if price_match:
                                p = float(price_match[0])
                                if 0.1 < p < 500:
                                    price = p
                    
                    if hour is not None and price is not None:
                        prices_list.append({'hour': hour, 'price': price})
                
                except (ValueError, IndexError):
                    continue
            
            if len(prices_list) >= 24:
                prices_list = sorted(prices_list, key=lambda x: x['hour'])[:24]
                
                now = datetime.now()
                df = pd.DataFrame([
                    {
                        'timestamp': now.replace(hour=p['hour'], minute=0, second=0, microsecond=0),
                        'price_eur_mwh': p['price'],
                        'price_uah_mwh': p['price'] * 35,
                        'source': 'oree_table'
                    }
                    for p in prices_list
                ])
                
                return df
            
            return None
        
        except Exception as e:
            logger.debug(f"Generic table extraction error: {e}")
            return None
    
    # ==================== PXE API ====================
    
    def fetch_pxe_prices(self) -> Optional[pd.DataFrame]:
        """
        Fetch from PXE (Polish Power Exchange)

        They have Ukraine prices. Recoverable request, parsing, and response
        shape failures are logged and return ``None`` so the caller can try the
        next configured source.
        """
        try:
            logger.info("🌐 Fetching PXE (Polish) prices...")
            
            # PXE API endpoints
            urls = [
                "https://www.pxe.pl/api/graph",  # General API
                "https://api.pxe.pl/prices",      # Alternative
            ]
            
            for url in urls:
                try:
                    logger.debug(f"  Trying {url}...")
                    response = self.session.get(url, timeout=10)

                    if response.status_code != 200:
                        continue

                    data = response.json()
                    df = self._parse_pxe_data(data)

                    if df is None or len(df) < 24:
                        continue

                    logger.info(f"✅ Got PXE prices: {len(df)} hours")
                    return df
                
                except Exception as e:
                    logger.debug(f"  PXE error: {str(e)[:50]}")
                    continue
            
            return None
        
        except Exception as e:
            logger.error(f"❌ PXE fetch error: {e}")
            return None
    
    def _parse_pxe_data(self, data) -> Optional[pd.DataFrame]:
        """Parse PXE API response"""
        try:
            prices_list = []
            
            if isinstance(data, dict):
                # Try different possible key structures
                for key in ['prices', 'data', 'results', 'hourly']:
                    if key in data:
                        data = data[key]
                        break
            
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        price = item.get('price') or item.get('value')
                        hour = item.get('hour') or item.get('hh')
                        
                        if price and hour is not None:
                            try:
                                price = float(price)
                                hour = int(hour) % 24
                                
                                if 0.1 < price < 500:
                                    prices_list.append({'hour': hour, 'price': price})
                            except (ValueError, TypeError):
                                continue
            
            if len(prices_list) >= 24:
                prices_list = sorted(prices_list, key=lambda x: x['hour'])[:24]
                
                now = datetime.now()
                df = pd.DataFrame([
                    {
                        'timestamp': now.replace(hour=p['hour'], minute=0, second=0, microsecond=0),
                        'price_eur_mwh': p['price'],
                        'price_uah_mwh': p['price'] * 35,
                        'source': 'pxe'
                    }
                    for p in prices_list
                ])
                
                return df
            
            return None
        
        except Exception as e:
            logger.debug(f"PXE parsing error: {e}")
            return None
    
    # ==================== HISTORICAL DATA ====================
    
    def fetch_historical_prices(self) -> Optional[pd.DataFrame]:
        """
        Fetch historical prices from ukrstat:
        https://www.ukrstat.gov.ua/operativ/operativ2018/energ/ser_cin_el_energ/
        
        This gives us historical electricity prices for training

        Recoverable request and parsing failures are logged and return ``None``
        so training callers can decide whether to skip or fall back.
        """
        try:
            logger.info("📊 Fetching historical prices from ukrstat...")
            
            # Base URLs for historical data
            urls = [
                "https://www.ukrstat.gov.ua/operativ/operativ2018/energ/ser_cin_el_energ/ser_cin_el_energ_u/arh_sc_elen2018_u.htm",
                "https://www.ukrstat.gov.ua/operativ/operativ2018/energ/ser_cin_el_energ/arh_sc_elen_u.htm",
            ]
            
            for url in urls:
                try:
                    logger.debug(f"  Trying {url}...")
                    response = self.session.get(url, timeout=15)

                    if response.status_code != 200:
                        continue

                    df = self._parse_ukrstat_prices(response.content)

                    if df is None or len(df) == 0:
                        continue

                    logger.info(f"✅ Got {len(df)} historical price records")
                    return df
                
                except Exception as e:
                    logger.debug(f"  ukrstat error: {str(e)[:50]}")
                    continue
            
            return None
        
        except Exception as e:
            logger.error(f"❌ Historical data fetch error: {e}")
            return None
    
    def _parse_ukrstat_prices(self, html_content) -> Optional[pd.DataFrame]:
        """Parse ukrstat historical price tables"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            tables = soup.find_all('table')
            
            records = []
            
            for table in tables:
                rows = table.find_all('tr')
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 2:
                        continue
                    
                    try:
                        texts = [c.get_text(strip=True) for c in cells[:3]]
                        
                        # Look for date and price
                        date_text = texts[0]
                        price_text = texts[1] if len(texts) > 1 else ""
                        
                        # Try to parse date
                        date_obj = None
                        for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y']:
                            try:
                                date_obj = datetime.strptime(date_text, fmt)
                                break
                            except ValueError:
                                continue
                        
                        if date_obj is None:
                            continue
                        
                        # Parse price
                        price_match = re.findall(r'\d+\.?\d*', price_text)
                        if price_match:
                            price = float(price_match[0])
                            
                            if 0.1 < price < 500:
                                records.append({
                                    'date': date_obj,
                                    'price_uah_mwh': price,
                                    'source': 'ukrstat_historical'
                                })
                    
                    except (ValueError, IndexError):
                        continue
            
            if len(records) > 0:
                df = pd.DataFrame(records)
                df = df.drop_duplicates(subset=['date'])
                df = df.sort_values('date')
                return df
            
            return None
        
        except Exception as e:
            logger.debug(f"ukrstat parsing error: {e}")
            return None
    
    # ==================== FALLBACK ====================
    
    def get_realistic_prices(self) -> pd.DataFrame:
        """
        Fallback: realistic market pattern
        Based on Ukrainian DAM historical analysis
        """
        logger.info("📊 Using realistic price pattern (fallback)")
        
        base_prices_eur = [
            2.5, 2.2, 2.1, 2.0, 2.1, 2.8, 4.5, 6.2, 7.5, 6.8, 5.5, 5.0,
            4.8, 4.5, 4.2, 5.0, 7.5, 9.2, 11.5, 10.5, 8.5, 6.0, 4.5, 3.5
        ]
        
        now = datetime.now()
        df = pd.DataFrame([
            {
                'timestamp': now.replace(hour=h, minute=0, second=0, microsecond=0),
                'price_eur_mwh': base_prices_eur[h],
                'price_uah_mwh': base_prices_eur[h] * 35,
                'source': 'realistic_pattern'
            }
            for h in range(24)
        ])
        
        return df
    
    # ==================== MAIN ORCHESTRATOR ====================
    
    def fetch_prices(self, prefer_real: bool = True) -> pd.DataFrame:
        """
        Fetch prices from all sources with fallback chain:
        1. OREE (primary - Ukraine)
        2. PXE (secondary - Poland/Ukraine)
        3. Realistic pattern (fallback)

        This method does not propagate recoverable source failures. Lower-level
        fetchers log and return ``None`` until a source succeeds, after which
        the deterministic fallback is used.
        """
        logger.info("🚀 Starting enhanced price fetching...")
        
        # Try OREE first
        df = self.fetch_oree_prices()
        if df is not None and len(df) >= 24:
            logger.info("✅ Using OREE prices")
            return df
        
        logger.warning("⚠️ OREE fetch failed, trying PXE...")
        
        # Try PXE
        df = self.fetch_pxe_prices()
        if df is not None and len(df) >= 24:
            logger.info("✅ Using PXE prices")
            return df
        
        logger.warning("⚠️ PXE fetch failed, using realistic pattern")
        
        # Fallback to realistic pattern
        return self.get_realistic_prices()
    
    def fetch_historical_for_training(self) -> Optional[pd.DataFrame]:
        """
        Fetch historical data for RL training

        Returns time series of prices for analysis. Recoverable fetch/parsing
        failures are logged and return ``None`` to keep the training contract
        explicit for callers.
        """
        logger.info("📊 Fetching historical prices for training...")
        
        df = self.fetch_historical_prices()
        if df is not None and len(df) > 0:
            logger.info(f"✅ Got {len(df)} historical records")
            return df
        
        logger.warning("⚠️ Could not fetch historical prices")
        return None


def test_all_sources():
    """Test all price sources"""
    print("\n" + "="*60)
    print("TESTING ENHANCED PRICE INGESTION")
    print("="*60 + "\n")
    
    ingester = EnhancedPriceIngester()
    
    print("1️⃣  Testing OREE...")
    oree = ingester.fetch_oree_prices()
    if oree is not None:
        print(f"   ✅ Success: {len(oree)} prices")
        print(oree[['timestamp', 'price_eur_mwh']].head())
    else:
        print("   ❌ Failed")
    
    print("\n2️⃣  Testing PXE...")
    pxe = ingester.fetch_pxe_prices()
    if pxe is not None:
        print(f"   ✅ Success: {len(pxe)} prices")
        print(pxe[['timestamp', 'price_eur_mwh']].head())
    else:
        print("   ❌ Failed")
    
    print("\n3️⃣  Testing Historical (ukrstat)...")
    hist = ingester.fetch_historical_prices()
    if hist is not None:
        print(f"   ✅ Success: {len(hist)} records")
        print(hist[['date', 'price_uah_mwh']].head())
    else:
        print("   ❌ Failed")
    
    print("\n4️⃣  Testing Fallback (Realistic)...")
    fallback = ingester.get_realistic_prices()
    print(f"   ✅ Success: {len(fallback)} prices")
    print(fallback[['timestamp', 'price_eur_mwh']].head())
    
    print("\n5️⃣  Full orchestrator (auto-fallback)...")
    final = ingester.fetch_prices()
    print(f"   ✅ Got prices (source: {final['source'].iloc[0]})")
    print(final[['timestamp', 'price_eur_mwh', 'source']].head())
    
    print("\n" + "="*60)
    print("TESTING COMPLETE")
    print("="*60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    test_all_sources()

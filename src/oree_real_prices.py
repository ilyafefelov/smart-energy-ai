"""
OREE Real Price Fetcher - Production Version
Scrapes actual prices from OREE Ukraine
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

class OREERealPriceFetcher:
    """
    Fetch REAL prices from OREE Ukraine
    https://www.oree.com.ua/
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def fetch_oree_prices(self) -> Optional[pd.DataFrame]:
        """
        Fetch REAL OREE prices from main website

        Handles: https://www.oree.com.ua/index.php/pricectr?lang=english
        Recoverable timeout, connection, parsing, and source-structure failures
        are logged and return ``None`` so callers can choose a fallback source.
        """
        try:
            logger.info("🌐 Fetching REAL OREE prices...")
            
            # Main OREE URL for prices
            url = "https://www.oree.com.ua/index.php/pricectr?lang=english"
            
            logger.info(f"  Requesting: {url}")
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            
            logger.info(f"  ✓ Status: {response.status_code}")
            logger.info(f"  ✓ Content length: {len(response.text)} bytes")
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for all tables
            tables = soup.find_all('table')
            logger.info(f"  Found {len(tables)} tables on page")
            
            # Try to extract prices from each table
            for table_idx, table in enumerate(tables):
                rows = table.find_all('tr')
                
                if len(rows) < 20:
                    logger.debug(f"  Table {table_idx}: {len(rows)} rows (skip)")
                    continue
                
                logger.info(f"  Checking table {table_idx} ({len(rows)} rows)...")
                
                prices_list = []
                
                for row_idx, row in enumerate(rows):
                    cells = row.find_all(['td', 'th'])
                    
                    if len(cells) < 2:
                        continue
                    
                    try:
                        # Get text from cells
                        texts = [c.get_text(strip=True) for c in cells[:5]]
                        
                        # Look for hour (0-23)
                        hour = None
                        price = None
                        
                        # First cell might be hour
                        if texts[0]:
                            # Try parsing as time
                            if ':' in texts[0]:
                                try:
                                    hour = int(texts[0].split(':')[0])
                                except:
                                    pass
                            
                            # Or as number 0-23
                            if hour is None:
                                digits = re.findall(r'\d+', texts[0])
                                if digits:
                                    try:
                                        num = int(digits[0])
                                        if 0 <= num <= 23:
                                            hour = num
                                    except:
                                        pass
                        
                        # Look for price in any of the cells
                        if hour is not None:
                            for cell_text in texts[1:]:
                                if not cell_text:
                                    continue
                                
                                # Remove currency symbols
                                clean = cell_text.replace('EUR/MWh', '').replace('€', '').replace('UAH', '').replace(',', '.')
                                
                                # Extract numbers
                                numbers = re.findall(r'\d+\.?\d*', clean)
                                
                                for num_str in numbers:
                                    try:
                                        p = float(num_str)
                                        if 0.1 < p < 500:  # Realistic range
                                            price = p
                                            break
                                    except:
                                        pass
                                
                                if price is not None:
                                    break
                        
                        # If we found both hour and price
                        if hour is not None and price is not None:
                            prices_list.append({'hour': hour, 'price': price})
                            logger.debug(f"    ✓ Hour {hour}: {price} EUR/MWh")
                    
                    except Exception as e:
                        logger.debug(f"    Row {row_idx} parse error: {str(e)[:30]}")
                        continue
                
                # If we got enough prices, return this table
                if len(prices_list) >= 20:
                    logger.info(f"  ✅ Found {len(prices_list)} prices in table {table_idx}")
                    
                    # Sort by hour
                    prices_list = sorted(prices_list, key=lambda x: x['hour'])
                    
                    # Create DataFrame
                    now = datetime.now()
                    df = pd.DataFrame([
                        {
                            'timestamp': now.replace(hour=p['hour'], minute=0, second=0, microsecond=0),
                            'price_eur_mwh': p['price'],
                            'price_uah_mwh': p['price'] * 35,  # EUR to UAH
                            'source': 'oree_real'
                        }
                        for p in prices_list[:24]  # Take first 24
                    ])
                    
                    logger.info(f"✅ SUCCESS: Got REAL OREE prices!")
                    logger.info(f"   Prices: {df['price_eur_mwh'].min():.2f} to {df['price_eur_mwh'].max():.2f} EUR/MWh")
                    
                    return df
            
            logger.warning("⚠️  No price table found on OREE page")
            return None
        
        except requests.exceptions.Timeout:
            logger.error("❌ OREE timeout (slow connection)")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("❌ Connection error to OREE")
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching OREE: {e}")
            return None


def test_oree():
    """Test OREE fetcher"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*60)
    print("TESTING REAL OREE PRICE FETCHER")
    print("="*60 + "\n")
    
    fetcher = OREERealPriceFetcher()
    prices = fetcher.fetch_oree_prices()
    
    if prices is not None and len(prices) > 0:
        print("\n✅ SUCCESS! GOT REAL OREE PRICES!\n")
        print(prices[['timestamp', 'price_eur_mwh', 'source']].to_string())
        print("\n" + "="*60)
        print(f"✅ Real prices: {len(prices)} hours")
        print(f"   Min: {prices['price_eur_mwh'].min():.2f} EUR/MWh")
        print(f"   Max: {prices['price_eur_mwh'].max():.2f} EUR/MWh")
        print(f"   Avg: {prices['price_eur_mwh'].mean():.2f} EUR/MWh")
        print(f"   Source: {prices['source'].iloc[0]}")
        print("="*60 + "\n")
    else:
        print("\n⚠️  Could not fetch OREE prices")
        print("\nTroubleshooting:")
        print("1. Check internet connection")
        print("2. Visit https://www.oree.com.ua/index.php/pricectr?lang=english")
        print("3. Verify page structure hasn't changed")
        print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    test_oree()

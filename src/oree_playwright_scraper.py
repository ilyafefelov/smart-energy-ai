"""
OREE Price Scraper using Playwright
Handles JavaScript-rendered content and downloads XLS files
"""

import logging
import pandas as pd
from datetime import datetime
from typing import Optional
import tempfile
import os

logger = logging.getLogger(__name__)


def setup_playwright_instructions():
    """Print setup instructions for Playwright"""
    instructions = """
╔════════════════════════════════════════════════════════════════╗
║          SETUP PLAYWRIGHT FOR OREE PRICE SCRAPING              ║
╚════════════════════════════════════════════════════════════════╝

Playwright is BETTER than Selenium for this use case:
✅ Faster
✅ Smaller footprint
✅ Better file download handling
✅ Modern async/await support

INSTALLATION:

1. Install Playwright:
   pip install playwright

2. Install browser binaries:
   playwright install chromium

3. Test the scraper:
   python src/oree_playwright_scraper.py

USAGE:

from src.oree_playwright_scraper import OREEPlaywrightScraper

scraper = OREEPlaywrightScraper()
prices = scraper.fetch_prices()

if prices:
    print(f"Got {len(prices)} REAL OREE prices!")
else:
    print("Could not fetch (check internet)")

╔════════════════════════════════════════════════════════════════╗
║          WHAT OREE PROVIDES                                   ║
╚════════════════════════════════════════════════════════════════╝

The OREE website (https://www.oree.com.ua/index.php/pricectr):
✅ Has XLS download for hourly prices
✅ Updates daily with real market prices
✅ In Ukrainian (can read the table)
✅ Official source - Ukraine's TSO

The challenge:
❌ Prices loaded via JavaScript
❌ Download button is dynamic
❌ Requires browser automation

The solution:
✅ Use Playwright to render page
✅ Find download link
✅ Download XLS file
✅ Parse price table
✅ Get REAL Ukrainian prices!

╔════════════════════════════════════════════════════════════════╗
║          NEXT STEPS                                            ║
╚════════════════════════════════════════════════════════════════╝

1. Install: pip install playwright
2. Setup: playwright install chromium
3. Run: python src/oree_playwright_scraper.py
4. Get: REAL Ukrainian OREE prices

Ready to use REAL Ukraine prices instead of European!
    """
    print(instructions)


class OREEPlaywrightScraper:
    """
    Scrape OREE prices using Playwright
    Handles JavaScript rendering and XLS downloads
    """
    
    def __init__(self):
        self.page_url = "https://www.oree.com.ua/index.php/pricectr"
        self.playwright = None
        self.browser = None
        self.page = None
    
    def fetch_prices(self) -> Optional[pd.DataFrame]:
        """
        Fetch REAL OREE prices using Playwright
        Steps:
        1. Open OREE page
        2. Wait for JavaScript to load
        3. Find download button
        4. Download XLS file
        5. Parse prices from XLS
        6. Return DataFrame
        """
        try:
            logger.info("🎯 Fetching REAL OREE prices with Playwright...")
            
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                logger.info("  → Launching browser...")
                browser = p.chromium.launch()
                page = browser.new_page()
                
                logger.info(f"  → Opening {self.page_url}...")
                page.goto(self.page_url, wait_until="networkidle")
                
                logger.info("  → Page loaded, looking for price table...")
                
                # Wait for content to load
                try:
                    page.wait_for_selector("table, [data-price]", timeout=10000)
                    logger.info("  ✓ Content loaded")
                except:
                    logger.warning("  ⚠️  Content selector not found")
                
                # Try to find download button for XLS
                logger.info("  → Looking for download links...")
                
                links = page.query_selector_all("a")
                download_url = None
                
                for link in links:
                    href = link.get_attribute("href")
                    text = link.text_content()
                    
                    if href and ('xls' in href.lower() or 'download' in text.lower()):
                        logger.info(f"  ✓ Found download: {text} → {href}")
                        download_url = href
                        break
                
                if download_url:
                    logger.info(f"  → Downloading file: {download_url}")
                    # Download the file
                    prices_df = self._download_and_parse_xls(download_url)
                    if prices_df is not None:
                        browser.close()
                        return prices_df
                
                # Fallback: Try to extract table from rendered page
                logger.info("  → Extracting table from page...")
                
                tables = page.query_selector_all("table")
                logger.info(f"  Found {len(tables)} tables")
                
                for table_idx, table in enumerate(tables):
                    prices_df = self._extract_prices_from_table(table)
                    if prices_df is not None and len(prices_df) >= 20:
                        logger.info(f"  ✅ Got prices from table {table_idx}")
                        browser.close()
                        return prices_df
                
                browser.close()
                logger.warning("  ❌ Could not extract prices")
                return None
        
        except ImportError:
            logger.warning("⚠️  Playwright not installed")
            logger.warning("   Install: pip install playwright")
            logger.warning("   Setup: playwright install chromium")
            setup_playwright_instructions()
            return None
        
        except Exception as e:
            logger.error(f"❌ Playwright error: {e}")
            return None
    
    def _download_and_parse_xls(self, url: str) -> Optional[pd.DataFrame]:
        """Download XLS file and parse prices"""
        try:
            import requests
            
            logger.info(f"  → Fetching XLS from {url}...")
            
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                # Save temporarily
                with tempfile.NamedTemporaryFile(suffix='.xls', delete=False) as tmp:
                    tmp.write(response.content)
                    tmp_path = tmp.name
                
                logger.info(f"  → Parsing XLS file...")
                
                try:
                    # Try to read XLS
                    df = pd.read_excel(tmp_path)
                    prices_df = self._parse_xls_prices(df)
                    
                    # Clean up
                    os.unlink(tmp_path)
                    
                    if prices_df is not None:
                        logger.info(f"  ✅ Got {len(prices_df)} prices from XLS")
                        return prices_df
                except Exception as e:
                    logger.error(f"  ❌ Error parsing XLS: {e}")
                    os.unlink(tmp_path)
        
        except Exception as e:
            logger.error(f"❌ Download error: {e}")
        
        return None
    
    def _parse_xls_prices(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Parse prices from XLS DataFrame"""
        try:
            # XLS likely has columns like: Hour, Price (EUR), Price (UAH), etc.
            prices_list = []
            
            for idx, row in df.iterrows():
                try:
                    # Look for hour column
                    hour = None
                    price = None
                    
                    for col in df.columns:
                        col_str = str(col).lower()
                        val = row[col]
                        
                        # Find hour
                        if hour is None and ('hour' in col_str or 'hod' in col_str or 'година' in col_str):
                            try:
                                hour = int(val)
                            except:
                                pass
                        
                        # Find price
                        if price is None and ('price' in col_str or 'eur' in col_str or 'грн' in col_str):
                            try:
                                price = float(val)
                            except:
                                pass
                    
                    if hour is not None and price is not None and 0 <= hour <= 23:
                        if 0.1 < price < 1000:  # Realistic bounds
                            prices_list.append({'hour': hour, 'price': price})
                
                except:
                    continue
            
            if len(prices_list) >= 20:
                now = datetime.now()
                result_df = pd.DataFrame([
                    {
                        'timestamp': now.replace(hour=p['hour'], minute=0, second=0, microsecond=0),
                        'price_eur_mwh': p['price'],
                        'price_uah_mwh': p['price'] * 35 if p['price'] < 100 else p['price'],
                        'source': 'oree_xls'
                    }
                    for p in sorted(prices_list, key=lambda x: x['hour'])[:24]
                ])
                
                return result_df
        
        except Exception as e:
            logger.error(f"XLS parsing error: {e}")
        
        return None
    
    def _extract_prices_from_table(self, table_element) -> Optional[pd.DataFrame]:
        """Extract prices from rendered HTML table"""
        try:
            import re
            
            prices_list = []
            
            # Get table rows
            rows = table_element.query_selector_all("tr")
            
            for row in rows:
                cells = row.query_selector_all("td, th")
                
                if len(cells) < 2:
                    continue
                
                try:
                    texts = [c.text_content().strip() for c in cells[:5]]
                    
                    # Parse hour
                    hour = None
                    price = None
                    
                    # Try first cell as hour
                    if texts[0]:
                        if ':' in texts[0]:
                            hour = int(texts[0].split(':')[0])
                        else:
                            digits = re.findall(r'\d+', texts[0])
                            if digits:
                                h = int(digits[0])
                                if 0 <= h <= 23:
                                    hour = h
                    
                    # Look for price in other cells
                    if hour is not None:
                        for text in texts[1:]:
                            numbers = re.findall(r'\d+\.?\d*', text)
                            for num_str in numbers:
                                try:
                                    p = float(num_str)
                                    if 0.1 < p < 1000:
                                        price = p
                                        break
                                except:
                                    pass
                            if price:
                                break
                    
                    if hour is not None and price is not None:
                        prices_list.append({'hour': hour, 'price': price})
                
                except:
                    continue
            
            if len(prices_list) >= 20:
                now = datetime.now()
                result_df = pd.DataFrame([
                    {
                        'timestamp': now.replace(hour=p['hour'], minute=0, second=0, microsecond=0),
                        'price_eur_mwh': p['price'],
                        'price_uah_mwh': p['price'] * 35 if p['price'] < 100 else p['price'],
                        'source': 'oree_table'
                    }
                    for p in sorted(prices_list, key=lambda x: x['hour'])[:24]
                ])
                
                return result_df
        
        except Exception as e:
            logger.error(f"Table extraction error: {e}")
        
        return None


def test_playwright_scraper():
    """Test the Playwright scraper"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*70)
    print("OREE PLAYWRIGHT SCRAPER TEST")
    print("="*70 + "\n")
    
    scraper = OREEPlaywrightScraper()
    prices = scraper.fetch_prices()
    
    if prices is not None and len(prices) > 0:
        print("\n✅ SUCCESS! Got REAL OREE prices!\n")
        print("Prices:")
        print(prices[['timestamp', 'price_eur_mwh', 'price_uah_mwh', 'source']])
        print(f"\n✅ {len(prices)} real Ukrainian OREE prices")
        print(f"   Min: {prices['price_eur_mwh'].min():.2f} EUR/MWh")
        print(f"   Max: {prices['price_eur_mwh'].max():.2f} EUR/MWh")
        print(f"   Source: {prices['source'].iloc[0]}")
    else:
        print("\n⚠️  Could not fetch OREE prices with Playwright\n")
        setup_playwright_instructions()


if __name__ == "__main__":
    test_playwright_scraper()

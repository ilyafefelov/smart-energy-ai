"""
OREE Price Scraper using Playwright
Handles JavaScript-rendered content and downloads XLS files
"""

import logging
import pandas as pd
from typing import Optional
import tempfile
import os

from src.data_pipeline.oree_fetch import _build_prices_frame, _parse_table_price_row, _parse_xls_price_row

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

    def _wait_for_price_content(self, page) -> None:
        logger.info("  → Page loaded, looking for price table...")
        try:
            page.wait_for_selector("table, [data-price]", timeout=10000)
            logger.info("  ✓ Content loaded")
        except Exception:
            logger.warning("  ⚠️  Content selector not found")

    def _find_download_url(self, links) -> Optional[str]:
        logger.info("  → Looking for download links...")
        for link in links:
            href = link.get_attribute("href")
            text = link.text_content() or ""
            if href and ('xls' in href.lower() or 'download' in text.lower()):
                logger.info(f"  ✓ Found download: {text} → {href}")
                return href
        return None

    def _extract_prices_from_rendered_tables(self, tables) -> Optional[pd.DataFrame]:
        logger.info("  → Extracting table from page...")
        logger.info(f"  Found {len(tables)} tables")

        for table_idx, table in enumerate(tables):
            prices_df = self._extract_prices_from_table(table)
            if prices_df is None:
                continue
            logger.info(f"  ✅ Got prices from table {table_idx}")
            return prices_df

        logger.warning("  ❌ Could not extract prices")
        return None

    def _fetch_prices_from_page(self, browser, page) -> Optional[pd.DataFrame]:
        try:
            logger.info(f"  → Opening {self.page_url}...")
            page.goto(self.page_url, wait_until="networkidle")

            self._wait_for_price_content(page)

            download_url = self._find_download_url(page.query_selector_all("a"))
            if download_url:
                logger.info(f"  → Downloading file: {download_url}")
                prices_df = self._download_and_parse_xls(download_url)
                if prices_df is not None:
                    return prices_df

            return self._extract_prices_from_rendered_tables(page.query_selector_all("table"))
        finally:
            browser.close()
    
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
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("⚠️  Playwright not installed")
            logger.warning("   Install: pip install playwright")
            logger.warning("   Setup: playwright install chromium")
            setup_playwright_instructions()
            return None

        try:
            logger.info("🎯 Fetching REAL OREE prices with Playwright...")
            with sync_playwright() as p:
                logger.info("  → Launching browser...")
                browser = p.chromium.launch()
                page = browser.new_page()
                return self._fetch_prices_from_page(browser, page)
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
                tmp_path = None
                with tempfile.NamedTemporaryFile(suffix='.xls', delete=False) as tmp:
                    tmp.write(response.content)
                    tmp_path = tmp.name
                
                logger.info(f"  → Parsing XLS file...")
                
                try:
                    df = pd.read_excel(tmp_path)
                    return self._parse_xls_prices(df)
                except Exception as e:
                    logger.error(f"  ❌ Error parsing XLS: {e}")
                finally:
                    if tmp_path is not None:
                        os.unlink(tmp_path)
        
        except Exception as e:
            logger.error(f"❌ Download error: {e}")
        
        return None
    
    def _parse_xls_prices(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Parse prices from XLS DataFrame"""
        try:
            prices_list = []
            columns = list(df.columns)

            for _, row in df.iterrows():
                price_row = _parse_xls_price_row(row, columns)
                if price_row is not None:
                    prices_list.append(price_row)

            result_df = _build_prices_frame(prices_list, 'oree_xls')
            if result_df is not None:
                logger.info(f"  ✅ Got {len(result_df)} prices from XLS")
            return result_df
        
        except Exception as e:
            logger.error(f"XLS parsing error: {e}")
        
        return None
    
    def _extract_prices_from_table(self, table_element) -> Optional[pd.DataFrame]:
        """Extract prices from rendered HTML table"""
        try:
            prices_list = []
            rows = table_element.query_selector_all("tr")

            for row in rows:
                cells = row.query_selector_all("td, th")

                price_row = _parse_table_price_row(cells)
                if price_row is not None:
                    prices_list.append(price_row)

            return _build_prices_frame(prices_list, 'oree_table')
        
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

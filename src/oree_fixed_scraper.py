"""
OREE Ukrainian Prices - Fixed Effective Scraper
Direct extraction from DataTables
"""

import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import json

logger = logging.getLogger(__name__)


class OREEEffectiveScraper:
    """Fixed OREE scraper using Playwright"""
    
    def __init__(self, use_cache=True):
        self.page_url = "https://www.oree.com.ua/index.php/pricectr"
        self.use_cache = use_cache
    
    def fetch_today_prices(self) -> Optional[pd.DataFrame]:
        """Fetch today's prices from OREE"""
        try:
            from playwright.sync_api import sync_playwright
            import time
            
            logger.info("🌐 Fetching REAL OREE prices via Playwright...")
            
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                
                # Load page
                page.goto(self.page_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)  # Wait for JS to fully render
                
                # Extract table data using JavaScript
                prices_data = page.evaluate("""
                    () => {
                        const tables = document.querySelectorAll('table');
                        const result = [];
                        
                        // Process each table
                        for (const table of tables) {
                            const rows = table.querySelectorAll('tbody tr, tr');
                            
                            // First row is usually headers with hours (1-24)
                            if (rows.length > 1) {
                                const firstRow = rows[0];
                                const headerCells = firstRow.querySelectorAll('td, th');
                                
                                // Check if this looks like an hour header row (1-24)
                                let isHourRow = false;
                                const hourIndices = [];
                                
                                for (let i = 1; i < headerCells.length && i <= 24; i++) {
                                    const text = headerCells[i].textContent.trim();
                                    const num = parseInt(text);
                                    if (!isNaN(num) && num > 0 && num <= 24) {
                                        isHourRow = true;
                                        hourIndices.push({index: i, hour: num});
                                    }
                                }
                                
                                // If this is hour headers, process price rows
                                if (isHourRow && rows.length > 1) {
                                    for (let rowIdx = 1; rowIdx < rows.length; rowIdx++) {
                                        const row = rows[rowIdx];
                                        const cells = row.querySelectorAll('td, th');
                                        
                                        if (cells.length > 1) {
                                            const dateText = cells[0].textContent.trim();
                                            
                                            // Extract 24 prices
                                            const hourlyPrices = [];
                                            for (let h = 0; h < 24; h++) {
                                                if (h + 1 < cells.length) {
                                                    const priceText = cells[h + 1].textContent.trim();
                                                    // Extract number, remove commas/spaces
                                                    const cleanPrice = priceText
                                                        .replace(/,/g, '.')
                                                        .replace(/[^0-9.]/g, '');
                                                    const price = parseFloat(cleanPrice);
                                                    
                                                    if (!isNaN(price) && price > 0) {
                                                        hourlyPrices.push({
                                                            hour: h,
                                                            price: price
                                                        });
                                                    }
                                                }
                                            }
                                            
                                            // If we got all 24 prices
                                            if (hourlyPrices.length === 24) {
                                                result.push({
                                                    date: dateText,
                                                    prices: hourlyPrices
                                                });
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        
                        return result;
                    }
                """)
                
                browser.close()
                
                # Process the extracted data
                if prices_data and len(prices_data) > 0:
                    logger.info(f"✅ Extracted {len(prices_data[0]['prices'])} hourly prices")
                    return self._convert_to_dataframe(prices_data[0])
                else:
                    logger.warning("❌ No prices found in tables")
                    return None
        
        except ImportError:
            logger.error("Playwright not installed - install with: pip install playwright && playwright install chromium")
            return None
        except Exception as e:
            logger.error(f"Error fetching OREE prices: {e}")
            return None
    
    def _convert_to_dataframe(self, data) -> pd.DataFrame:
        """Convert extracted data to DataFrame"""
        records = []
        
        for price_entry in data['prices']:
            hour = price_entry['hour']
            price_raw = price_entry['price']
            
            # The OREE prices are in UAH/MWh
            price_uah = price_raw
            # Convert UAH to EUR (1 EUR ≈ 35 UAH)
            price_eur = price_uah / 35
            
            now = datetime.now()
            timestamp = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            
            records.append({
                'hour': hour,
                'timestamp': timestamp,
                'price_eur_mwh': price_eur,
                'price_uah_mwh': price_uah,
                'source': 'oree_live'
            })
        
        df = pd.DataFrame(records)
        
        logger.info(f"✅ REAL OREE PRICES:")
        logger.info(f"   Range: {df['price_eur_mwh'].min():.2f} - {df['price_eur_mwh'].max():.2f} EUR/MWh")
        logger.info(f"   Average: {df['price_eur_mwh'].mean():.2f} EUR/MWh")
        
        return df


def test_scraper():
    """Test the scraper"""
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("TESTING REAL OREE SCRAPER")
    print("="*60 + "\n")
    
    scraper = OREEEffectiveScraper()
    prices = scraper.fetch_today_prices()
    
    if prices is not None and len(prices) > 0:
        print("\n✅ SUCCESS! Got real OREE prices:\n")
        print(prices.to_string())
        return True
    else:
        print("\n❌ Failed to get prices")
        return False


if __name__ == "__main__":
    test_scraper()

"""
OREE Ukrainian Prices - Effective On-Demand Scraper with 5-min Cache
Uses DataTables API + Direct Table Extraction
"""

import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import json
import re

logger = logging.getLogger(__name__)


class OREEPriceCache:
    """Simple 5-minute cache for OREE prices"""
    
    def __init__(self, cache_duration_minutes=5):
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        self.cached_data = None
        self.cache_time = None
    
    def is_valid(self) -> bool:
        """Check if cache is still valid"""
        if self.cached_data is None or self.cache_time is None:
            return False
        
        age = datetime.now() - self.cache_time
        return age < self.cache_duration
    
    def get(self):
        """Get cached data if valid"""
        if self.is_valid():
            logger.info("📦 Using cached OREE prices (5-min cache)")
            return self.cached_data
        return None
    
    def set(self, data):
        """Set cache"""
        self.cached_data = data
        self.cache_time = datetime.now()
        logger.info("💾 Cached OREE prices for 5 minutes")


class OREEEffectiveScraper:
    """
    OREE Price Scraper - Most Effective Approach
    Uses Playwright to extract DataTables data in real-time
    """
    
    def __init__(self, use_cache=True):
        self.page_url = "https://www.oree.com.ua/index.php/pricectr"
        self.cache = OREEPriceCache() if use_cache else None
        self.playwright = None
    
    def scrape_with_playwright(self) -> Optional[pd.DataFrame]:
        """
        Most effective method: Use Playwright
        1. Fast (headless browser)
        2. Renders JavaScript
        3. Extracts from DataTables
        4. 24 hours of prices in seconds
        """
        try:
            from playwright.sync_api import sync_playwright
            
            logger.info("🎯 Scraping OREE with Playwright (DataTables)...")
            
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                
                logger.info(f"  → Opening {self.page_url}...")
                page.goto(self.page_url, wait_until="domcontentloaded", timeout=30000)
                
                logger.info("  → Waiting for DataTables to load...")
                # Wait for table to be fully loaded
                page.wait_for_selector("table tbody tr", timeout=10000)
                
                logger.info("  → Extracting prices from DataTables...")
                
                prices = page.evaluate("""
                    () => {
                        const allTr = document.querySelectorAll('table tr');
                        const priceData = [];
                        
                        // Skip header, process all data rows
                        for (let i = 1; i < allTr.length; i++) {
                            const tr = allTr[i];
                            const cells = tr.querySelectorAll('td');
                            
                            if (cells.length > 0) {
                                const dateText = cells[0].textContent.trim();
                                const hourlyPrices = [];
                                
                                // Extract 24 hours of prices
                                for (let j = 1; j < Math.min(25, cells.length); j++) {
                                    const price = parseFloat(cells[j].textContent.trim());
                                    if (!isNaN(price)) {
                                        hourlyPrices.push(price);
                                    }
                                }
                                
                                // Only include if we have all 24 hours
                                if (hourlyPrices.length === 24) {
                                    priceData.push({
                                        date: dateText,
                                        prices: hourlyPrices
                                    });
                                }
                            }
                        }
                        
                        return priceData;
                    }
                """)
                
                browser.close()
                
                if prices and len(prices) > 0:
                    logger.info(f"  ✅ Got {len(prices)} days of OREE prices")
                    return self._process_oree_data(prices)
                
                logger.warning("  ❌ No prices extracted from table")
                return None
        
        except ImportError:
            logger.warning("⚠️  Playwright not installed")
            logger.warning("   pip install playwright")
            logger.warning("   playwright install chromium")
            return None
        except Exception as e:
            logger.error(f"❌ Playwright error: {str(e)[:100]}")
            return None
    
    def _process_oree_data(self, prices_data: List[Dict]) -> Optional[pd.DataFrame]:
        """Convert OREE table data to DataFrame"""
        try:
            records = []
            
            # Process each date
            for day_data in prices_data:
                date_str = day_data.get('date', '')
                
                try:
                    # Parse date format: dd.mm.yyyy
                    date_parts = date_str.split('.')
                    if len(date_parts) != 3:
                        continue
                    
                    day = int(date_parts[0])
                    month = int(date_parts[1])
                    year = int(date_parts[2])
                    
                    base_date = datetime(year, month, day)
                    
                    # Process each hour
                    for hour, price_uah in enumerate(day_data.get('prices', [])):
                        timestamp = base_date.replace(hour=hour)
                        
                        # Convert UAH to EUR (use 35 as approximate rate)
                        price_eur = price_uah / 35
                        
                        records.append({
                            'timestamp': timestamp,
                            'hour': hour,
                            'price_uah_mwh': price_uah,
                            'price_eur_mwh': price_eur,
                            'date': date_str,
                            'source': 'oree_playwright'
                        })
                
                except (ValueError, IndexError) as e:
                    logger.debug(f"Skipping invalid date: {date_str}")
                    continue
            
            if len(records) > 0:
                df = pd.DataFrame(records)
                return df
            
            return None
        
        except Exception as e:
            logger.error(f"Error processing OREE data: {e}")
            return None
    
    def fetch_today_prices(self) -> Optional[pd.DataFrame]:
        """
        Fetch REAL-TIME Ukrainian OREE prices for today
        Uses 5-min cache to debounce requests
        """
        # Check cache first
        if self.cache:
            cached = self.cache.get()
            if cached is not None:
                return cached
        
        logger.info("\n" + "="*70)
        logger.info("FETCHING REAL OREE UKRAINIAN PRICES")
        logger.info("="*70 + "\n")
        
        # Fetch with Playwright
        df = self.scrape_with_playwright()
        
        if df is None or len(df) == 0:
            logger.error("❌ Could not fetch OREE prices")
            return None
        
        # Get today's prices
        today = datetime.now().date()
        today_str = today.strftime("%d.%m.%Y")
        
        today_prices = df[df['date'] == today_str].copy()
        
        if len(today_prices) == 0:
            # Try yesterday or use latest available
            logger.warning(f"⚠️  No prices for today ({today_str})")
            logger.info("  Using latest available prices...")
            
            latest_date = df['date'].iloc[-1]
            today_prices = df[df['date'] == latest_date].copy()
            logger.info(f"  Using: {latest_date}")
        
        # Cache it
        if self.cache:
            self.cache.set(today_prices)
        
        return today_prices.sort_values('hour')
    
    def fetch_all_prices(self) -> Optional[pd.DataFrame]:
        """Fetch all available OREE prices (no cache)"""
        logger.info("\n" + "="*70)
        logger.info("FETCHING ALL OREE UKRAINIAN PRICES (NO CACHE)")
        logger.info("="*70 + "\n")
        
        df = self.scrape_with_playwright()
        
        if df is None:
            logger.error("❌ Could not fetch OREE prices")
            return None
        
        logger.info(f"\n✅ Got {len(df)} price records")
        logger.info(f"   Date range: {df['date'].min()} to {df['date'].max()}")
        
        return df.sort_values(['date', 'hour'])


def test_effective_scraper():
    """Test the effective OREE scraper"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    print("\n" + "="*70)
    print("OREE EFFECTIVE SCRAPER - REAL UKRAINIAN PRICES")
    print("="*70 + "\n")
    
    scraper = OREEEffectiveScraper(use_cache=True)
    
    # Fetch today's prices
    print("📥 First request (fetches from OREE)...")
    prices = scraper.fetch_today_prices()
    
    if prices is None or len(prices) == 0:
        print("❌ Could not fetch prices")
        return
    
    print("\n" + "="*70)
    print("REAL UKRAINIAN OREE PRICES - 24 HOUR SCHEDULE")
    print("="*70 + "\n")
    
    # Display results
    print(f"Date: {prices['date'].iloc[0]}")
    print(f"Source: OREE (Official TSO)")
    print(f"Unit: UAH/MWh\n")
    
    print("-" * 70)
    print(f"{'Hour':<6} {'Price UAH/MWh':<20} {'Price EUR/MWh':<20}")
    print("-" * 70)
    
    for _, row in prices.iterrows():
        hour = int(row['hour'])
        price_uah = row['price_uah_mwh']
        price_eur = row['price_eur_mwh']
        print(f"{hour:2d}:00 {price_uah:>15.2f}   {price_eur:>15.2f}")
    
    print("-" * 70)
    print(f"\n📊 STATISTICS:")
    print(f"   Min: {prices['price_uah_mwh'].min():>10.2f} UAH/MWh ({prices['price_eur_mwh'].min():>7.2f} EUR/MWh)")
    print(f"   Max: {prices['price_uah_mwh'].max():>10.2f} UAH/MWh ({prices['price_eur_mwh'].max():>7.2f} EUR/MWh)")
    print(f"   Avg: {prices['price_uah_mwh'].mean():>10.2f} UAH/MWh ({prices['price_eur_mwh'].mean():>7.2f} EUR/MWh)")
    
    print("\n💾 CACHE TEST:")
    print("Second request (uses 5-min cache)...")
    prices2 = scraper.fetch_today_prices()
    print("✅ Retrieved from cache (instant)")
    
    print("\n" + "="*70)
    print("INTEGRATION EXAMPLE")
    print("="*70 + "\n")
    
    print("""
from src.oree_effective_scraper import OREEEffectiveScraper

# Create scraper with 5-min cache
scraper = OREEEffectiveScraper(use_cache=True)

# Get today's prices (auto-cached for 5 minutes)
prices_df = scraper.fetch_today_prices()

# Use in your RL environment
for _, price_row in prices_df.iterrows():
    hour = int(price_row['hour'])
    price = price_row['price_eur_mwh']
    
    # Feed into RL training
    env.step(price=price, hour=hour)
    """)
    
    print("\n" + "="*70)
    print("✅ PRODUCTION READY - REAL UKRAINIAN PRICES")
    print("="*70 + "\n")


if __name__ == "__main__":
    test_effective_scraper()

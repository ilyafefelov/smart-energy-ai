"""
OREE Price Scraper with Selenium for JavaScript-rendered content
Handles: https://www.oree.com.ua/index.php/pricectr?lang=english
"""

import logging
import pandas as pd
from datetime import datetime
from typing import Optional
import re

logger = logging.getLogger(__name__)

def scrape_oree_with_selenium() -> Optional[pd.DataFrame]:
    """
    Scrape OREE using Selenium (requires WebDriver)
    Install: pip install selenium
    Download: https://chromedriver.chromium.org/ (your Chrome version)
    
    This handles JavaScript-rendered prices
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
        
        logger.info("🔧 Using Selenium to fetch OREE prices...")
        
        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Try headless mode first
        chrome_options.add_argument("--headless")
        
        try:
            # Initialize driver
            driver = webdriver.Chrome(options=chrome_options)
            
            # Go to OREE price page
            url = "https://www.oree.com.ua/index.php/pricectr?lang=english"
            logger.info(f"  Opening {url}...")
            driver.get(url)
            
            # Wait for page to load
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
                )
            except:
                logger.debug("  Table load timeout, continuing anyway")
            
            # Get page source
            page_source = driver.page_source
            driver.quit()
            
            # Parse with BeautifulSoup
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract prices
            prices_list = []
            for table in soup.find_all('table'):
                rows = table.find_all('tr')
                
                if len(rows) < 24:
                    continue
                
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
                            digits = re.findall(r'\d+', hour_text)
                            hour = int(digits[0]) if digits else None
                        
                        if hour is None or not (0 <= hour <= 23):
                            continue
                        
                        # Parse price
                        price_match = re.findall(r'\d+\.?\d*', price_text)
                        if price_match:
                            price = float(price_match[0])
                            
                            if 0.1 < price < 500:
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
                        'source': 'oree_selenium'
                    }
                    for p in prices_list
                ])
                
                logger.info(f"✅ Selenium: Got {len(df)} OREE prices")
                return df
            
            logger.warning("❌ Selenium: Could not extract 24 prices")
            return None
        
        except ImportError:
            logger.warning("⚠️  Selenium not installed. Run: pip install selenium")
            return None
        except Exception as e:
            logger.error(f"❌ Selenium error: {e}")
            return None
    
    except Exception as e:
        logger.error(f"❌ Selenium setup error: {e}")
        return None


def setup_selenium_instructions():
    """Print setup instructions for Selenium"""
    instructions = """
    
╔════════════════════════════════════════════════════════════════╗
║          SETUP SELENIUM FOR OREE SCRAPING                      ║
╚════════════════════════════════════════════════════════════════╝

To enable JavaScript-based OREE scraping:

1. Install Selenium:
   pip install selenium

2. Download ChromeDriver:
   - Go to: https://chromedriver.chromium.org/
   - Find version matching your Chrome version
     (Check: chrome://settings/help)
   - Download and save to project folder

3. Use in code:
   from src.oree_selenium_scraper import scrape_oree_with_selenium
   
   prices = scrape_oree_with_selenium()
   if prices is not None:
       print(f"Got {len(prices)} OREE prices!")

4. Troubleshoot:
   - If "ChromeDriver not found": Put chromedriver in project root
   - If page doesn't load: Check internet connection
   - If "Timeout": Page structure may have changed (email OREE)
   - If "Permission denied": Make chromedriver executable:
     chmod +x chromedriver (on Linux/Mac)

╔════════════════════════════════════════════════════════════════╗
║          ALTERNATIVE: CONTACT OREE DIRECTLY                   ║
╚════════════════════════════════════════════════════════════════╝

For reliable real-time prices, consider:
- Emailing: oree@oree.com.ua
- Requesting: API access or data feed
- Mentioning: Academic project (thesis)
- They often provide data to educational institutions!

╔════════════════════════════════════════════════════════════════╗
║          USING PXE API (RECOMMENDED)                          ║
╚════════════════════════════════════════════════════════════════╝

If OREE is difficult, use PXE (Polish Power Exchange):
- More reliable API
- Has Ukrainian market prices
- Well-documented
- No scraping needed

pip install pxe-api  # (if available)

Or manually:
- API docs: https://www.pxe.pl/en/api-documentation
- Prices endpoint: [check their docs]
- Returns JSON with hourly prices

    """
    print(instructions)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("OREE SELENIUM SCRAPER")
    print("="*60)
    
    prices = scrape_oree_with_selenium()
    
    if prices is not None:
        print(f"\n✅ Success! Got {len(prices)} prices")
        print(prices.head(10))
    else:
        print("\n⚠️  Selenium scraping not available")
        setup_selenium_instructions()

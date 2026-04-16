"""
OREE Real Price Fetcher - Production Version
Scrapes actual prices from OREE Ukraine
"""

import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

OREE_PRICES_URL = "https://www.oree.com.ua/index.php/pricectr?lang=english"
UAH_PER_EUR = 35.0


def _parse_hour(text: str) -> Optional[int]:
    """Parse an hour value from OREE table text."""
    if not text:
        return None

    if ":" in text:
        try:
            hour = int(text.split(":", 1)[0])
        except ValueError:
            hour = None
        if hour is not None and 0 <= hour <= 23:
            return hour

    for digit in re.findall(r"\d+", text):
        try:
            hour = int(digit)
        except ValueError:
            continue
        if 0 <= hour <= 23:
            return hour

    return None


def _parse_realistic_price(cell_texts: list[str]) -> Optional[float]:
    """Return the first realistic EUR/MWh price found in table cells."""
    for cell_text in cell_texts:
        if not cell_text:
            continue

        clean = (
            cell_text.replace("EUR/MWh", "")
            .replace("€", "")
            .replace("UAH", "")
            .replace(",", ".")
        )

        for number_text in re.findall(r"\d+\.?\d*", clean):
            try:
                price = float(number_text)
            except ValueError:
                continue

            if 0.1 < price < 500:
                return price

    return None


def _extract_table_prices(table) -> list[dict[str, float]]:
    """Parse hour-price rows from one OREE HTML table."""
    prices_list = []

    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue

        texts = [cell.get_text(strip=True) for cell in cells[:5]]
        hour = _parse_hour(texts[0])
        if hour is None:
            continue

        price = _parse_realistic_price(texts[1:])
        if price is None:
            continue

        prices_list.append({"hour": hour, "price": price})

    return prices_list


def _build_prices_frame(prices_list: list[dict[str, float]]) -> pd.DataFrame:
    """Convert parsed hourly prices into the public OREE DataFrame format."""
    now = datetime.now()
    ordered_prices = sorted(prices_list, key=lambda row: row["hour"])[:24]
    return pd.DataFrame(
        [
            {
                "timestamp": now.replace(
                    hour=price_row["hour"], minute=0, second=0, microsecond=0
                ),
                "price_eur_mwh": price_row["price"],
                "price_uah_mwh": price_row["price"] * UAH_PER_EUR,
                "source": "oree_real",
            }
            for price_row in ordered_prices
        ]
    )

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

            logger.info(f"  Requesting: {OREE_PRICES_URL}")
            response = self.session.get(OREE_PRICES_URL, timeout=20)
            response.raise_for_status()

            logger.info(f"  ✓ Status: {response.status_code}")
            logger.info(f"  ✓ Content length: {len(response.text)} bytes")

            soup = BeautifulSoup(response.content, 'html.parser')
            tables = soup.find_all('table')
            logger.info(f"  Found {len(tables)} tables on page")

            for table_idx, table in enumerate(tables):
                rows = table.find_all('tr')

                if len(rows) < 20:
                    logger.debug(f"  Table {table_idx}: {len(rows)} rows (skip)")
                    continue

                logger.info(f"  Checking table {table_idx} ({len(rows)} rows)...")

                prices_list = _extract_table_prices(table)
                if len(prices_list) >= 20:
                    logger.info(f"  ✅ Found {len(prices_list)} prices in table {table_idx}")

                    df = _build_prices_frame(prices_list)

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

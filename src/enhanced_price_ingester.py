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

PXE_API_URLS = [
    'https://www.pxe.pl/api/graph',
    'https://api.pxe.pl/prices',
]

UKRSTAT_URLS = [
    'https://www.ukrstat.gov.ua/operativ/operativ2018/energ/ser_cin_el_energ/ser_cin_el_energ_u/arh_sc_elen2018_u.htm',
    'https://www.ukrstat.gov.ua/operativ/operativ2018/energ/ser_cin_el_energ/arh_sc_elen_u.htm',
]

SUPPORTED_DATE_FORMATS = ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y')


def _extract_hour_from_text(text: str) -> Optional[int]:
    """Parse an hourly index from either HH:00 or plain digit text."""
    if ':' in text:
        try:
            hour = int(text.split(':')[0])
        except ValueError:
            hour = None
    else:
        hour = None

    if hour is None:
        digits = re.findall(r'\d+', text)
        if digits:
            hour = int(digits[0])

    if hour is None or not (0 <= hour <= 23):
        return None

    return hour


def _extract_price_from_text(
    text: str,
    *,
    strip_tokens: tuple[str, ...] = (),
    minimum: float = 0.1,
    maximum: float = 500,
) -> Optional[float]:
    """Return the first realistic price found in a text fragment."""
    normalized = text.replace(',', '.')
    for token in strip_tokens:
        normalized = normalized.replace(token, '')

    for number_text in re.findall(r'\d+\.?\d*', normalized):
        try:
            price = float(number_text)
        except ValueError:
            continue

        if minimum < price < maximum:
            return price

    return None


def _build_hourly_price_frame(prices_list: list[dict[str, float]], source: str) -> Optional[pd.DataFrame]:
    """Convert hourly price pairs into the common 24-row price frame."""
    if len(prices_list) < 24:
        return None

    sorted_prices = sorted(prices_list, key=lambda x: x['hour'])[:24]
    now = datetime.now()
    return pd.DataFrame(
        [
            {
                'timestamp': now.replace(hour=price_row['hour'], minute=0, second=0, microsecond=0),
                'price_eur_mwh': price_row['price'],
                'price_uah_mwh': price_row['price'] * 35,
                'source': source,
            }
            for price_row in sorted_prices
        ]
    )


def _extract_oree_price_row(cell_texts: list[str]) -> Optional[dict[str, float]]:
    """Parse one OREE-style hour/price row."""
    hour = _extract_hour_from_text(cell_texts[0])
    if hour is None:
        return None

    for price_cell in cell_texts[1:]:
        price = _extract_price_from_text(price_cell, strip_tokens=('EUR/MWh', '€'))
        if price is not None:
            return {'hour': hour, 'price': price}

    return None


def _extract_generic_price_row(texts: list[str]) -> Optional[dict[str, float]]:
    """Parse one generic table row by looking for any hour-like and price-like values."""
    hour = None
    price = None

    for text in texts:
        if hour is None:
            hour = _extract_hour_from_text(text)
        if price is None:
            price = _extract_price_from_text(text)
        if hour is not None and price is not None:
            return {'hour': hour, 'price': price}

    return None


def _parse_pxe_price_row(item: object) -> Optional[dict[str, float]]:
    """Parse one PXE API item into a normalized hour/price pair."""
    if not isinstance(item, dict):
        return None

    price_value = item.get('price') or item.get('value')
    hour_value = item.get('hour') or item.get('hh')
    if not price_value or hour_value is None:
        return None

    try:
        price = float(price_value)
        hour = int(hour_value) % 24
    except (ValueError, TypeError):
        return None

    if not 0.1 < price < 500:
        return None

    return {'hour': hour, 'price': price}


def _parse_supported_date(text: str) -> Optional[datetime]:
    """Parse a supported ukrstat date format."""
    for date_format in SUPPORTED_DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format)
        except ValueError:
            continue
    return None


def _parse_ukrstat_record(texts: list[str]) -> Optional[dict[str, object]]:
    """Parse one ukrstat row into a date/price record."""
    if not texts:
        return None

    date_obj = _parse_supported_date(texts[0])
    if date_obj is None:
        return None

    price_text = texts[1] if len(texts) > 1 else ''
    price = _extract_price_from_text(price_text)
    if price is None:
        return None

    return {
        'date': date_obj,
        'price_uah_mwh': price,
        'source': 'ukrstat_historical',
    }


def _extract_first_complete_table(
    soup: BeautifulSoup,
    table_parser,
    *,
    minimum_rows: int = 24,
) -> tuple[Optional[int], Optional[pd.DataFrame]]:
    """Return the first table index and parsed frame meeting the row threshold."""
    for table_idx, table in enumerate(soup.find_all('table')):
        df = table_parser(table)
        if df is None or len(df) < minimum_rows:
            continue
        return table_idx, df

    return None, None

class EnhancedPriceIngester:
    """Fetch prices from multiple sources"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def _fetch_first_frame_from_urls(
        self,
        urls: list[str],
        *,
        timeout: int,
        response_to_frame,
        minimum_rows: int,
        success_message: str,
        error_label: str,
    ) -> Optional[pd.DataFrame]:
        """Try URLs in order until a parser returns a sufficiently complete frame."""
        for url in urls:
            try:
                logger.debug(f'  Trying {url}...')
                response = self.session.get(url, timeout=timeout)
                if response.status_code != 200:
                    continue

                df = response_to_frame(response)
                if df is None or len(df) < minimum_rows:
                    continue

                logger.info(success_message.format(row_count=len(df)))
                return df
            except Exception as e:
                logger.debug(f'  {error_label} error: {str(e)[:50]}')

        return None
    
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
            table_idx, df = _extract_first_complete_table(soup, self._extract_price_from_table)
            if df is not None:
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

                    cell_texts = [c.get_text(strip=True) for c in cells[:3]]
                    price_row = _extract_oree_price_row(cell_texts)
                    if price_row is not None:
                        prices_list.append(price_row)
                
                if len(prices_list) >= 24:
                    break

            return _build_hourly_price_frame(prices_list, 'oree')
        
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

                price_row = _extract_generic_price_row(texts)
                if price_row is not None:
                    prices_list.append(price_row)

            return _build_hourly_price_frame(prices_list, 'oree_table')
        
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
            return self._fetch_first_frame_from_urls(
                PXE_API_URLS,
                timeout=10,
                response_to_frame=lambda response: self._parse_pxe_data(response.json()),
                minimum_rows=24,
                success_message='✅ Got PXE prices: {row_count} hours',
                error_label='PXE',
            )
        
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
                    price_row = _parse_pxe_price_row(item)
                    if price_row is not None:
                        prices_list.append(price_row)

            return _build_hourly_price_frame(prices_list, 'pxe')
        
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
            return self._fetch_first_frame_from_urls(
                UKRSTAT_URLS,
                timeout=15,
                response_to_frame=lambda response: self._parse_ukrstat_prices(response.content),
                minimum_rows=1,
                success_message='✅ Got {row_count} historical price records',
                error_label='ukrstat',
            )
        
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

                    texts = [c.get_text(strip=True) for c in cells[:3]]
                    record = _parse_ukrstat_record(texts)
                    if record is not None:
                        records.append(record)
            
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

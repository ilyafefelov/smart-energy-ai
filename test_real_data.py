"""
Test real data fetching from APIs
Verifies that weather and price data are being fetched from real sources
"""

import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_weather_api():
    """Test Open-Meteo weather API"""
    print("\n" + "="*60)
    print("🌤️  TESTING WEATHER API (Open-Meteo)")
    print("="*60)
    
    from src.data_pipeline.ingest_weather import WeatherIngester
    
    ingester = WeatherIngester(latitude=50.45, longitude=30.52)
    
    # Fetch from API
    print("\n1️⃣  Fetching weather data from Open-Meteo API...")
    data = ingester.fetch_weather()
    
    if not data:
        print("❌ FAILED: Could not fetch weather data")
        return False
    
    print(f"✅ SUCCESS: Received data from API")
    print(f"   - Contains 'hourly' key: {'hourly' in data}")
    print(f"   - Contains 'latitude': {data.get('latitude', 'N/A')}")
    print(f"   - Contains 'longitude': {data.get('longitude', 'N/A')}")
    
    # Parse data
    print("\n2️⃣  Parsing weather data...")
    df = ingester.parse_weather_data(data)
    
    if df is None or df.empty:
        print("❌ FAILED: Could not parse weather data")
        return False
    
    print(f"✅ SUCCESS: Parsed {len(df)} weather records")
    print(f"\n   First 5 records:")
    print(df.head().to_string())
    
    # Validate data
    print("\n3️⃣  Validating weather data...")
    is_valid = ingester.validate_weather_data(df)
    
    if is_valid:
        print("✅ SUCCESS: Weather data is valid")
    else:
        print("⚠️  WARNING: Weather data has some issues (but still usable)")
    
    print(f"\n   Temperature range: {df['temperature'].min():.1f}°C to {df['temperature'].max():.1f}°C")
    print(f"   Solar radiation range: {df['solar_radiation'].min():.1f} to {df['solar_radiation'].max():.1f} W/m²")
    print(f"   Cloud cover range: {df['cloudcover'].min():.1f}% to {df['cloudcover'].max():.1f}%")
    
    return True


def test_price_api():
    """Test OREE price API and scraping"""
    print("\n" + "="*60)
    print("💰 TESTING PRICE API & SCRAPING (OREE)")
    print("="*60)
    
    from src.data_pipeline.ingest_prices import PriceIngester
    
    ingester = PriceIngester()
    
    # Try API first
    print("\n1️⃣  Attempting to fetch from OREE API...")
    df = ingester.fetch_oree_api()
    
    if df is not None and not df.empty:
        print(f"✅ SUCCESS: API returned {len(df)} price records")
        api_source = "OREE API"
    else:
        print("⚠️  API not available, trying web scraping...")
        print("\n2️⃣  Attempting to fetch from OREE website...")
        df = ingester.fetch_oree_prices()
        
        if df is not None and not df.empty:
            print(f"✅ SUCCESS: Website scraping returned {len(df)} price records")
            api_source = "OREE Website (scraping)"
        else:
            print("❌ FAILED: Could not fetch prices from any source")
            return False
    
    print(f"   Source: {api_source}")
    
    # Validate data
    print(f"\n3️⃣  Validating price data...")
    is_valid = ingester.validate_price_data(df)
    
    if is_valid:
        print("✅ SUCCESS: Price data is valid")
    else:
        print("⚠️  WARNING: Price data has some issues (but still usable)")
    
    print(f"\n   Price range: {df['price_eur_mwh'].min():.2f} to {df['price_eur_mwh'].max():.2f} EUR/MWh")
    print(f"   In UAH: {df['price_uah_mwh'].min():.0f} to {df['price_uah_mwh'].max():.0f} UAH/MWh")
    
    print(f"\n   First 5 records:")
    print(df[['timestamp', 'price_eur_mwh', 'price_uah_mwh', 'source']].head().to_string())
    
    # Check for realistic prices
    if df['price_eur_mwh'].min() > 0.1 and df['price_eur_mwh'].max() < 500:
        print("\n✅ Price ranges are realistic")
    else:
        print("\n⚠️  Price ranges seem unusual")
    
    return True


def main():
    """Run all API tests"""
    print("\n" + "🧪 REAL DATA FETCHING TEST SUITE 🧪".center(60))
    print("Verifying actual API data (not dummy data)")
    print("="*60)
    
    results = {}
    
    # Test weather API
    try:
        results['Weather API'] = test_weather_api()
    except Exception as e:
        print(f"\n❌ Weather API test crashed: {e}")
        results['Weather API'] = False
    
    # Test price API
    try:
        results['Price API'] = test_price_api()
    except Exception as e:
        print(f"\n❌ Price API test crashed: {e}")
        results['Price API'] = False
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED - REAL DATA IS BEING FETCHED")
    else:
        print("\n⚠️  SOME TESTS FAILED - CHECK YOUR API ACCESS")
    
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Test OREE Playwright scraper"""

from src.oree_effective_scraper import OREEEffectiveScraper
import time

print("Testing OREE Playwright scraper...")
print("=" * 60)

try:
    scraper = OREEEffectiveScraper(use_cache=False)
    print("Scraper initialized")
    print("Fetching OREE prices (this may take 10-20 seconds)...")
    
    start = time.time()
    prices = scraper.fetch_today_prices()
    elapsed = time.time() - start
    
    if prices is not None and len(prices) > 0:
        print(f"\n✅ SUCCESS! Got {len(prices)} rows in {elapsed:.1f}s\n")
        print("First 3 rows:")
        print(prices[['hour', 'price_eur_mwh', 'price_uah_mwh']].head(3).to_string())
        print("\nStatistics:")
        print(f"  Min: {prices['price_eur_mwh'].min():.2f} EUR/MWh")
        print(f"  Max: {prices['price_eur_mwh'].max():.2f} EUR/MWh")
        print(f"  Avg: {prices['price_eur_mwh'].mean():.2f} EUR/MWh")
        print(f"\nSource: {prices['source'].iloc[0]}")
    else:
        print("❌ No data returned")
        
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}")
    print(f"Message: {str(e)}")
    import traceback
    print("\nTraceback:")
    traceback.print_exc()

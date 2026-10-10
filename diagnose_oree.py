#!/usr/bin/env python3
"""Diagnose OREE website structure"""

from playwright.sync_api import sync_playwright
import time

print("Diagnosing OREE website...")
print("=" * 60)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        url = "https://www.oree.com.ua/index.php/pricectr"
        print(f"Opening: {url}")
        
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)  # Wait for JS to load
        
        # Get page title
        title = page.title()
        print(f"Page title: {title}")
        
        # Look for tables
        tables = page.query_selector_all("table")
        print(f"\nFound {len(tables)} tables on page")
        
        # Look for price-related text
        text_content = page.content()
        
        if "price" in text_content.lower():
            print("✓ Page contains 'price' text")
        
        if "EUR" in text_content or "MWh" in text_content:
            print("✓ Page contains 'EUR' or 'MWh'")
        
        # Try to find and display first table structure
        if tables:
            table = tables[0]
            rows = table.query_selector_all("tr")
            print(f"\nFirst table has {len(rows)} rows")
            
            if rows:
                # Get first row
                first_row = rows[0]
                cells = first_row.query_selector_all("td, th")
                print(f"First row has {len(cells)} cells")
                
                if len(cells) > 0:
                    print("\nFirst row content (first 5 cells):")
                    for i, cell in enumerate(cells[:5]):
                        text = cell.inner_text()[:50]
                        print(f"  Cell {i}: {text}")
        
        # Look for any numbers that might be prices
        numbers = page.locator("td, span, div").filter(has_text="EUR").count()
        print(f"\nElements with 'EUR': {numbers}")
        
        browser.close()
        print("\n✅ Diagnosis complete")
        
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

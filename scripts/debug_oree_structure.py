#!/usr/bin/env python3
"""Debug OREE page structure"""

import requests
from bs4 import BeautifulSoup
import re

url = "https://www.oree.com.ua/index.php/pricectr?lang=english"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print("\nFetching OREE page structure...\n")

response = requests.get(url, headers=headers, timeout=20)
soup = BeautifulSoup(response.content, 'html.parser')

print("="*60)
print("PAGE STRUCTURE ANALYSIS")
print("="*60)

# Look for all text content that might contain prices
text = soup.get_text()

print(f"\nTotal page text: {len(text)} characters")

# Look for price-like patterns (numbers with EUR or UAH)
price_patterns = re.findall(r'\d+\.?\d*\s*(EUR|UAH|€|грн)', text)
print(f"\nPrice patterns found: {len(price_patterns)}")
if price_patterns:
    print(f"Examples: {price_patterns[:5]}")

# Look for time/hour patterns
hour_patterns = re.findall(r'(\d{1,2}):00|hour\s+(\d{1,2})', text, re.IGNORECASE)
print(f"\nHour patterns found: {len(hour_patterns)}")
if hour_patterns:
    print(f"Examples: {hour_patterns[:5]}")

# Look for divs that might contain prices
divs = soup.find_all('div')
print(f"\nDivs found: {len(divs)}")

# Look for spans
spans = soup.find_all('span')
print(f"Spans found: {len(spans)}")

# Look for any data-* attributes
data_attrs = soup.find_all(attrs={'data-price': True})
print(f"\nElements with data-price: {len(data_attrs)}")

data_attrs = soup.find_all(attrs={'data-hour': True})
print(f"Elements with data-hour: {len(data_attrs)}")

# Look for script tags with JSON data
scripts = soup.find_all('script')
print(f"\nScript tags: {len(scripts)}")

for idx, script in enumerate(scripts):
    if script.string and ('price' in script.string.lower() or 'dam' in script.string.lower() or 'json' in script.string.lower()):
        print(f"\nScript {idx} contains 'price'/'DAM'/'JSON':")
        content = script.string[:200]
        print(f"  {content}...")

print("\n" + "="*60)
print("RECOMMENDATION:")
print("="*60)

# Check if it's a JavaScript-heavy page
if len(scripts) > 20:
    print("\n⚠️  Page uses heavy JavaScript (likely SPA)")
    print("   → Need Selenium or headless browser")
    print("   → Try: pip install selenium")
    print("   → Then use Selenium scraper")
elif price_patterns:
    print("\n✅ Page contains price data")
    print("   → Try: Beautiful Soup approach")
else:
    print("\n❌ Prices not found in HTML")
    print("   → Likely loaded via AJAX/JavaScript")
    print("   → Or behind API call")
    print("   → Try: Check Network tab in browser DevTools")

print("\n" + "="*60 + "\n")

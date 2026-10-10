#!/usr/bin/env python3
"""Check OREE page for Excel downloads and price tables"""

import requests
from bs4 import BeautifulSoup
import re

url = 'https://www.oree.com.ua/index.php/pricectr'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print('\nChecking OREE page structure...\n')
print("="*70)

response = requests.get(url, headers=headers, timeout=20)
soup = BeautifulSoup(response.content, 'html.parser')

# Find all links
links = soup.find_all('a')
print(f'Total links found: {len(links)}\n')

# Look for XLS/Excel links
print('🔍 Excel/XLS Files:')
print("-"*70)
found_xls = False
for link in links:
    href = link.get('href', '')
    text = link.get_text(strip=True)
    
    if 'xls' in href.lower() or 'excel' in href.lower() or href.endswith('.xls') or href.endswith('.xlsx'):
        print(f'✅ {text}')
        print(f'   {href}\n')
        found_xls = True

if not found_xls:
    print('No XLS links in simple scan\n')

# Look for price-related content
print("\n💰 Price-related Links:")
print("-"*70)
price_count = 0
for link in links:
    href = link.get('href', '')
    text = link.get_text(strip=True)
    
    if ('price' in text.lower() or 'price' in href.lower()) and text.strip():
        print(f'{text}')
        if href:
            print(f'   {href}')
        print()
        price_count += 1

if price_count == 0:
    print('No price-related links found\n')

# Look for download/file links
print("\n📥 Download Links:")
print("-"*70)
download_count = 0
for link in links:
    href = link.get('href', '')
    text = link.get_text(strip=True)
    
    if ('download' in text.lower() or 'download' in href.lower()) and text.strip():
        print(f'{text}')
        print(f'   {href}')
        print()
        download_count += 1

if download_count == 0:
    print('No download links found\n')

# Check for tables with price data
print("\n📊 Tables on page:")
print("-"*70)
tables = soup.find_all('table')
print(f'Tables found: {len(tables)}\n')

for idx, table in enumerate(tables):
    rows = table.find_all('tr')
    cols = table.find_all('td')
    print(f'Table {idx}: {len(rows)} rows, ~{len(cols)} cells')
    
    # Show first few cells
    if rows:
        first_row = rows[0]
        first_cells = first_row.find_all(['td', 'th'])[:3]
        cell_texts = [c.get_text(strip=True)[:20] for c in first_cells]
        print(f'  First row: {" | ".join(cell_texts)}')
    print()

# Look for any downloadable content in page
print("\n🔗 All href attributes with 'file', 'attach', 'media':")
print("-"*70)
for link in soup.find_all('a'):
    href = link.get('href', '')
    if any(x in href.lower() for x in ['file', 'attach', 'media', '.xls', '.xlsx', '.csv', '.pdf']):
        text = link.get_text(strip=True)[:30]
        print(f'{text}: {href}')

print("\n" + "="*70)
print("\n✅ Check complete - see above for download links and tables\n")

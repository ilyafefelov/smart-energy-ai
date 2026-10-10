#!/usr/bin/env python3
"""Test OREE API endpoints"""

import requests
import json

print('Trying different OREE endpoints...\n')

# Try different APIs that might have OREE data
apis = [
    'https://www.oree.com.ua/api/prices',
    'https://www.oree.com.ua/api/dam/prices',
    'https://api.oree.com.ua/prices',
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json'
}

for url in apis:
    try:
        print(f'Testing: {url}')
        response = requests.get(url, headers=headers, timeout=5)
        print(f'  Status: {response.status_code}')
        
        if response.status_code == 200:
            if 'json' in response.headers.get('content-type', '').lower():
                print(f'  Got JSON response')
                data = response.json()
                if isinstance(data, dict):
                    print(f'  Keys: {list(data.keys())[:3]}')
                elif isinstance(data, list):
                    print(f'  List with {len(data)} items')
            else:
                content_len = len(response.text)
                if content_len > 1000:
                    print(f'  Got {content_len} bytes of data')
        print()
    except Exception as e:
        print(f'  Error: {str(e)[:50]}')
        print()

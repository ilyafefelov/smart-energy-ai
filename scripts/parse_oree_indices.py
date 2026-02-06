#!/usr/bin/env python3
"""
Parse OREE hourly price indices from Excel/HTML files (Jan-Feb 2026)

OREE files may be saved HTML tables with .xls extension
This script handles both cases with fallback strategies
"""

import pandas as pd
import re
import json
from pathlib import Path
from typing import Optional, List, Dict

class OREEPriceParser:
    def __init__(self, raw_dir: str = 'data/raw', processed_dir: str = 'data/processed'):
        self.raw_dir = Path(raw_dir)
        self.processed_dir = Path(processed_dir)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
    
    def try_parse_file(self, filepath: str) -> Optional[pd.DataFrame]:
        """Attempt to parse file with multiple strategies"""
        file_path = Path(filepath)
        
        # Strategy 1: Try as HTML (common for OREE web exports)
        try:
            print(f"🔍 Strategy 1: Reading {file_path.name} as HTML table...")
            # Read first as text to check if it's HTML
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(500)
                if '<table' in content.lower() or '<tr>' in content.lower():
                    dfs = pd.read_html(str(file_path))
                    if dfs:
                        df = dfs[0]
                        print(f"✅ HTML parsing succeeded! Shape: {df.shape}")
                        return df
        except Exception as e:
            print(f"⚠️ HTML parsing failed: {e}")
        
        # Strategy 2: Try as Excel (.xlsx or .xls)
        try:
            print(f"🔍 Strategy 2: Reading {file_path.name} as Excel (.xlsx)...")
            df = pd.read_excel(file_path, engine='openpyxl')
            print(f"✅ Excel parsing succeeded! Shape: {df.shape}")
            return df
        except Exception as e:
            print(f"⚠️ Excel parsing failed: {e}")
        
        # Strategy 3: Try with xlrd (older Excel format)
        try:
            print(f"🔍 Strategy 3: Reading {file_path.name} with xlrd...")
            df = pd.read_excel(file_path, engine='xlrd')
            print(f"✅ xlrd parsing succeeded! Shape: {df.shape}")
            return df
        except Exception as e:
            print(f"⚠️ xlrd parsing failed: {e}")
        
        # Strategy 4: Try reading as text/CSV
        try:
            print(f"🔍 Strategy 4: Reading {file_path.name} as raw text...")
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(2000)
                # Look for CSV-like patterns
                if ',' in content or '\t' in content:
                    df = pd.read_csv(file_path, sep=None, engine='python')
                    print(f"✅ Text parsing succeeded! Shape: {df.shape}")
                    return df
        except Exception as e:
            print(f"⚠️ Text parsing failed: {e}")
        
        print(f"❌ All strategies failed for {file_path.name}")
        return None
    
    def parse_and_save(self, month: str):
        """Parse month file and save as CSV"""
        files_map = {
            '01': 'indexes_01.2026.xls',
            '02': 'indexes_02.2026.xls',
        }
        
        if month not in files_map:
            print(f"❌ Unknown month: {month}")
            return False
        
        file_name = files_map[month]
        file_path = self.raw_dir / file_name
        
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return False
        
        print(f"\n{'='*60}")
        print(f"📊 PARSING: {file_name}")
        print(f"{'='*60}")
        
        df = self.try_parse_file(str(file_path))
        
        if df is not None:
            print(f"\n📊 DataFrame info:")
            print(f"  Shape: {df.shape}")
            print(f"  Columns: {list(df.columns)}")
            print(f"\n📋 First 3 rows:")
            print(df.head(3))
            
            # Clean column names
            df.columns = [str(col).strip() for col in df.columns]
            
            # Save to CSV
            output_file = self.processed_dir / f'hourly_prices_{month}_2026.csv'
            df.to_csv(output_file, index=False)
            print(f"\n✅ Saved to: {output_file}")
            print(f"   Size: {output_file.stat().st_size} bytes")
            
            return True
        else:
            print(f"\n⚠️ Could not parse {file_name}")
            return False
    
    def merge_months(self):
        """Merge January and February data"""
        jan_file = self.processed_dir / 'hourly_prices_01_2026.csv'
        feb_file = self.processed_dir / 'hourly_prices_02_2026.csv'
        
        if not jan_file.exists() or not feb_file.exists():
            print("⚠️ Missing parsed files")
            return None
        
        print(f"\n{'='*60}")
        print(f"🔄 MERGING: January + February 2026")
        print(f"{'='*60}")
        
        df_jan = pd.read_csv(jan_file)
        df_feb = pd.read_csv(feb_file)
        
        df_merged = pd.concat([df_jan, df_feb], ignore_index=True)
        
        output_file = self.processed_dir / 'hourly_prices_jan_feb_2026.csv'
        df_merged.to_csv(output_file, index=False)
        
        print(f"\n✅ Merged dataset:")
        print(f"  January: {len(df_jan)} rows")
        print(f"  February: {len(df_feb)} rows")
        print(f"  Total: {len(df_merged)} rows")
        print(f"  Saved to: {output_file}")
        
        return df_merged


if __name__ == '__main__':
    parser = OREEPriceParser()
    
    # Parse both months
    success_01 = parser.parse_and_save('01')
    success_02 = parser.parse_and_save('02')
    
    # Merge if both succeeded
    if success_01 and success_02:
        parser.merge_months()
    else:
        print("\n⚠️ Could not parse all files, skipping merge")

#!/usr/bin/env python3
"""
Combine available price data sources for ML training
- OREE hourly (Feb 2026)
- SSSU historical (2018-2024)
- Create unified dataset for hybrid ML system
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

def create_combined_dataset():
    processed_dir = Path('data/processed')
    
    # Read OREE February data
    print("📊 LOADING OREE FEBRUARY 2026")
    df_oree_feb = pd.read_csv(processed_dir / 'hourly_prices_02_2026.csv')
    df_oree_feb['Дата'] = pd.to_datetime(df_oree_feb['Дата'], format='%d.%m.%Y')
    df_oree_feb['Month'] = df_oree_feb['Дата'].dt.month
    df_oree_feb['Year'] = df_oree_feb['Дата'].dt.year
    
    print(f"✅ Loaded {len(df_oree_feb)} records from Feb 2026")
    print(f"   Price range: {df_oree_feb['Середньозважена ціна, грн/МВт.год'].min():.2f} - {df_oree_feb['Середньозважена ціна, грн/МВт.год'].max():.2f} UAH/MWh")
    print(f"   Avg weighted price: {df_oree_feb['Середньозважена ціна, грн/МВт.год'].mean():.2f} UAH/MWh\n")
    
    # Look for SSSU data
    sssu_file = processed_dir / 'ukraine_energy_ml_dataset_2026.csv'
    if sssu_file.exists():
        print("📊 LOADING SSSU HISTORICAL DATA")
        df_sssu = pd.read_csv(sssu_file)
        print(f"✅ Loaded SSSU data")
        print(f"   Records: {len(df_sssu)}")
        print(f"   Columns: {list(df_sssu.columns)}\n")
    else:
        print("⚠️ SSSU data not found, using OREE only\n")
        df_sssu = None
    
    # Create summary statistics
    print("="*60)
    print("📈 ENERGY PRICE ANALYSIS (2026)")
    print("="*60)
    print(f"\n🔥 FEBRUARY 2026 CRISIS:")
    print(f"  Base price:           {df_oree_feb['Base, грн/МВт.год'].mean():>10.2f} UAH/MWh")
    print(f"  Peak price:           {df_oree_feb['Peak, грн/МВт.год'].mean():>10.2f} UAH/MWh (+{((df_oree_feb['Peak, грн/МВт.год'].mean() / df_oree_feb['Base, грн/МВт.год'].mean() - 1) * 100):.1f}%)")
    print(f"  Off-Peak price:       {df_oree_feb['OffPeak, грн/МВт.год'].mean():>10.2f} UAH/MWh (-{((1 - df_oree_feb['OffPeak, грн/МВт.год'].mean() / df_oree_feb['Base, грн/МВт.год'].mean()) * 100):.1f}%)")
    print(f"  Weighted avg:         {df_oree_feb['Середньозважена ціна, грн/МВт.год'].mean():>10.2f} UAH/MWh")
    print(f"  Min:                  {df_oree_feb['Мінімальна ціна, грн/МВт.год'].mean():>10.2f} UAH/MWh")
    print(f"  Max:                  {df_oree_feb['Максимальна ціна, грн/МВт.год'].mean():>10.2f} UAH/MWh")
    
    # Calculate volatility
    price_col = 'Середньозважена ціна, грн/МВт.год'
    volatility = df_oree_feb[price_col].std()
    print(f"\n📊 VOLATILITY:")
    print(f"  Std Dev:              {volatility:>10.2f} UAH/MWh")
    print(f"  Coefficient:          {(volatility / df_oree_feb[price_col].mean() * 100):>10.1f}% (CV)")
    
    # Battery arbitrage opportunity
    print(f"\n⚡ BATTERY ARBITRAGE (50kW storage):")
    min_price = df_oree_feb['Мінімальна ціна, грн/МВт.год'].min()
    max_price = df_oree_feb['Максимальна ціна, грн/МВт.год'].max()
    diff = max_price - min_price
    daily_kwh = 50 * 24
    potential_gain = (diff / 1000) * daily_kwh
    print(f"  Min price (buy):      {min_price:>10.2f} UAH/MWh")
    print(f"  Max price (sell):     {max_price:>10.2f} UAH/MWh")
    print(f"  Spread:               {diff:>10.2f} UAH/MWh")
    print(f"  Max daily gain:       {potential_gain:>10.2f} UAH (if perfect arbitrage)")
    
    print(f"\n{'='*60}")
    print(f"✅ Data preparation complete")
    print(f"{'='*60}\n")
    
    return df_oree_feb

if __name__ == '__main__':
    df = create_combined_dataset()
    
    # Save summary
    print("💾 Saving analysis...")
    df.to_csv('data/processed/oree_feb_2026_analysis.csv', index=False)
    print("✅ Saved to data/processed/oree_feb_2026_analysis.csv")

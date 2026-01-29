"""
DEPRECATED: Old optimizer using DUMMY DATA
This file is kept for reference only.

USE INSTEAD: optimizer_real.py
Which uses REAL data from APIs:
  - Real weather from Open-Meteo
  - Real prices from OREE
  - Real/realistic factory loads
"""

import pandas as pd
import numpy as np
import os

def run_optimization():
    """
    ❌ DEPRECATED - Uses hardcoded dummy data
    
    Prices, Solar, and Factory Load are NOT REAL
    This was original POC code only
    
    For production: use optimizer_real.py instead
    """
    print("⚠️  WARNING: Using DEPRECATED optimizer with dummy data!")
    print("✅ USE: optimizer_real.py for real data\n")
    
    print("--- Running Smart Energy Optimization Engine (DUMMY DATA) ---")
    
    hours = list(range(24))
    # ❌ DUMMY PRICES (UAH/kWh)
    prices = [2.5, 2.2, 2.1, 2.0, 2.1, 2.8, 4.5, 6.2, 7.5, 6.8, 5.5, 5.0, 
              4.8, 4.5, 4.2, 5.0, 7.5, 9.2, 11.5, 10.5, 8.5, 6.0, 4.5, 3.5]
    # ❌ DUMMY SOLAR (kW)
    solar_gen = [0, 0, 0, 0, 0, 2, 15, 40, 65, 85, 95, 100, 
                 98, 88, 70, 45, 20, 5, 0, 0, 0, 0, 0, 0]
    # ❌ DUMMY FACTORY LOAD (kW)
    factory_load = [50] * 24 
    
    battery_capacity = 200 # kWh
    soc = 20.0 # %
    results = []
    
    for h in hours:
        p, g, l = prices[h], solar_gen[h], factory_load[h]
        action = "BUY FROM GRID"
        net = l - g
        
        if net < 0: # Excess Solar
            if soc < 95:
                action = "STORE SOLAR"
                soc += (abs(net) / battery_capacity) * 100
            else:
                action = "SELL TO GRID"
        else: # Deficit
            if p > 8.0 and soc > 20: # Expensive evening
                action = "DISCHARGE BATTERY"
                soc -= (net / battery_capacity) * 100
            elif p < 3.0 and soc < 90: # Cheap night
                action = "CHARGE FROM GRID"
                soc += 15.0 # Constant charge rate
            else:
                action = "BUY FROM GRID"
        
        soc = max(0.0, min(100.0, soc))
        results.append({'Hour': h, 'Price': p, 'Solar': g, 'Action': action, 'SOC': round(soc, 1)})

    df = pd.DataFrame(results)
    print(df.to_string(index=False))
    
    out_dir = 'projects/smart-energy-ai/data/processed'
    if not os.path.exists(out_dir): os.makedirs(out_dir)
    df.to_csv(f'{out_dir}/optimization_results.csv', index=False)
    print(f"\nSaved to {out_dir}/optimization_results.csv")
    print("\n⚠️  This data is DUMMY - not for production use!")

if __name__ == "__main__":
    run_optimization()

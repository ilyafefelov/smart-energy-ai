"""
DEPRECATED: Old optimizer_v2 using DUMMY DATA
This file is kept for reference only.

USE INSTEAD: optimizer_real.py
Which uses REAL data from APIs:
  - Real weather from Open-Meteo
  - Real prices from OREE
  - Real/realistic factory loads with scenario modifiers
"""

import pandas as pd
import numpy as np
import os

def run_optimized_scenario(scenario="Normal", solar_mult=1.0, load_mult=1.0):
    """
    ❌ DEPRECATED - Uses hardcoded dummy data
    
    Prices, Solar, and Factory Load are NOT REAL
    This was original POC code only
    
    For production: use optimizer_real.py instead
    """
    print(f"⚠️  WARNING: Using DEPRECATED optimizer_v2 with dummy data!")
    print(f"✅ USE: optimizer_real.py for real data\n")
    
    print(f"--- Running Scenario: {scenario} (DUMMY DATA) ---")
    
    hours = list(range(24))
    # ❌ DUMMY PRICES
    prices = [2.5, 2.2, 2.1, 2.0, 2.1, 2.8, 4.5, 6.2, 7.5, 6.8, 5.5, 5.0, 
              4.8, 4.5, 4.2, 5.0, 7.5, 9.2, 11.5, 10.5, 8.5, 6.0, 4.5, 3.5]
    # ❌ DUMMY SOLAR
    solar_gen = [0, 0, 0, 0, 0, 2, 15, 40, 65, 85, 95, 100, 
                 98, 88, 70, 45, 20, 5, 0, 0, 0, 0, 0, 0]
    # ❌ DUMMY FACTORY LOAD
    factory_load = [50] * 24 

    # Apply scenario modifiers
    if scenario == "Winter":
        solar_mult *= 0.2 # 80% less sun
        load_mult *= 1.3  # 30% more heating load
    elif scenario == "Blackout":
        prices = [0] * 24 # Grid is gone
        solar_mult *= 1.0 
        load_mult *= 0.5  # Only critical load (50% of normal)
    
    battery_capacity = 300 
    soc = 50.0 # Start mid-day
    results = []
    
    for h in hours:
        p = prices[h]
        g = solar_gen[h] * solar_mult
        l = factory_load[h] * load_mult
        net = l - g
        action = "BUY FROM GRID"
        
        if scenario == "Blackout":
            if net < 0:
                action = "OFF-GRID: STORE SOLAR"
                soc += (abs(net) / battery_capacity) * 100
            elif soc > 10:
                action = "OFF-GRID: USE BATTERY"
                soc -= (net / battery_capacity) * 100
            else:
                action = "OFF-GRID: DIESEL GEN START"
        else:
            if net < 0:
                if soc < 95:
                    action = "STORE SOLAR"
                    soc += (abs(net) / battery_capacity) * 100
                else: action = "SELL TO GRID"
            else:
                if p > 8.0 and soc > 20:
                    action = "DISCHARGE BATTERY"
                    soc -= (net / battery_capacity) * 100
                elif p < 3.0 and soc < 90:
                    action = "CHARGE FROM GRID"
                    soc += 10.0
                else: action = "BUY FROM GRID"
        
        soc = max(0.0, min(100.0, soc))
        results.append({'Hour': h, 'Price': p, 'Solar': round(g, 1), 'Action': action, 'SOC': round(soc, 1)})

    df = pd.DataFrame(results)
    out_dir = 'projects/smart-energy-ai/data/processed'
    if not os.path.exists(out_dir): os.makedirs(out_dir)
    df.to_csv(f'{out_dir}/opt_{scenario.lower()}.csv', index=False)
    
    print(df.to_string(index=False))
    print(f"\n⚠️  This data is DUMMY - not for production use!")
    return df

if __name__ == "__main__":
    for s in ["Normal", "Winter", "Blackout"]:
        run_optimized_scenario(s)

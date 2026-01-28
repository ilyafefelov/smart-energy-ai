import pandas as pd
import numpy as np
import os

def run_optimization():
    print("--- Running Smart Energy Optimization Engine ---")
    
    hours = list(range(24))
    # Prices (UAH/kWh), Solar (kW), Factory Load (kW)
    prices = [2.5, 2.2, 2.1, 2.0, 2.1, 2.8, 4.5, 6.2, 7.5, 6.8, 5.5, 5.0, 
              4.8, 4.5, 4.2, 5.0, 7.5, 9.2, 11.5, 10.5, 8.5, 6.0, 4.5, 3.5]
    solar_gen = [0, 0, 0, 0, 0, 2, 15, 40, 65, 85, 95, 100, 
                 98, 88, 70, 45, 20, 5, 0, 0, 0, 0, 0, 0]
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

if __name__ == "__main__":
    run_optimization()

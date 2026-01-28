import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def generate_business_plots():
    df = pd.read_csv('projects/smart-energy-ai/data/processed/optimization_results.csv')
    
    # Let's simulate energy flow components based on actions
    # Factory Load is constant 50 in our simulation
    load = 50
    solar = df['Solar']
    
    from_solar = []
    from_battery = []
    from_grid = []
    to_grid_sell = []
    
    for i, row in df.iterrows():
        s = row['Solar']
        act = row['Action']
        
        if act == "SELL TO GRID":
            from_solar.append(load) # used solar for load
            from_battery.append(0)
            from_grid.append(0)
            to_grid_sell.append(s - load)
        elif act == "DISCHARGE BATTERY":
            from_solar.append(s)
            from_battery.append(load - s)
            from_grid.append(0)
            to_grid_sell.append(0)
        elif act == "CHARGE FROM GRID":
            from_solar.append(s)
            from_battery.append(0)
            from_grid.append(load) # simplified: we buy for load + buy for battery
            to_grid_sell.append(0)
        else: # BUY FROM GRID or STORE SOLAR
            from_solar.append(min(s, load))
            from_battery.append(0)
            from_grid.append(max(0, load - s))
            to_grid_sell.append(0)

    # Plotting
    plt.figure(figsize=(14, 8))
    x = df['Hour']
    
    plt.stackplot(x, from_solar, from_battery, from_grid, 
                  labels=['Used Solar (Free)', 'Used Battery (Stored)', 'Bought from Grid (Cost)'],
                  colors=['#ffcc00', '#00cc96', '#ff5555'], alpha=0.7)
    
    plt.plot(x, [load]*24, color='black', linestyle='--', linewidth=2, label='Factory Demand')
    
    # Adding Sell events
    sell_x = [i for i, v in enumerate(to_grid_sell) if v > 0]
    sell_y = [to_grid_sell[i] for i in sell_x]
    if sell_x:
        plt.bar(sell_x, sell_y, bottom=load, color='#3399ff', alpha=0.6, label='Sold to Grid (Profit)')

    plt.title('Energy Balance & Financial Optimization Strategy', fontsize=16)
    plt.xlabel('Hour of Day', fontsize=12)
    plt.ylabel('Energy Flow (kWh)', fontsize=12)
    plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
    plt.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('projects/smart-energy-ai/plots/energy_balance_business.png')
    plt.close()
    print("Business plot saved.")

if __name__ == "__main__":
    if not os.path.exists('projects/smart-energy-ai/plots'): os.makedirs('projects/smart-energy-ai/plots')
    generate_business_plots()

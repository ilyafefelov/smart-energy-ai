import pandas as pd
import matplotlib.pyplot as plt
import os

def generate_plots():
    df = pd.read_csv('projects/smart-energy-ai/data/processed/optimization_results.csv')
    
    # 1. Price & Solar Plot
    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax1.set_xlabel('Hour of Day')
    ax1.set_ylabel('Price (UAH)', color='tab:red')
    ax1.plot(df['Hour'], df['Price'], color='tab:red', linewidth=3, label='Price')
    ax1.tick_params(axis='y', labelcolor='tab:red')

    ax2 = ax1.twinx()
    ax2.set_ylabel('Solar Gen (kW)', color='tab:orange')
    ax2.bar(df['Hour'], df['Solar'], color='tab:orange', alpha=0.4, label='Solar')
    ax2.tick_params(axis='y', labelcolor='tab:orange')

    plt.title('Market Price & Solar Generation')
    plt.grid(True, alpha=0.3)
    plt.savefig('projects/smart-energy-ai/plots/price_solar_mpl.png')
    plt.close()

    # 2. Battery SOC Plot
    plt.figure(figsize=(12, 6))
    plt.fill_between(df['Hour'], df['SOC'], color="skyblue", alpha=0.4)
    plt.plot(df['Hour'], df['SOC'], color="Slateblue", alpha=0.6, linewidth=2)
    plt.title('Battery State of Charge (SOC) %')
    plt.xlabel('Hour of Day')
    plt.ylabel('Charge %')
    plt.grid(True, alpha=0.3)
    plt.savefig('projects/smart-energy-ai/plots/battery_soc_mpl.png')
    plt.close()
    
    print("Static plots saved successfully via Matplotlib.")

if __name__ == "__main__":
    if not os.path.exists('projects/smart-energy-ai/plots'): os.makedirs('projects/smart-energy-ai/plots')
    generate_plots()

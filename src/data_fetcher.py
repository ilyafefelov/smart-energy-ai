import pandas as pd
import datetime

def fetch_sample_energy_data():
    print("Initializing data collection for Step 1...")
    # Create 24 hours of sample data
    base = datetime.datetime(2024, 1, 1, 0, 0)
    timestamps = [base + datetime.timedelta(hours=x) for x in range(24)]
    
    # Typical price curve (low at night, peak in morning and evening)
    prices = [65.2, 58.1, 55.0, 52.3, 54.0, 60.5, 75.2, 88.0, 95.1, 92.0, 85.5, 80.0, 
              78.2, 77.5, 82.0, 90.5, 110.2, 125.0, 115.3, 105.0, 95.5, 88.0, 80.2, 70.0]
              
    # Typical solar curve (peak at noon)
    solar = [0, 0, 0, 0, 0, 5, 25, 60, 120, 180, 220, 240, 
             235, 210, 160, 90, 30, 5, 0, 0, 0, 0, 0, 0]
             
    df = pd.DataFrame({
        'timestamp': timestamps,
        'price_eur_mwh': prices,
        'solar_gen_kw': solar
    })
    
    output_path = 'projects/smart-energy-ai/data/raw/sample_energy_data.csv'
    df.to_csv(output_path, index=False)
    print(f"Sample data saved to {output_path}")
    print("\n--- DATA PREVIEW ---")
    print(df.head(10))
    return df

if __name__ == "__main__":
    fetch_sample_energy_data()

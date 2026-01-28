import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import joblib

def train_baseline():
    print("--- Starting Baseline Training ---")
    # Load the data we generated in Step 1
    df = pd.read_csv('projects/smart-energy-ai/data/raw/sample_energy_data.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Feature Engineering: Extract hour of the day
    df['hour'] = df['timestamp'].dt.hour
    
    # Let's say we want to predict 'price_eur_mwh' based on 'hour'
    X = df[['hour']]
    y = df['price_eur_mwh']
    
    # Since we have very little data (24h), we'll just demonstrate the fit
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    # Save the model
    model_path = 'projects/smart-energy-ai/src/baseline_price_model.joblib'
    joblib.dump(model, model_path)
    print(f"Model trained and saved to {model_path}")
    
    # Quick prediction for tomorrow morning (8 AM)
    test_hour = np.array([[8]])
    prediction = model.predict(test_hour)
    print(f"Predicted price for hour 8: {prediction[0]:.2f} EUR/MWh")
    
    return model

if __name__ == "__main__":
    train_baseline()

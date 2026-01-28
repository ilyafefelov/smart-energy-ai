import requests
import pandas as pd
import datetime

def fetch_weather_forecast(lat=50.45, lon=30.52): # Kyiv coordinates
    print(f"Fetching weather forecast for Kyiv ({lat}, {lon})...")
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,shortwave_radiation,cloud_cover&forecast_days=3"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        hourly = data['hourly']
        df = pd.DataFrame({
            'timestamp': pd.to_datetime(hourly['time']),
            'temp': hourly['temperature_2m'],
            'radiation': hourly['shortwave_radiation'], # Direct solar energy
            'clouds': hourly['cloud_cover']
        })
        path = 'projects/smart-energy-ai/data/raw/weather_forecast.csv'
        df.to_csv(path, index=False)
        print(f"Weather data saved to {path}")
        print(df.head(5))
    else:
        print("Failed to fetch weather data.")

if __name__ == '__main__':
    fetch_weather_forecast()

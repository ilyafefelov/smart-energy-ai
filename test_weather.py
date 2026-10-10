#!/usr/bin/env python3
"""Test real weather data"""

import sys
sys.path.insert(0, '.')
from src.data_pipeline.ingest_weather import WeatherIngester

print('\nTesting REAL WEATHER DATA from Open-Meteo\n')
print('=' * 60)

ingester = WeatherIngester()
weather_data = ingester.fetch_weather()

if weather_data:
    weather_df = ingester.parse_weather_data(weather_data)
    print('✅ REAL WEATHER DATA - TODAY IN KYIV')
    print('=' * 60)
    cols_to_show = ['temperature', 'solar_radiation', 'cloudcover', 'wind_speed', 'humidity']
    print(weather_df[cols_to_show].to_string())
    print()
    print(f'✅ Real data: {len(weather_df)} hours')
    
    temp_min = weather_df['temperature'].min()
    temp_max = weather_df['temperature'].max()
    print(f'✅ Temperature range: {temp_min:.1f}C to {temp_max:.1f}C')
    
    solar_min = weather_df['solar_radiation'].min()
    solar_max = weather_df['solar_radiation'].max()
    print(f'✅ Solar range: {solar_min:.0f} to {solar_max:.0f} W/m2')
    
    cloud_min = weather_df['cloudcover'].min()
    cloud_max = weather_df['cloudcover'].max()
    print(f'✅ Cloud cover: {cloud_min:.0f}% to {cloud_max:.0f}%')
else:
    print('❌ Failed to fetch weather')

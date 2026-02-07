"""Test script to verify Dagster assets work."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from energy_ml.assets.data_sources import (
    weather_data,
    solar_irradiance,
    wind_potential,
    battery_state,
    price_data_current,
)

print("=" * 60)
print("🧪 Testing Energy ML Assets")
print("=" * 60)

try:
    print("\n1️⃣ Testing weather_data asset...")
    weather_result = weather_data()
    if hasattr(weather_result, 'value'):
        print(f"   ✅ Got weather data: {weather_result.value.to_dict(orient='records')[0]}")
    else:
        print(f"   ✅ Asset executed (result type: {type(weather_result)})")
except Exception as e:
    print(f"   ❌ Error: {e}")

try:
    print("\n2️⃣ Testing battery_state asset...")
    battery_result = battery_state()
    if hasattr(battery_result, 'value'):
        print(f"   ✅ Got battery data: {battery_result.value.to_dict(orient='records')[0]}")
    else:
        print(f"   ✅ Asset executed")
except Exception as e:
    print(f"   ❌ Error: {e}")

try:
    print("\n3️⃣ Testing price_data_current asset...")
    price_result = price_data_current()
    if hasattr(price_result, 'value'):
        print(f"   ✅ Got price data: {price_result.value.to_dict(orient='records')[0]}")
    else:
        print(f"   ✅ Asset executed")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("✅ Basic asset tests complete!")
print("=" * 60)
print("\nNext step: Run 'dagster dev' in this directory")
print("Then open http://localhost:3000 in your browser")

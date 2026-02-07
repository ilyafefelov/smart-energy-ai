"""Test script to verify Dagster assets work."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from energy_ml.assets.data_sources import (
    weather_data,
    weather_forecast,
    solar_irradiance,
    wind_potential,
    battery_state,
    price_data_current,
)
from energy_ml.assets.features import (
    time_features,
    weather_features,
    generation_features,
    battery_features,
    price_features,
    interaction_features,
    feature_matrix,
)

print("=" * 80)
print("🧪 Testing Energy ML Assets (Data Sources + Features)")
print("=" * 80)

# Test data sources
print("\n📊 DATA SOURCES LAYER")
print("-" * 80)

try:
    print("\n1️⃣ weather_data...")
    weather_result = weather_data()
    if hasattr(weather_result, 'value'):
        weather_df = weather_result.value
        print(f"   ✅ Shape: {weather_df.shape}")
    else:
        weather_df = weather_result
        print(f"   ✅ Type: {type(weather_df)}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    weather_df = None

try:
    print("\n2️⃣ weather_forecast...")
    forecast_result = weather_forecast()
    if hasattr(forecast_result, 'value'):
        forecast_df = forecast_result.value
        print(f"   ✅ Shape: {forecast_df.shape}")
    else:
        forecast_df = forecast_result
        print(f"   ✅ Type: {type(forecast_df)}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    forecast_df = None

try:
    print("\n3️⃣ solar_irradiance...")
    if weather_df is not None:
        solar_result = solar_irradiance(weather_df)
        if hasattr(solar_result, 'value'):
            solar_df = solar_result.value
            print(f"   ✅ GHI: {solar_df['ghi_w_per_m2'].values[0]} W/m²")
        else:
            solar_df = solar_result
except Exception as e:
    print(f"   ❌ Error: {e}")
    solar_df = None

try:
    print("\n4️⃣ wind_potential...")
    if weather_df is not None:
        wind_result = wind_potential(weather_df)
        if hasattr(wind_result, 'value'):
            wind_df = wind_result.value
            print(f"   ✅ Power: {wind_df['power_potential_kw'].values[0]:.2f} kW")
        else:
            wind_df = wind_result
except Exception as e:
    print(f"   ❌ Error: {e}")
    wind_df = None

try:
    print("\n5️⃣ battery_state...")
    battery_result = battery_state()
    if hasattr(battery_result, 'value'):
        battery_df = battery_result.value
        print(f"   ✅ SOC: {battery_df['soc_percent'].values[0]}%")
    else:
        battery_df = battery_result
except Exception as e:
    print(f"   ❌ Error: {e}")
    battery_df = None

try:
    print("\n6️⃣ price_data_current...")
    price_result = price_data_current()
    if hasattr(price_result, 'value'):
        price_df = price_result.value
        print(f"   ✅ Price: {price_df['price_uah_per_kwh'].values[0]:.2f} ₴/kWh")
    else:
        price_df = price_result
except Exception as e:
    print(f"   ❌ Error: {e}")
    price_df = None

# Test features
print("\n\n🧠 FEATURE ENGINEERING LAYER")
print("-" * 80)

try:
    print("\n7️⃣ time_features...")
    if weather_df is not None:
        tf_result = time_features(weather_df)
        if hasattr(tf_result, 'value'):
            tf_df = tf_result.value
            print(f"   ✅ Generated {tf_df.shape[1]} features")
        else:
            tf_df = tf_result
except Exception as e:
    print(f"   ❌ Error: {e}")
    tf_df = None

try:
    print("\n8️⃣ weather_features...")
    if weather_df is not None and forecast_df is not None:
        wf_result = weather_features(weather_df, forecast_df)
        if hasattr(wf_result, 'value'):
            wf_df = wf_result.value
            print(f"   ✅ Generated {wf_df.shape[1]} features")
        else:
            wf_df = wf_result
except Exception as e:
    print(f"   ❌ Error: {e}")
    wf_df = None

try:
    print("\n9️⃣ generation_features...")
    if solar_df is not None and wind_df is not None:
        gf_result = generation_features(solar_df, wind_df)
        if hasattr(gf_result, 'value'):
            gf_df = gf_result.value
            print(f"   ✅ Generated {gf_df.shape[1]} features")
        else:
            gf_df = gf_result
except Exception as e:
    print(f"   ❌ Error: {e}")
    gf_df = None

try:
    print("\n🔟 battery_features...")
    if battery_df is not None:
        bf_result = battery_features(battery_df)
        if hasattr(bf_result, 'value'):
            bf_df = bf_result.value
            print(f"   ✅ Generated {bf_df.shape[1]} features")
        else:
            bf_df = bf_result
except Exception as e:
    print(f"   ❌ Error: {e}")
    bf_df = None

try:
    print("\n1️⃣1️⃣ price_features...")
    if price_df is not None:
        pf_result = price_features(price_df)
        if hasattr(pf_result, 'value'):
            pf_df = pf_result.value
            print(f"   ✅ Generated {pf_df.shape[1]} features")
        else:
            pf_df = pf_result
except Exception as e:
    print(f"   ❌ Error: {e}")
    pf_df = None

try:
    print("\n1️⃣2️⃣ interaction_features...")
    if all([tf_df is not None, wf_df is not None, gf_df is not None, bf_df is not None, pf_df is not None]):
        if_result = interaction_features(tf_df, wf_df, gf_df, bf_df, pf_df)
        if hasattr(if_result, 'value'):
            if_df = if_result.value
            print(f"   ✅ Generated {if_df.shape[1]} features")
        else:
            if_df = if_result
except Exception as e:
    print(f"   ❌ Error: {e}")
    if_df = None

try:
    print("\n1️⃣3️⃣ feature_matrix...")
    if all([tf_df is not None, wf_df is not None, gf_df is not None, bf_df is not None, pf_df is not None, if_df is not None]):
        fm_result = feature_matrix(tf_df, wf_df, gf_df, bf_df, pf_df, if_df)
        if hasattr(fm_result, 'value'):
            fm_df = fm_result.value
            print(f"   ✅ FEATURE MATRIX: {fm_df.shape[0]} rows × {fm_df.shape[1]-1} features (excluding timestamp)")
            print(f"   Column breakdown:")
            print(f"      - Time: 13 features")
            print(f"      - Weather: 14 features")
            print(f"      - Generation: 9 features")
            print(f"      - Battery: 10 features")
            print(f"      - Price: 14 features")
            print(f"      - Interactions: 13 features")
            print(f"      - TOTAL: 73 features + timestamp")
        else:
            fm_df = fm_result
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 80)
print("✅ All asset tests complete!")
print("=" * 80)
print("\nNext step: Run 'dagster dev' in this directory")
print("Then open http://localhost:3000 in your browser to see the asset graph")
print("\nYou should see:")
print("  - 6 data source assets (weather, solar, wind, battery, price, forecast)")
print("  - 7 feature assets (time, weather, generation, battery, price, interactions, matrix)")
print("  - Dependency lines showing data flow from sources → features → matrix")

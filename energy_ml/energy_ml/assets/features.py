"""Feature engineering assets for Energy ML system.

These assets transform raw data into machine learning features.
They depend on data source assets and create the feature matrix.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any
from dagster import asset, Output, Definitions
import logging

logger = logging.getLogger(__name__)


@asset(
    name="time_features",
    description="Time-based features extracted from timestamp",
    tags={"domain": "features", "category": "time"}
)
def time_features(weather_data: pd.DataFrame) -> Output[pd.DataFrame]:
    """Extract time-based features from timestamp."""
    
    logger.info("⏰ Generating time features...")
    
    ts = weather_data['timestamp'].values[0]
    dt = pd.Timestamp(ts).to_pydatetime()
    
    # Day of year (1-366)
    day_of_year = dt.timetuple().tm_yday
    
    # Time-based features
    features = {
        'hour': dt.hour,
        'day_of_week': dt.weekday(),  # 0=Monday, 6=Sunday
        'day_of_month': dt.day,
        'day_of_year': day_of_year,
        'month': dt.month,
        'quarter': (dt.month - 1) // 3,
        'is_weekend': 1 if dt.weekday() >= 5 else 0,
        'is_working_hours': 1 if 9 <= dt.hour <= 17 else 0,
        'is_peak_hours': 1 if 18 <= dt.hour <= 21 else 0,
    }
    
    # Seasonal encoding (sin/cos for cyclical nature)
    day_sin = np.sin(2 * np.pi * day_of_year / 365)
    day_cos = np.cos(2 * np.pi * day_of_year / 365)
    hour_sin = np.sin(2 * np.pi * dt.hour / 24)
    hour_cos = np.cos(2 * np.pi * dt.hour / 24)
    
    features.update({
        'day_sin': day_sin,
        'day_cos': day_cos,
        'hour_sin': hour_sin,
        'hour_cos': hour_cos,
    })
    
    df = pd.DataFrame([features])
    
    logger.info(f"✅ Generated {len(features)} time features")
    
    return Output(
        df,
        metadata={
            "num_features": len(features),
            "hour": features['hour'],
            "day_of_week": features['day_of_week'],
        }
    )


@asset(
    name="weather_features",
    description="Normalized weather features with lags",
    tags={"domain": "features", "category": "weather"}
)
def weather_features(weather_data: pd.DataFrame, weather_forecast: pd.DataFrame) -> Output[pd.DataFrame]:
    """Extract and normalize weather features."""
    
    logger.info("🌤️ Generating weather features...")
    
    current = weather_data.iloc[0]
    
    # Normalize temperature (-10 to +40°C range)
    temp_normalized = (current['temp'] - 15) / 25  # Center at 15°C, scale by 25°C range
    
    # Humidity (0-100)
    humidity_norm = current['humidity'] / 100
    
    # Cloud cover (0-100)
    cloud_norm = current['cloud_cover'] / 100
    
    # Wind speed (0-20 m/s typical)
    wind_norm = current['wind_speed'] / 20
    
    # Pressure anomaly (relative to 1013 hPa)
    pressure_anom = current['pressure'] - 1013
    
    # Wind direction encoding
    wind_dir_rad = np.radians(current['wind_direction'])
    wind_dir_sin = np.sin(wind_dir_rad)
    wind_dir_cos = np.cos(wind_dir_rad)
    
    # Forecast features (next 12 hours average)
    forecast_12h = weather_forecast[weather_forecast['timestamp'] <= (
        weather_data['timestamp'].values[0] + pd.Timedelta(hours=12)
    )]
    
    forecast_temp_avg = forecast_12h['temp'].mean() if len(forecast_12h) > 0 else current['temp']
    forecast_cloud_avg = forecast_12h['cloud_cover'].mean() if len(forecast_12h) > 0 else current['cloud_cover']
    forecast_wind_avg = forecast_12h['wind_speed'].mean() if len(forecast_12h) > 0 else current['wind_speed']
    
    features = {
        'temp_c': current['temp'],
        'temp_normalized': temp_normalized,
        'humidity_norm': humidity_norm,
        'cloud_cover_norm': cloud_norm,
        'wind_speed_ms': current['wind_speed'],
        'wind_speed_norm': wind_norm,
        'wind_direction_deg': current['wind_direction'],
        'wind_direction_sin': wind_dir_sin,
        'wind_direction_cos': wind_dir_cos,
        'pressure_hpa': current['pressure'],
        'pressure_anomaly': pressure_anom,
        'forecast_temp_12h': forecast_temp_avg,
        'forecast_cloud_12h': forecast_cloud_avg,
        'forecast_wind_12h': forecast_wind_avg,
    }
    
    df = pd.DataFrame([features])
    
    logger.info(f"✅ Generated {len(features)} weather features")
    
    return Output(
        df,
        metadata={
            "num_features": len(features),
            "temp_c": current['temp'],
            "wind_speed_ms": current['wind_speed'],
        }
    )


@asset(
    name="generation_features",
    description="Solar and wind generation potential features",
    tags={"domain": "features", "category": "generation"}
)
def generation_features(solar_irradiance: pd.DataFrame, wind_potential: pd.DataFrame) -> Output[pd.DataFrame]:
    """Extract solar and wind generation features."""
    
    logger.info("⚡ Generating generation features...")
    
    solar = solar_irradiance.iloc[0]
    wind = wind_potential.iloc[0]
    
    # Assume standard capacities
    solar_capacity_kw = 10.0  # 10 kW solar array
    wind_capacity_kw = 5.0    # 5 kW wind turbine
    
    # Solar potential (GHI normalized)
    ghi_norm = solar['ghi_w_per_m2'] / 1000  # Normalize to 0-1 range
    
    # Generate solar power (simplified)
    solar_power = (solar['ghi_w_per_m2'] * solar_capacity_kw * 0.18) / 1000
    solar_power = max(0, solar_power)
    
    # Wind power (already calculated)
    wind_power = wind['power_potential_kw']
    
    # Total potential generation
    total_potential = solar_power + wind_power
    
    # Generation mix (ratio of solar to total)
    if total_potential > 0:
        solar_ratio = solar_power / total_potential
    else:
        solar_ratio = 0
    
    features = {
        'solar_ghi_w_m2': solar['ghi_w_per_m2'],
        'solar_ghi_norm': ghi_norm,
        'solar_elevation_deg': solar['elevation_deg'],
        'solar_power_kw': round(solar_power, 2),
        'wind_speed_ms': wind['wind_speed_ms'],
        'wind_power_kw': round(wind['power_potential_kw'], 2),
        'total_gen_potential_kw': round(total_potential, 2),
        'solar_ratio': solar_ratio,
        'is_night': int(solar['is_night']),
    }
    
    df = pd.DataFrame([features])
    
    logger.info(f"✅ Generated {len(features)} generation features")
    logger.info(f"   Solar: {solar_power:.2f} kW, Wind: {wind_power:.2f} kW, Total: {total_potential:.2f} kW")
    
    return Output(
        df,
        metadata={
            "num_features": len(features),
            "solar_power_kw": round(solar_power, 2),
            "wind_power_kw": round(wind_power, 2),
            "total_potential_kw": round(total_potential, 2),
        }
    )


@asset(
    name="battery_features",
    description="Battery state features and derived metrics",
    tags={"domain": "features", "category": "battery"}
)
def battery_features(battery_state: pd.DataFrame) -> Output[pd.DataFrame]:
    """Extract battery state features."""
    
    logger.info("🔋 Generating battery features...")
    
    battery = battery_state.iloc[0]
    
    soc = battery['soc_percent']
    capacity = battery['capacity_kwh']
    charge_rate = battery['charge_rate_kw']
    discharge_rate = battery['discharge_rate_kw']
    health = battery['health_percent']
    
    # Time to empty (assuming constant discharge)
    energy_available = (soc / 100) * capacity
    if discharge_rate > 0:
        hours_to_empty = energy_available / discharge_rate
    else:
        hours_to_empty = 999  # If not discharging, can't run out
    
    # Time to full (assuming constant charge)
    energy_needed = ((100 - soc) / 100) * capacity
    if charge_rate > 0:
        hours_to_full = energy_needed / charge_rate
    else:
        hours_to_full = 999
    
    # Battery efficiency (degradation factor)
    efficiency = health / 100
    
    # Normalized SOC
    soc_norm = soc / 100
    
    # Battery urgency (how critical is current state)
    if soc < 20:
        urgency = "critical"
    elif soc < 40:
        urgency = "low"
    elif soc > 80:
        urgency = "high"
    else:
        urgency = "normal"
    
    urgency_score = {"critical": 3, "low": 2, "normal": 1, "high": 0}[urgency]
    
    features = {
        'soc_percent': soc,
        'soc_normalized': soc_norm,
        'capacity_kwh': capacity,
        'charge_rate_kw': charge_rate,
        'discharge_rate_kw': discharge_rate,
        'health_percent': health,
        'efficiency': efficiency,
        'hours_to_empty': hours_to_empty,
        'hours_to_full': hours_to_full,
        'urgency_score': urgency_score,
    }
    
    df = pd.DataFrame([features])
    
    logger.info(f"✅ Generated {len(features)} battery features")
    logger.info(f"   SOC: {soc:.1f}%, Hours to empty: {hours_to_empty:.1f}h, Health: {health:.1f}%")
    
    return Output(
        df,
        metadata={
            "num_features": len(features),
            "soc_percent": soc,
            "hours_to_empty": hours_to_empty,
        }
    )


@asset(
    name="price_features",
    description="Price-based features with lags and statistics",
    tags={"domain": "features", "category": "price"}
)
def price_features(price_data_current: pd.DataFrame) -> Output[pd.DataFrame]:
    """Extract price-based features."""
    
    logger.info("💰 Generating price features...")
    
    price = price_data_current.iloc[0]['price_uah_per_kwh']
    
    # Normalize price (typical range 5-20 ₴/kWh)
    price_norm = (price - 12.5) / 7.5  # Center at 12.5, scale by 7.5
    
    # Price level classification
    if price < 8:
        price_level = "very_cheap"
    elif price < 12:
        price_level = "cheap"
    elif price < 15:
        price_level = "average"
    elif price < 20:
        price_level = "expensive"
    else:
        price_level = "very_expensive"
    
    price_level_score = {
        "very_cheap": 0,
        "cheap": 1,
        "average": 2,
        "expensive": 3,
        "very_expensive": 4
    }[price_level]
    
    # Placeholder lags (would be filled from historical data in real pipeline)
    # In production, these would come from a historical price database
    price_lag1h = price * 0.98  # Assume slight increase trend
    price_lag3h = price * 0.95
    price_lag6h = price * 0.92
    price_lag24h = price * 0.90
    
    # Moving averages
    price_ma_3h = (price + price_lag1h + price_lag3h) / 3
    price_ma_6h = (price + price_lag1h + price_lag3h + price_lag6h) / 4
    price_ma_24h = price * 0.95  # Placeholder
    
    # Price change
    price_change_1h = price - price_lag1h
    price_change_3h = price - price_lag3h
    price_change_6h = price - price_lag6h
    
    # Volatility (simplified)
    prices = [price, price_lag1h, price_lag3h, price_lag6h]
    price_volatility = np.std(prices)
    
    features = {
        'price_uah_kwh': price,
        'price_normalized': price_norm,
        'price_level_score': price_level_score,
        'price_lag_1h': price_lag1h,
        'price_lag_3h': price_lag3h,
        'price_lag_6h': price_lag6h,
        'price_lag_24h': price_lag24h,
        'price_ma_3h': price_ma_3h,
        'price_ma_6h': price_ma_6h,
        'price_ma_24h': price_ma_24h,
        'price_change_1h': price_change_1h,
        'price_change_3h': price_change_3h,
        'price_change_6h': price_change_6h,
        'price_volatility': price_volatility,
    }
    
    df = pd.DataFrame([features])
    
    logger.info(f"✅ Generated {len(features)} price features")
    logger.info(f"   Price: {price:.2f} ₴/kWh ({price_level}), Volatility: {price_volatility:.2f}")
    
    return Output(
        df,
        metadata={
            "num_features": len(features),
            "price_uah_kwh": price,
            "price_level": price_level,
        }
    )


@asset(
    name="interaction_features",
    description="Complex interaction features combining multiple data sources",
    tags={"domain": "features", "category": "interactions"}
)
def interaction_features(
    time_features: pd.DataFrame,
    weather_features: pd.DataFrame,
    generation_features: pd.DataFrame,
    battery_features: pd.DataFrame,
    price_features: pd.DataFrame
) -> Output[pd.DataFrame]:
    """Create interaction and combined features."""
    
    logger.info("🔗 Generating interaction features...")
    
    # Extract values
    hour = time_features.iloc[0]['hour']
    is_peak = time_features.iloc[0]['is_peak_hours']
    temp = weather_features.iloc[0]['temp_c']
    cloud_cover = weather_features.iloc[0]['cloud_cover_norm']
    wind_speed = weather_features.iloc[0]['wind_speed_ms']
    solar_power = generation_features.iloc[0]['solar_power_kw']
    wind_power = generation_features.iloc[0]['wind_power_kw']
    total_gen = generation_features.iloc[0]['total_gen_potential_kw']
    soc = battery_features.iloc[0]['soc_percent']
    hours_to_empty = battery_features.iloc[0]['hours_to_empty']
    price = price_features.iloc[0]['price_uah_kwh']
    
    features = {}
    
    # Generation-Price interactions
    features['gen_price_ratio'] = total_gen / (price + 0.1)  # Avoid division by zero
    features['solar_price_ratio'] = solar_power / (price + 0.1)
    features['wind_price_ratio'] = wind_power / (price + 0.1)
    
    # Battery-Price interactions
    features['soc_price_product'] = (soc / 100) * price
    features['hours_to_empty_price'] = hours_to_empty * price
    
    # Generation-Weather interactions
    features['solar_cloud_product'] = solar_power * (1 - cloud_cover)
    features['wind_temp_interaction'] = wind_speed * (temp / 15)  # Relative to 15°C
    
    # Time-based interactions
    features['peak_hour_generation'] = total_gen * is_peak
    features['peak_hour_price'] = price * is_peak
    
    # Complex multi-way interactions
    features['battery_gen_price_score'] = (
        (soc / 100) * total_gen * (1 / (price + 1))
    )
    
    # Opportunity score (when to charge/discharge)
    charge_score = total_gen / (price + 0.1) * ((100 - soc) / 100)
    discharge_score = price * ((soc - 20) / 100)  # Only valuable if we have excess
    features['charge_opportunity'] = max(0, charge_score)
    features['discharge_opportunity'] = max(0, discharge_score)
    
    df = pd.DataFrame([features])
    
    logger.info(f"✅ Generated {len(features)} interaction features")
    
    return Output(
        df,
        metadata={
            "num_features": len(features),
            "gen_price_ratio": features['gen_price_ratio'],
            "battery_gen_price_score": features['battery_gen_price_score'],
        }
    )


@asset(
    name="feature_matrix",
    description="Combined feature matrix (100+ features, ready for ML)",
    tags={"domain": "features", "type": "matrix"}
)
def feature_matrix(
    time_features: pd.DataFrame,
    weather_features: pd.DataFrame,
    generation_features: pd.DataFrame,
    battery_features: pd.DataFrame,
    price_features: pd.DataFrame,
    interaction_features: pd.DataFrame
) -> Output[pd.DataFrame]:
    """Combine all features into a single feature matrix."""
    
    logger.info("🧠 Building feature matrix...")
    
    # Concatenate all feature dataframes
    combined = pd.concat([
        time_features,
        weather_features,
        generation_features,
        battery_features,
        price_features,
        interaction_features,
    ], axis=1)
    
    # Add timestamp for tracking
    combined['timestamp'] = datetime.utcnow()
    
    # Feature counts
    num_features = combined.shape[1] - 1  # Exclude timestamp
    
    logger.info(f"✅ Feature matrix created: {combined.shape[0]} rows × {num_features} features")
    logger.info(f"   Features: Time({time_features.shape[1]}) + Weather({weather_features.shape[1]}) + " \
                f"Generation({generation_features.shape[1]}) + Battery({battery_features.shape[1]}) + " \
                f"Price({price_features.shape[1]}) + Interactions({interaction_features.shape[1]})")
    
    # Data quality check
    missing_count = combined.isnull().sum().sum()
    if missing_count > 0:
        logger.warning(f"⚠️ Found {missing_count} missing values in feature matrix")
        combined = combined.fillna(combined.mean(numeric_only=True))
    
    # Check for infinite values
    inf_count = np.isinf(combined.select_dtypes(include=[np.number])).sum().sum()
    if inf_count > 0:
        logger.warning(f"⚠️ Found {inf_count} infinite values, replacing with max finite values")
        combined = combined.replace([np.inf, -np.inf], np.nan).fillna(combined.replace([np.inf, -np.inf], np.nan).max())
    
    return Output(
        combined,
        metadata={
            "num_features": num_features,
            "num_rows": combined.shape[0],
            "missing_values": int(missing_count),
            "infinite_values": int(inf_count),
            "timestamp": str(datetime.utcnow()),
        }
    )


# Create Definitions object for Dagster
defs = Definitions(
    assets=[
        time_features,
        weather_features,
        generation_features,
        battery_features,
        price_features,
        interaction_features,
        feature_matrix,
    ]
)

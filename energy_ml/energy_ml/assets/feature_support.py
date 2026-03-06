from datetime import datetime, timezone
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def build_time_features(weather_data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Extract time-derived features from the weather timestamp."""
    ts = weather_data["timestamp"].values[0]
    dt = pd.Timestamp(ts).to_pydatetime()
    day_of_year = dt.timetuple().tm_yday
    features = {
        "hour": dt.hour,
        "day_of_week": dt.weekday(),
        "day_of_month": dt.day,
        "day_of_year": day_of_year,
        "month": dt.month,
        "quarter": (dt.month - 1) // 3,
        "is_weekend": 1 if dt.weekday() >= 5 else 0,
        "is_working_hours": 1 if 9 <= dt.hour <= 17 else 0,
        "is_peak_hours": 1 if 18 <= dt.hour <= 21 else 0,
        "day_sin": np.sin(2 * np.pi * day_of_year / 365),
        "day_cos": np.cos(2 * np.pi * day_of_year / 365),
        "hour_sin": np.sin(2 * np.pi * dt.hour / 24),
        "hour_cos": np.cos(2 * np.pi * dt.hour / 24),
    }
    return pd.DataFrame([features]), {
        "num_features": len(features),
        "hour": features["hour"],
        "day_of_week": features["day_of_week"],
    }


def build_weather_features(weather_data: pd.DataFrame, weather_forecast: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Create normalized current and near-term forecast weather features."""
    current = weather_data.iloc[0]
    forecast_12h = weather_forecast[
        weather_forecast["timestamp"] <= (weather_data["timestamp"].values[0] + pd.Timedelta(hours=12))
    ]
    features = {
        "temp_c": current["temp"],
        "temp_normalized": (current["temp"] - 15) / 25,
        "humidity_norm": current["humidity"] / 100,
        "cloud_cover_norm": current["cloud_cover"] / 100,
        "wind_speed_ms": current["wind_speed"],
        "wind_speed_norm": current["wind_speed"] / 20,
        "wind_direction_deg": current["wind_direction"],
        "wind_direction_sin": np.sin(np.radians(current["wind_direction"])),
        "wind_direction_cos": np.cos(np.radians(current["wind_direction"])),
        "pressure_hpa": current["pressure"],
        "pressure_anomaly": current["pressure"] - 1013,
        "forecast_temp_12h": forecast_12h["temp"].mean() if len(forecast_12h) > 0 else current["temp"],
        "forecast_cloud_12h": forecast_12h["cloud_cover"].mean() if len(forecast_12h) > 0 else current["cloud_cover"],
        "forecast_wind_12h": forecast_12h["wind_speed"].mean() if len(forecast_12h) > 0 else current["wind_speed"],
    }
    return pd.DataFrame([features]), {
        "num_features": len(features),
        "temp_c": current["temp"],
        "wind_speed_ms": current["wind_speed"],
    }


def build_generation_features(solar_irradiance: pd.DataFrame, wind_potential: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, Any]]:
    """Create generation potential features from solar and wind data."""
    solar = solar_irradiance.iloc[0]
    wind = wind_potential.iloc[0]
    solar_power = max(0, (solar["ghi_w_per_m2"] * 10.0 * 0.18) / 1000)
    wind_power = wind["power_potential_kw"]
    total_potential = solar_power + wind_power
    features = {
        "solar_ghi_w_m2": solar["ghi_w_per_m2"],
        "solar_ghi_norm": solar["ghi_w_per_m2"] / 1000,
        "solar_elevation_deg": solar["elevation_deg"],
        "solar_power_kw": round(solar_power, 2),
        "wind_speed_ms": wind["wind_speed_ms"],
        "wind_power_kw": round(wind_power, 2),
        "total_gen_potential_kw": round(total_potential, 2),
        "solar_ratio": solar_power / total_potential if total_potential > 0 else 0,
        "is_night": int(solar["is_night"]),
    }
    return pd.DataFrame([features]), {
        "num_features": len(features),
        "solar_power_kw": round(solar_power, 2),
        "wind_power_kw": round(wind_power, 2),
        "total_potential_kw": round(total_potential, 2),
    }, {
        "solar_power": solar_power,
        "wind_power": wind_power,
        "total_potential": total_potential,
    }


def build_battery_features(battery_state: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, Any]]:
    """Create derived battery-state features."""
    battery = battery_state.iloc[0]
    soc = battery["soc_percent"]
    capacity = battery["capacity_kwh"]
    charge_rate = battery["charge_rate_kw"]
    discharge_rate = battery["discharge_rate_kw"]
    health = battery["health_percent"]
    hours_to_empty = ((soc / 100) * capacity) / discharge_rate if discharge_rate > 0 else 999
    hours_to_full = (((100 - soc) / 100) * capacity) / charge_rate if charge_rate > 0 else 999
    if soc < 20:
        urgency = "critical"
    elif soc < 40:
        urgency = "low"
    elif soc > 80:
        urgency = "high"
    else:
        urgency = "normal"
    features = {
        "soc_percent": soc,
        "soc_normalized": soc / 100,
        "capacity_kwh": capacity,
        "charge_rate_kw": charge_rate,
        "discharge_rate_kw": discharge_rate,
        "health_percent": health,
        "efficiency": health / 100,
        "hours_to_empty": hours_to_empty,
        "hours_to_full": hours_to_full,
        "urgency_score": {"critical": 3, "low": 2, "normal": 1, "high": 0}[urgency],
    }
    return pd.DataFrame([features]), {
        "num_features": len(features),
        "soc_percent": soc,
        "hours_to_empty": hours_to_empty,
    }, {
        "soc": soc,
        "hours_to_empty": hours_to_empty,
        "health": health,
    }


def build_price_features(price_data_current: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, Any]]:
    """Create price-based lag and volatility features."""
    price = price_data_current.iloc[0]["price_uah_per_kwh"]
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
    price_lag1h = price * 0.98
    price_lag3h = price * 0.95
    price_lag6h = price * 0.92
    price_lag24h = price * 0.90
    prices = [price, price_lag1h, price_lag3h, price_lag6h]
    price_volatility = np.std(prices)
    features = {
        "price_uah_kwh": price,
        "price_normalized": (price - 12.5) / 7.5,
        "price_level_score": {"very_cheap": 0, "cheap": 1, "average": 2, "expensive": 3, "very_expensive": 4}[price_level],
        "price_lag_1h": price_lag1h,
        "price_lag_3h": price_lag3h,
        "price_lag_6h": price_lag6h,
        "price_lag_24h": price_lag24h,
        "price_ma_3h": (price + price_lag1h + price_lag3h) / 3,
        "price_ma_6h": (price + price_lag1h + price_lag3h + price_lag6h) / 4,
        "price_ma_24h": price * 0.95,
        "price_change_1h": price - price_lag1h,
        "price_change_3h": price - price_lag3h,
        "price_change_6h": price - price_lag6h,
        "price_volatility": price_volatility,
    }
    return pd.DataFrame([features]), {
        "num_features": len(features),
        "price_uah_kwh": price,
        "price_level": price_level,
    }, {
        "price": price,
        "price_level": price_level,
        "volatility": price_volatility,
    }


def build_interaction_features(
    time_features: pd.DataFrame,
    weather_features: pd.DataFrame,
    generation_features: pd.DataFrame,
    battery_features: pd.DataFrame,
    price_features: pd.DataFrame,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Create cross-domain interaction features."""
    hour = time_features.iloc[0]["hour"]
    is_peak = time_features.iloc[0]["is_peak_hours"]
    temp = weather_features.iloc[0]["temp_c"]
    cloud_cover = weather_features.iloc[0]["cloud_cover_norm"]
    wind_speed = weather_features.iloc[0]["wind_speed_ms"]
    solar_power = generation_features.iloc[0]["solar_power_kw"]
    wind_power = generation_features.iloc[0]["wind_power_kw"]
    total_gen = generation_features.iloc[0]["total_gen_potential_kw"]
    soc = battery_features.iloc[0]["soc_percent"]
    hours_to_empty = battery_features.iloc[0]["hours_to_empty"]
    price = price_features.iloc[0]["price_uah_kwh"]
    features = {
        "gen_price_ratio": total_gen / (price + 0.1),
        "solar_price_ratio": solar_power / (price + 0.1),
        "wind_price_ratio": wind_power / (price + 0.1),
        "soc_price_product": (soc / 100) * price,
        "hours_to_empty_price": hours_to_empty * price,
        "solar_cloud_product": solar_power * (1 - cloud_cover),
        "wind_temp_interaction": wind_speed * (temp / 15),
        "peak_hour_generation": total_gen * is_peak,
        "peak_hour_price": price * is_peak,
        "battery_gen_price_score": (soc / 100) * total_gen * (1 / (price + 1)),
    }
    charge_score = total_gen / (price + 0.1) * ((100 - soc) / 100)
    discharge_score = price * ((soc - 20) / 100)
    features["charge_opportunity"] = max(0, charge_score)
    features["discharge_opportunity"] = max(0, discharge_score)
    return pd.DataFrame([features]), {
        "num_features": len(features),
        "gen_price_ratio": features["gen_price_ratio"],
        "battery_gen_price_score": features["battery_gen_price_score"],
    }


def build_feature_matrix(
    time_features: pd.DataFrame,
    weather_features: pd.DataFrame,
    generation_features: pd.DataFrame,
    battery_features: pd.DataFrame,
    price_features: pd.DataFrame,
    interaction_features: pd.DataFrame,
    timestamp: datetime | None = None,
) -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, Any]]:
    """Combine and clean the full feature matrix."""
    combined = pd.concat(
        [
            time_features,
            weather_features,
            generation_features,
            battery_features,
            price_features,
            interaction_features,
        ],
        axis=1,
    )
    timestamp = timestamp or utc_now()
    combined["timestamp"] = timestamp
    num_features = combined.shape[1] - 1
    missing_count = combined.isnull().sum().sum()
    if missing_count > 0:
        combined = combined.fillna(combined.mean(numeric_only=True))
    inf_count = np.isinf(combined.select_dtypes(include=[np.number])).sum().sum()
    if inf_count > 0:
        numeric_columns = combined.select_dtypes(include=[np.number]).columns
        cleaned_numeric = combined[numeric_columns].replace([np.inf, -np.inf], np.nan)
        fill_values = cleaned_numeric.max().fillna(0)
        combined[numeric_columns] = cleaned_numeric.fillna(fill_values)
    metadata = {
        "num_features": num_features,
        "num_rows": combined.shape[0],
        "missing_values": int(missing_count),
        "infinite_values": int(inf_count),
        "timestamp": str(timestamp),
    }
    summary = {"num_features": num_features, "num_rows": combined.shape[0]}
    return combined, metadata, summary


def build_definitions(assets: list[Any]) -> Any:
    """Import Dagster Definitions lazily for direct-file tests."""
    from dagster import Definitions

    return Definitions(assets=assets)

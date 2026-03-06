"""Support helpers for top-level feature engineering."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Dict, Optional

import polars as pl


def normalize_feature(value: float, feature_min: float, feature_max: float) -> float:
    """Normalize a single feature into the 0-1 range."""
    if feature_max <= feature_min:
        return 0.5

    normalized = (value - feature_min) / (feature_max - feature_min)
    return max(0.0, min(1.0, normalized))


def extract_temporal_features(timestamp: datetime) -> Dict[str, float]:
    """Extract normalized temporal features for a timestamp."""
    hour = timestamp.hour
    day_of_week = timestamp.weekday()
    quarter = (timestamp.month - 1) // 3

    return {
        "hour_of_day": normalize_feature(hour / 23.0, 0.0, 1.0),
        "day_of_week": normalize_feature(day_of_week / 6.0, 0.0, 1.0),
        "is_peak_hour": 1.0 if 6 <= hour < 23 else 0.0,
        "season": normalize_feature(quarter / 3.0, 0.0, 1.0),
    }


def extract_price_features(
    tariff_model,
    historical_data: Optional[Dict],
    current_hour: int,
    tariff_min_uah_mwh: float,
    tariff_max_uah_mwh: float,
) -> Dict[str, float]:
    """Extract normalized tariff features."""
    current_rate = tariff_model.get_hourly_rate(current_hour)
    trend = 0.5
    volatility = 0.3

    if historical_data and "tariff_history" in historical_data:
        history = historical_data["tariff_history"]
        if len(history) >= 6:
            recent_prices = history[-6:]
            mean_price = sum(recent_prices) / len(recent_prices)
            variance = sum((price - mean_price) ** 2 for price in recent_prices) / len(recent_prices)
            std_dev = math.sqrt(variance)
            volatility_pct = (std_dev / mean_price) if mean_price > 0 else 0
            volatility = normalize_feature(volatility_pct, 0.0, 0.2)

        if len(history) >= 12:
            recent_avg = sum(history[-6:]) / 6
            older_avg = sum(history[-12:-6]) / 6
            trend_value = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
            trend = normalize_feature(trend_value, -0.1, 0.1)

    return {
        "current_tariff": normalize_feature(current_rate, tariff_min_uah_mwh, tariff_max_uah_mwh),
        "trend": trend,
        "volatility": volatility,
    }


def extract_battery_features(max_degradation_cost_uah_kwh: float) -> Dict[str, float]:
    """Extract normalized battery state features from the current model assumptions."""
    soc = 60.0
    health = 95.0
    cycles_remaining = 5000
    battery_cost_uah = 50000
    degradation_cost = battery_cost_uah / (max(cycles_remaining, 100) * 10)
    cycles_log = math.log10(max(cycles_remaining, 1))

    return {
        "soc": soc / 100.0,
        "health": health / 100.0,
        "degradation_cost": normalize_feature(degradation_cost, 0.0, max_degradation_cost_uah_kwh),
        "cycles_remaining": max(0.0, min(1.0, cycles_log / math.log10(10000))),
    }


def extract_load_features(
    load_profile,
    historical_data: Optional[Dict],
    current_hour: int,
    max_load_kw: float,
) -> Dict[str, float]:
    """Extract normalized load profile features."""
    next_hour = (current_hour + 1) % 24
    current_load = load_profile.get_hourly_coefficient(current_hour, 0) * 10.0
    forecast_load = load_profile.get_hourly_coefficient(next_hour, 0) * 10.0
    trend = 0.5

    if historical_data and "load_history" in historical_data:
        history = historical_data["load_history"]
        if len(history) >= 6:
            recent_avg = sum(history[-3:]) / 3
            older_avg = sum(history[-6:-3]) / 3
            trend_value = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
            trend = normalize_feature(trend_value, -0.5, 0.5)

    return {
        "current_load": normalize_feature(current_load, 0.0, max_load_kw),
        "forecast_1h": normalize_feature(forecast_load, 0.0, max_load_kw),
        "trend": trend,
    }


def combine_feature_groups(
    temporal: Dict[str, float],
    price: Dict[str, float],
    battery: Dict[str, float],
    load: Dict[str, float],
) -> Dict[str, float]:
    """Combine extracted feature groups into the model input shape."""
    return {
        "hour_of_day": temporal["hour_of_day"],
        "day_of_week": temporal["day_of_week"],
        "is_peak_hour": temporal["is_peak_hour"],
        "season": temporal["season"],
        "current_tariff_uah_mwh": price["current_tariff"],
        "price_trend": price["trend"],
        "price_volatility": price["volatility"],
        "soc_percent": battery["soc"],
        "battery_health": battery["health"],
        "degradation_cost_uah_kwh": battery["degradation_cost"],
        "battery_cycles_remaining": battery["cycles_remaining"],
        "current_load_kw": load["current_load"],
        "load_forecast_1h": load["forecast_1h"],
        "load_trend": load["trend"],
    }


def clamp_feature_frame(df: pl.DataFrame, logger) -> pl.DataFrame:
    """Clamp any out-of-range feature values back into the expected bounds."""
    for column in df.columns:
        min_val = df[column].min()
        max_val = df[column].max()
        if min_val < 0.0 or max_val > 1.0:
            logger.warning("Feature %s out of bounds: [%s, %s]", column, min_val, max_val)
            df = df.with_columns(pl.col(column).clip(0.0, 1.0))
    return df


def append_feature_history(
    feature_history: list[Dict[str, object]],
    features: Dict[str, float],
    timestamp: datetime,
) -> None:
    """Record a feature extraction snapshot for later analysis."""
    feature_history.append(
        {
            "timestamp": timestamp.isoformat(),
            "features": features.copy(),
        }
    )


def get_feature_importance_map() -> Dict[str, float]:
    """Return the current heuristic feature importance map."""
    return {
        "hour_of_day": 0.15,
        "is_peak_hour": 0.18,
        "current_tariff_uah_mwh": 0.16,
        "price_trend": 0.10,
        "soc_percent": 0.12,
        "battery_health": 0.08,
        "current_load_kw": 0.07,
        "day_of_week": 0.05,
        "load_forecast_1h": 0.05,
        "degradation_cost_uah_kwh": 0.02,
        "price_volatility": 0.02,
        "season": 0.01,
        "load_trend": 0.01,
        "battery_cycles_remaining": 0.01,
    }

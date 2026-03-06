"""Support helpers for nested data source assets."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict

import polars as pl
from dagster import Definitions, Output


def is_cache_fresh(cache_dict: Dict[str, Any], ttl_seconds: int) -> bool:
    """Check if cache is still fresh."""
    if cache_dict["timestamp"] is None:
        return False
    return (datetime.utcnow() - cache_dict["timestamp"]).total_seconds() < ttl_seconds


def build_weather_frame(data: dict) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "timestamp": [datetime.utcnow()],
            "temp": [data["main"]["temp"]],
            "humidity": [data["main"]["humidity"]],
            "cloud_cover": [data["clouds"]["all"]],
            "wind_speed": [data["wind"]["speed"]],
            "wind_direction": [data["wind"].get("deg", 0)],
            "pressure": [data["main"]["pressure"]],
            "description": [data["weather"][0]["description"]],
        }
    )


def build_weather_output(df: pl.DataFrame, source: str = "openweatherapi") -> Output[pl.DataFrame]:
    temp_val = df["temp"].item(0)
    wind_val = df["wind_speed"].item(0)
    return Output(
        df,
        metadata={
            "rows": len(df),
            "temp_c": float(temp_val),
            "wind_speed_ms": float(wind_val),
            "source": source,
        },
    )


def build_weather_error_output(error: Exception) -> Output[pl.DataFrame]:
    df = pl.DataFrame(
        {
            "timestamp": [datetime.utcnow()],
            "temp": [15.0],
            "humidity": [60.0],
            "cloud_cover": [50.0],
            "wind_speed": [5.0],
            "wind_direction": [180.0],
            "pressure": [1013.0],
            "description": ["Unknown"],
        }
    )
    return Output(df, metadata={"error": str(error)})


def build_forecast_frame(data: dict) -> pl.DataFrame:
    records = []
    for item in data.get("list", [])[:40]:
        records.append(
            {
                "timestamp": [datetime.fromtimestamp(item["dt"])],
                "temp": [item["main"]["temp"]],
                "cloud_cover": [item["clouds"]["all"]],
                "wind_speed": [item["wind"]["speed"]],
                "precipitation": [item.get("rain", {}).get("3h", 0)],
            }
        )
    return pl.concat([pl.DataFrame(record) for record in records])


def build_forecast_output(df: pl.DataFrame, source: str = "openweatherapi") -> Output[pl.DataFrame]:
    return Output(
        df,
        metadata={
            "rows": len(df),
            "days": len(df) / 8,
            "source": source,
        },
    )


def build_forecast_error_output(error: Exception) -> Output[pl.DataFrame]:
    timestamps = [datetime.utcnow() + timedelta(hours=3 * index) for index in range(40)]
    df = pl.DataFrame(
        {
            "timestamp": timestamps,
            "temp": [15.0] * 40,
            "cloud_cover": [50.0] * 40,
            "wind_speed": [5.0] * 40,
            "precipitation": [0.0] * 40,
        }
    )
    return Output(df, metadata={"error": str(error)})


def build_solar_output(weather_data: pl.DataFrame, position: dict, irradiance: dict) -> Output[pl.DataFrame]:
    df = pl.DataFrame(
        {
            "timestamp": weather_data["timestamp"],
            "ghi_w_per_m2": [irradiance["GHI"]],
            "dni_w_per_m2": [irradiance["DNI"]],
            "dhi_w_per_m2": [irradiance["DHI"]],
            "elevation_deg": [position["elevation"]],
            "azimuth_deg": [position["azimuth"]],
            "is_night": [position["is_night"]],
        }
    )
    return Output(
        df,
        metadata={
            "ghi_w_m2": irradiance["GHI"],
            "elevation_deg": position["elevation"],
            "is_night": position["is_night"],
        },
    )


def build_wind_output(weather_data: pl.DataFrame, power: float) -> Output[pl.DataFrame]:
    wind_speed = weather_data["wind_speed"].item(0)
    wind_direction = weather_data["wind_direction"].item(0)
    df = pl.DataFrame(
        {
            "timestamp": weather_data["timestamp"],
            "wind_speed_ms": [wind_speed],
            "wind_direction_deg": [wind_direction],
            "power_potential_kw": [power],
        }
    )
    return Output(
        df,
        metadata={
            "wind_speed_ms": wind_speed,
            "power_potential_kw": power,
        },
    )


def build_battery_state_output() -> Output[pl.DataFrame]:
    df = pl.DataFrame(
        {
            "timestamp": [datetime.utcnow()],
            "soc_percent": [72.6],
            "charge_rate_kw": [3.5],
            "discharge_rate_kw": [4.2],
            "capacity_kwh": [13.5],
            "health_percent": [95.0],
        }
    )
    soc_val = df["soc_percent"].item(0)
    return Output(
        df,
        metadata={
            "soc_percent": soc_val,
            "health_percent": df["health_percent"].item(0),
        },
    )


def build_price_output() -> Output[pl.DataFrame]:
    df = pl.DataFrame(
        {
            "timestamp": [datetime.utcnow()],
            "price_uah_per_kwh": [14.26],
            "currency": ["UAH"],
            "market": ["OREE"],
        }
    )
    price_val = df["price_uah_per_kwh"].item(0)
    return Output(
        df,
        metadata={
            "price_uah_kwh": price_val,
            "market": "OREE",
        },
    )


def build_definitions(assets: list[Any]) -> Definitions:
    return Definitions(assets=assets)
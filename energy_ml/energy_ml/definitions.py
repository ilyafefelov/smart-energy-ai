"""Dagster definitions for Energy ML system.

This is the entry point for Dagster. It loads all assets and jobs.
"""
from dagster import Definitions, define_asset_job
from energy_ml.assets.data_sources import (
    weather_data,
    weather_forecast,
    solar_irradiance,
    wind_potential,
    battery_state,
    price_data_current,
)

# Define jobs
# Daily batch job - recompute everything
daily_batch_job = define_asset_job(
    name="daily_batch_job",
    selection=[
        weather_data,
        weather_forecast,
        solar_irradiance,
        wind_potential,
        battery_state,
        price_data_current,
    ],
    tags={"batch": True, "frequency": "daily"},
)

# Create main definitions
defs = Definitions(
    assets=[
        weather_data,
        weather_forecast,
        solar_irradiance,
        wind_potential,
        battery_state,
        price_data_current,
    ],
    jobs=[daily_batch_job],
)

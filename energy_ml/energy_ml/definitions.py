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
from energy_ml.assets.features import (
    time_features,
    weather_features,
    generation_features,
    battery_features,
    price_features,
    interaction_features,
    feature_matrix,
)

# Define jobs
# Daily batch job - recompute everything
daily_batch_job = define_asset_job(
    name="daily_batch_job",
    selection=[
        # Data sources
        weather_data,
        weather_forecast,
        solar_irradiance,
        wind_potential,
        battery_state,
        price_data_current,
        # Features
        time_features,
        weather_features,
        generation_features,
        battery_features,
        price_features,
        interaction_features,
        feature_matrix,
    ],
    tags={"batch": True, "frequency": "daily"},
)

# Create main definitions
defs = Definitions(
    assets=[
        # Data sources
        weather_data,
        weather_forecast,
        solar_irradiance,
        wind_potential,
        battery_state,
        price_data_current,
        # Features
        time_features,
        weather_features,
        generation_features,
        battery_features,
        price_features,
        interaction_features,
        feature_matrix,
    ],
    jobs=[daily_batch_job],
)

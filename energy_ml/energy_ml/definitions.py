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
from energy_ml.assets.training import (
    training_data_prepared,
    synthetic_historical_data,
    backtest_dataset,
    baseline_model_metrics,
    xgboost_model_metadata,
    model_training_status,
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
        # Training
        training_data_prepared,
        backtest_dataset,
    ],
    tags={"batch": True, "frequency": "daily"},
)

# Training job - for model training and evaluation
training_job = define_asset_job(
    name="training_job",
    selection=[
        training_data_prepared,
        synthetic_historical_data,
        backtest_dataset,
        baseline_model_metrics,
        xgboost_model_metadata,
        model_training_status,
    ],
    tags={"batch": True, "frequency": "weekly"},
)

# Create main definitions
defs = Definitions(
    assets=[
        # Data sources (Layer 1)
        weather_data,
        weather_forecast,
        solar_irradiance,
        wind_potential,
        battery_state,
        price_data_current,
        # Features (Layer 2)
        time_features,
        weather_features,
        generation_features,
        battery_features,
        price_features,
        interaction_features,
        feature_matrix,
        # Training (Layer 3)
        training_data_prepared,
        synthetic_historical_data,
        backtest_dataset,
        baseline_model_metrics,
        xgboost_model_metadata,
        model_training_status,
    ],
    jobs=[daily_batch_job, training_job],
)

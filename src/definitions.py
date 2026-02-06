"""
Smart Energy AI V2 - Main Dagster Definitions

This module serves as the main entry point for the Dagster workspace,
defining all assets, resources, and schedules for the V2 system.

Thesis Relevance: Demonstrates Software-Defined Assets architecture
for scalable data orchestration in energy systems.
"""

from dagster import Definitions, AssetSelection, define_asset_job, ScheduleDefinition

# Import core assets
from .assets.core.market import market_data_asset
from .assets.core.weather import weather_asset  
from .assets.core.client_state import client_state_asset

# Import engines for feature processing
from .engines.polars_engine import PolarsEngine

# Define jobs
daily_data_refresh_job = define_asset_job(
    name="daily_data_refresh",
    selection=AssetSelection.assets(
        market_data_asset,
        weather_asset,
        client_state_asset
    ),
    description="Daily refresh of market, weather, and client state data"
)

# Define schedules
daily_refresh_schedule = ScheduleDefinition(
    job=daily_data_refresh_job,
    cron_schedule="0 6 * * *",  # 6:00 AM daily
    description="Run daily data refresh at 6:00 AM Kiev time"
)

# Resources (simplified for Stage 1)
resources = {
    # Will add S3 and MLflow in later phases
    "polars_engine": PolarsEngine()
}

# Main definitions for Dagster
defs = Definitions(
    assets=[
        market_data_asset,
        weather_asset,
        client_state_asset
    ],
    jobs=[daily_data_refresh_job],
    schedules=[daily_refresh_schedule],
    resources=resources
)
"""
Smart Energy AI V2 - Main Dagster Definitions

This module serves as the main entry point for the Dagster workspace,
defining all assets, resources, and schedules for the V2 system.

Thesis Relevance: Demonstrates Software-Defined Assets architecture
for scalable data orchestration in energy systems.
"""

from dagster import Definitions, AssetSelection, define_asset_job, ScheduleDefinition
import logging

# Import core assets
from .assets.core.market import market_data_asset
from .assets.core.weather import weather_asset  
from .assets.core.client_state import client_state_asset
from .assets.core.feature_matrix import feature_matrix_asset
from .assets.core.price_forecast import price_forecast_asset
from .assets.core.optimization_schedule import optimization_schedule_asset
from .assets.core.optimization_schedule_milp import optimization_schedule_milp_asset
from .assets.core.optimization_schedule_checks import optimization_schedule_contract_checks

# Import Phase 2 assets
from .assets.benchmarks.performance import (
    engine_benchmark_asset, 
    accuracy_benchmark_asset, 
    mlflow_tracking_asset
)
from .assets.multi_tenant.asset_factory import create_all_assets, multi_client_analytics

# Import engines for feature processing
from .engines import select_feature_engine
from .engines.polars_engine import create_polars_engine
from .io_managers import build_asset_io_manager_from_env

logger = logging.getLogger(__name__)

# Generate dynamic client assets using the asset factory
client_assets = create_all_assets()
optimization_assets_selection = AssetSelection.assets(
    optimization_schedule_asset,
    optimization_schedule_milp_asset,
)
optimization_schedule_checks_selection = AssetSelection.checks_for_assets(
    optimization_schedule_asset,
    optimization_schedule_milp_asset,
)

# Define jobs
daily_data_refresh_job = define_asset_job(
    name="daily_data_refresh",
    selection=AssetSelection.assets(
        market_data_asset,
        weather_asset,
        client_state_asset,
        feature_matrix_asset,
        price_forecast_asset,
        optimization_schedule_asset,
        optimization_schedule_milp_asset,
    ) | optimization_schedule_checks_selection,
    description="Daily refresh of market, weather, and client state data"
)

optimization_schedule_contract_checks_job = define_asset_job(
    name="optimization_schedule_contract_checks",
    selection=optimization_assets_selection | optimization_schedule_checks_selection,
    description="Run optimization schedule assets together with Dagster contract checks",
)

benchmark_job = define_asset_job(
    name="benchmark_engines",
    selection=AssetSelection.assets(
        engine_benchmark_asset,
        accuracy_benchmark_asset,
        mlflow_tracking_asset
    ),
    description="Performance and accuracy benchmarking of processing engines"
)

multi_tenant_job = define_asset_job(
    name="multi_tenant_analytics", 
    selection=AssetSelection.assets(multi_client_analytics),
    description="Cross-client analytics and comparative insights"
)

# Define schedules
daily_refresh_schedule = ScheduleDefinition(
    job=daily_data_refresh_job,
    cron_schedule="0 6 * * *",  # 6:00 AM daily
    description="Run daily data refresh at 6:00 AM Kiev time"
)

weekly_benchmark_schedule = ScheduleDefinition(
    job=benchmark_job,
    cron_schedule="0 3 * * 0",  # 3:00 AM on Sundays
    description="Weekly performance benchmarking"
)

# Resources (simplified for Stage 1)
selected_engine, engine_selection = select_feature_engine({"execution_mode": "auto"})
logger.info(
    "Selected feature engine: %s (requested=%s, fallback_reason=%s)",
    engine_selection["selected_engine"],
    engine_selection["requested_engine"],
    engine_selection["fallback_reason"],
)
resources = {
    # Existing resource name kept for compatibility.
    "polars_engine": create_polars_engine({}) or selected_engine,
    # Explicit generic selector output for new assets.
    "feature_engine": selected_engine,
    # Asset persistence plane; uses S3 when configured, filesystem otherwise.
    "io_manager": build_asset_io_manager_from_env(),
}

# Collect all assets
all_assets = [
    # Core assets
    market_data_asset,
    weather_asset, 
    client_state_asset,
    feature_matrix_asset,
    price_forecast_asset,
    optimization_schedule_asset,
    optimization_schedule_milp_asset,
    # Benchmark assets
    engine_benchmark_asset,
    accuracy_benchmark_asset,
    mlflow_tracking_asset,
    # Multi-tenant analytics
    multi_client_analytics
] + client_assets  # Add dynamically generated client assets

# Main definitions for Dagster
defs = Definitions(
    assets=all_assets,
    asset_checks=optimization_schedule_contract_checks,
    jobs=[daily_data_refresh_job, optimization_schedule_contract_checks_job, benchmark_job, multi_tenant_job],
    schedules=[daily_refresh_schedule, weekly_benchmark_schedule],
    resources=resources
)
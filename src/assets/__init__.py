from dagster import repository
from .core.market import market_data_asset
from .core.weather import weather_asset
from .core.client_state import client_state_asset
from .benchmarks.performance import (
    engine_benchmark_asset,
    accuracy_benchmark_asset,
    mlflow_tracking_asset,
)


@repository
def assets_repository():
    return [
        market_data_asset,
        weather_asset,
        client_state_asset,
        engine_benchmark_asset,
        accuracy_benchmark_asset,
        mlflow_tracking_asset,
    ]

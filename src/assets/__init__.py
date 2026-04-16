from dagster import repository
from .core.market import market_data_asset
from .core.weather import weather_asset
from .core.client_state import client_state_asset
from .core.feature_matrix import feature_matrix_asset
from .core.price_forecast import price_forecast_asset
from .core.optimization_schedule import optimization_schedule_asset
from .core.optimization_schedule_milp import optimization_schedule_milp_asset
from .benchmarks.performance import (
    engine_benchmark_asset,
    accuracy_benchmark_asset,
    forecast_value_benchmark_asset,
    mlflow_tracking_asset,
)


@repository
def assets_repository():
    return [
        market_data_asset,
        weather_asset,
        client_state_asset,
        feature_matrix_asset,
        price_forecast_asset,
        optimization_schedule_asset,
        optimization_schedule_milp_asset,
        engine_benchmark_asset,
        accuracy_benchmark_asset,
        forecast_value_benchmark_asset,
        mlflow_tracking_asset,
    ]

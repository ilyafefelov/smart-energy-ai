# Initialize the assets package
from .core.market import market_data_asset
from .core.weather import weather_asset
from .core.client_state import client_state_asset

__all__ = [
    "market_data_asset",
    "weather_asset", 
    "client_state_asset"
]
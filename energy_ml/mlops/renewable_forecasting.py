"""
Renewable Energy Forecasting Engine

Provides solar and wind generation forecasting based on:
- Weather data integration
- Geographic location
- Installed capacity
- Seasonal patterns
- Real-time generation modeling
"""
import importlib.util
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from energy_ml.user_config import UserConfigModel

try:
    from energy_ml.mlops.renewable_forecasting_support import (
        build_deterministic_fallback,
        build_live_context_weather,
        build_open_meteo_weather,
        calculate_capacity_factors,
        calculate_panel_efficiency,
        combine_forecasts,
        generate_solar_forecast,
        generate_wind_forecast,
        integrate_prediction_with_renewables,
        safe_float,
        wind_power_curve,
    )
except ImportError:
    _SUPPORT_MODULE_NAME = "energy_ml.mlops.renewable_forecasting_support"
    _SUPPORT_PATH = Path(__file__).with_name("renewable_forecasting_support.py")
    _SUPPORT_SPEC = importlib.util.spec_from_file_location(_SUPPORT_MODULE_NAME, _SUPPORT_PATH)
    if _SUPPORT_SPEC is None or _SUPPORT_SPEC.loader is None:
        raise ImportError(f"Unable to load renewable forecasting support module from {_SUPPORT_PATH}")
    _SUPPORT_MODULE = sys.modules.get(_SUPPORT_MODULE_NAME)
    if _SUPPORT_MODULE is None:
        _SUPPORT_MODULE = importlib.util.module_from_spec(_SUPPORT_SPEC)
        sys.modules[_SUPPORT_MODULE_NAME] = _SUPPORT_MODULE
        _SUPPORT_SPEC.loader.exec_module(_SUPPORT_MODULE)
    build_deterministic_fallback = _SUPPORT_MODULE.build_deterministic_fallback
    build_live_context_weather = _SUPPORT_MODULE.build_live_context_weather
    build_open_meteo_weather = _SUPPORT_MODULE.build_open_meteo_weather
    calculate_capacity_factors = _SUPPORT_MODULE.calculate_capacity_factors
    calculate_panel_efficiency = _SUPPORT_MODULE.calculate_panel_efficiency
    combine_forecasts = _SUPPORT_MODULE.combine_forecasts
    generate_solar_forecast = _SUPPORT_MODULE.generate_solar_forecast
    generate_wind_forecast = _SUPPORT_MODULE.generate_wind_forecast
    integrate_prediction_with_renewables = _SUPPORT_MODULE.integrate_prediction_with_renewables
    safe_float = _SUPPORT_MODULE.safe_float
    wind_power_curve = _SUPPORT_MODULE.wind_power_curve

logger = logging.getLogger(__name__)


class RenewableForecaster:
    """Engine for forecasting solar and wind generation."""
    
    def __init__(self):
        """Initialize renewable forecaster."""
        self.weather_cache = {}
        self.generation_models = {
            'solar': SolarGenerationModel(),
            'wind': WindGenerationModel()
        }
    
    def generate_forecasts(self, user_config: UserConfigModel) -> Dict[str, Any]:
        """Generate renewable energy forecasts.
        
        Args:
            user_config: User configuration with location and capacity data
            
        Returns:
            dict with solar, wind, and combined forecasts
        """
        try:
            # Get location (extend UserConfigModel to include this)
            latitude = getattr(user_config, 'latitude', 50.45)  # Default: Kyiv
            longitude = getattr(user_config, 'longitude', 30.52)
            
            # Get installed capacity (extend UserConfigModel)
            solar_capacity_kw = getattr(user_config, 'solar_capacity_kw', 0.0)
            wind_capacity_kw = getattr(user_config, 'wind_capacity_kw', 0.0)
            
            # Get weather data
            weather_data = self._get_weather_data(latitude, longitude)
            
            # Generate solar forecast
            solar_forecast = {}
            if solar_capacity_kw > 0:
                solar_forecast = self.generation_models['solar'].generate_forecast(
                    capacity_kw=solar_capacity_kw,
                    latitude=latitude,
                    longitude=longitude,
                    weather_data=weather_data
                )
            
            # Generate wind forecast
            wind_forecast = {}
            if wind_capacity_kw > 0:
                wind_forecast = self.generation_models['wind'].generate_forecast(
                    capacity_kw=wind_capacity_kw,
                    latitude=latitude,
                    longitude=longitude,
                    weather_data=weather_data
                )
            
            # Combine forecasts
            total_renewable = self._combine_forecasts(solar_forecast, wind_forecast)
            
            # Calculate capacity factors
            capacity_factors = self._calculate_capacity_factors(
                solar_forecast, wind_forecast, solar_capacity_kw, wind_capacity_kw
            )
            
            forecasts = {
                'solar_forecast': solar_forecast,
                'wind_forecast': wind_forecast,
                'total_renewable': total_renewable,
                'weather_data': weather_data,
                'capacity_factors': capacity_factors,
                'location': {'latitude': latitude, 'longitude': longitude},
                'installed_capacity': {
                    'solar_kw': solar_capacity_kw,
                    'wind_kw': wind_capacity_kw,
                    'total_kw': solar_capacity_kw + wind_capacity_kw
                },
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Generated renewable forecasts for {solar_capacity_kw}kW solar + {wind_capacity_kw}kW wind")
            
            return forecasts
            
        except Exception as e:
            logger.error(f"Renewable forecasting failed: {e}")
            return {
                'solar_forecast': {},
                'wind_forecast': {},
                'total_renewable': {},
                'weather_data': {},
                'capacity_factors': {},
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_weather_data(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Get weather data for the location.

        Priority:
        1) Live context injected by API layer (ENERGY_ML_LIVE_CONTEXT_JSON)
        2) Open-Meteo API
        3) Deterministic synthetic fallback (no randomness)
        """
        from_context = self._get_weather_from_live_context()
        if from_context:
            return from_context

        from_api = self._fetch_open_meteo_weather(latitude, longitude)
        if from_api:
            return from_api

        return self._build_deterministic_fallback(latitude, longitude)

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        return safe_float(value, default)

    def _get_weather_from_live_context(self) -> Optional[Dict[str, Any]]:
        return build_live_context_weather()

    def _fetch_open_meteo_weather(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        return build_open_meteo_weather(latitude, longitude, logger)

    def _build_deterministic_fallback(self, latitude: float, longitude: float) -> Dict[str, Any]:
        return build_deterministic_fallback(latitude, longitude)
    
    def _combine_forecasts(self, solar_forecast: Dict, wind_forecast: Dict) -> Dict[str, Any]:
        """Combine solar and wind forecasts into total renewable generation."""
        return combine_forecasts(solar_forecast, wind_forecast)
    
    def _calculate_capacity_factors(self, 
                                  solar_forecast: Dict, 
                                  wind_forecast: Dict,
                                  solar_capacity: float,
                                  wind_capacity: float) -> Dict[str, Any]:
        """Calculate capacity factors for renewable generation."""
        return calculate_capacity_factors(solar_forecast, wind_forecast, solar_capacity, wind_capacity)
    
    def integrate_with_prediction(self, 
                                prediction: Dict[str, Any],
                                renewable_data: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate renewable generation with energy trading prediction."""
        return integrate_prediction_with_renewables(
            prediction,
            renewable_data,
            (datetime.now().hour + 1) % 24,
        )


class SolarGenerationModel:
    """Model for solar PV generation forecasting."""
    
    def generate_forecast(self, 
                         capacity_kw: float,
                         latitude: float,
                         longitude: float,
                         weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate solar generation forecast."""
        return generate_solar_forecast(capacity_kw, weather_data, self._calculate_panel_efficiency)
    
    def _calculate_panel_efficiency(self, temperature: float) -> float:
        """Calculate solar panel efficiency based on temperature."""
        return calculate_panel_efficiency(temperature)


class WindGenerationModel:
    """Model for wind turbine generation forecasting."""
    
    def generate_forecast(self,
                         capacity_kw: float,
                         latitude: float,
                         longitude: float,
                         weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate wind generation forecast."""
        return generate_wind_forecast(capacity_kw, weather_data, self._wind_power_curve)
    
    def _wind_power_curve(self, wind_speed_m_s: float, rated_power_kw: float) -> float:
        """Calculate wind turbine power output using typical power curve."""
        return wind_power_curve(wind_speed_m_s, rated_power_kw)
"""Utility functions for solar and wind calculations."""
import importlib.util
import math
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict

try:
    from energy_ml.energy_ml.utils_support import (
        apply_cloud_cover,
        build_solar_position,
        clear_sky_ghi,
        split_irradiance_components,
    )
except ImportError:
    _SUPPORT_MODULE_NAME = "energy_ml.energy_ml.utils_support"
    _SUPPORT_PATH = Path(__file__).with_name("utils_support.py")
    _SUPPORT_SPEC = importlib.util.spec_from_file_location(_SUPPORT_MODULE_NAME, _SUPPORT_PATH)
    if _SUPPORT_SPEC is None or _SUPPORT_SPEC.loader is None:
        raise ImportError(f"Unable to load utils support module from {_SUPPORT_PATH}")
    _SUPPORT_MODULE = sys.modules.get(_SUPPORT_MODULE_NAME)
    if _SUPPORT_MODULE is None:
        _SUPPORT_MODULE = importlib.util.module_from_spec(_SUPPORT_SPEC)
        sys.modules[_SUPPORT_MODULE_NAME] = _SUPPORT_MODULE
        _SUPPORT_SPEC.loader.exec_module(_SUPPORT_MODULE)
    apply_cloud_cover = _SUPPORT_MODULE.apply_cloud_cover
    build_solar_position = _SUPPORT_MODULE.build_solar_position
    clear_sky_ghi = _SUPPORT_MODULE.clear_sky_ghi
    split_irradiance_components = _SUPPORT_MODULE.split_irradiance_components

def get_solar_position(lat: float, lon: float, dt: datetime) -> Dict[str, float]:
    """
    Calculate solar position (elevation and azimuth) for given location and time.
    Using simplified algorithm suitable for real-time calculations.
    
    Args:
        lat: Latitude (degrees)
        lon: Longitude (degrees)
        dt: Datetime object
        
    Returns:
        Dictionary with elevation and azimuth angles (degrees)
    """
    return build_solar_position(lat, dt)


def calculate_irradiance(position: Dict, cloud_cover: float, pressure: float = 1013) -> Dict[str, float]:
    """
    Calculate solar irradiance based on sun position and weather.
    
    Args:
        position: Solar position dict from get_solar_position()
        cloud_cover: Cloud cover percentage (0-100)
        pressure: Atmospheric pressure (hPa)
        
    Returns:
        Dictionary with GHI, DNI, DHI irradiance values (W/m²)
    """
    if position["is_night"]:
        return {"GHI": 0, "DNI": 0, "DHI": 0}

    ghi_clear = clear_sky_ghi(position["elevation"], pressure)
    ghi_actual = apply_cloud_cover(ghi_clear, cloud_cover)
    return split_irradiance_components(ghi_clear, ghi_actual, position["elevation"])


def wind_power_curve(wind_speed: float, rated_capacity: float = 5.0) -> float:
    """
    Calculate wind power output based on wind speed.
    Uses typical small wind turbine power curve.
    
    Args:
        wind_speed: Wind speed (m/s)
        rated_capacity: Rated capacity of turbine (kW)
        
    Returns:
        Power output (kW)
    """
    # Cut-in speed: 3 m/s
    # Rated speed: 15 m/s
    # Cut-out speed: 25 m/s
    
    if wind_speed < 3:
        return 0
    if wind_speed > 25:
        return 0
    if wind_speed >= 15:
        return rated_capacity
    
    # Linear ramp between 3 and 15 m/s
    ramp_start = 3
    ramp_end = 15
    ramp_factor = (wind_speed - ramp_start) / (ramp_end - ramp_start)
    
    return rated_capacity * ramp_factor


def solar_generation_from_irradiance(
    irradiance_ghi: float,
    capacity_kw: float,
    panel_efficiency: float = 0.18
) -> float:
    """
    Convert solar irradiance to generation in kW.
    
    Args:
        irradiance_ghi: Global Horizontal Irradiance (W/m²)
        capacity_kw: Installed capacity (kW)
        panel_efficiency: Panel efficiency (0-1)
        
    Returns:
        Generation (kW)
    """
    # Assume 1 m² of panel area per 1 kW capacity
    generation = (irradiance_ghi * capacity_kw * panel_efficiency) / 1000
    return max(0, generation)

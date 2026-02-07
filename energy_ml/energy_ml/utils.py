"""Utility functions for solar and wind calculations."""
import math
from datetime import datetime
from typing import Dict, Tuple

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
    # Day of year (1-366)
    day_of_year = dt.timetuple().tm_yday
    
    # Solar declination (degrees)
    B = (360 / 365) * (day_of_year - 81)
    declination = 23.45 * math.sin(math.radians(B))
    
    # Hour angle (degrees, 15° per hour from solar noon)
    hour = dt.hour + dt.minute / 60
    hour_angle = 15 * (hour - 12)
    
    # Solar elevation (degrees)
    lat_rad = math.radians(lat)
    decl_rad = math.radians(declination)
    ha_rad = math.radians(hour_angle)
    
    elev_sin = math.sin(lat_rad) * math.sin(decl_rad) + \
               math.cos(lat_rad) * math.cos(decl_rad) * math.cos(ha_rad)
    
    elevation = math.degrees(math.asin(max(-1, min(1, elev_sin))))
    
    # Solar azimuth (degrees from north)
    if elevation > -0.5:
        cos_azimuth = (math.sin(decl_rad) * math.cos(lat_rad) - \
                       math.cos(decl_rad) * math.sin(lat_rad) * math.cos(ha_rad)) / \
                      (math.cos(math.radians(elevation)) + 0.0001)
        azimuth = math.degrees(math.acos(max(-1, min(1, cos_azimuth))))
        if hour_angle > 0:
            azimuth = 360 - azimuth
    else:
        azimuth = 0
    
    return {
        "elevation": max(0, elevation),
        "azimuth": azimuth,
        "is_night": elevation < 0,
    }


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
    
    # Clear-sky GHI model (simplified)
    elevation_rad = math.radians(position["elevation"])
    sin_elev = math.sin(elevation_rad)
    
    # Air mass
    air_mass = 1 / (sin_elev + 0.50572 * math.pow(96.07995 - position["elevation"], -1.6364))
    air_mass = max(1, air_mass)
    
    # Clear-sky irradiance
    Io = 1361  # Solar constant (W/m²)
    Kt = 0.7   # Clearness index
    pressure_ratio = pressure / 1013
    
    ghi_clear = Io * Kt * math.pow(0.678, air_mass * pressure_ratio) * sin_elev
    ghi_clear = max(0, ghi_clear)
    
    # Adjust for clouds (clouds reduce by max 75%)
    cloud_factor = 1 - (cloud_cover / 100) * 0.75
    ghi_actual = ghi_clear * cloud_factor
    
    # Split into direct and diffuse (simplified)
    dni = ghi_clear / sin_elev * 0.8 if sin_elev > 0.1 else 0
    dhi = ghi_actual * 0.15
    
    return {
        "GHI": round(ghi_actual),
        "DNI": round(max(0, dni)),
        "DHI": round(dhi),
    }


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

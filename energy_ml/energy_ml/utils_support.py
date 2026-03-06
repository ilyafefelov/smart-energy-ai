"""Support helpers for solar and irradiance calculations."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Dict


def clamp(value: float, lower: float, upper: float) -> float:
    """Clamp a value into the provided inclusive range."""
    return max(lower, min(upper, value))


def day_of_year(dt: datetime) -> int:
    """Return the ordinal day of year for a datetime."""
    return dt.timetuple().tm_yday


def solar_declination(dt: datetime) -> float:
    """Return the approximate solar declination angle in degrees."""
    angle = (360 / 365) * (day_of_year(dt) - 81)
    return 23.45 * math.sin(math.radians(angle))


def hour_angle(dt: datetime) -> float:
    """Return the solar hour angle in degrees."""
    hour = dt.hour + dt.minute / 60
    return 15 * (hour - 12)


def solar_elevation(lat: float, declination: float, solar_hour_angle: float) -> float:
    """Compute solar elevation in degrees."""
    lat_rad = math.radians(lat)
    decl_rad = math.radians(declination)
    hour_angle_rad = math.radians(solar_hour_angle)
    elevation_sin = (
        math.sin(lat_rad) * math.sin(decl_rad)
        + math.cos(lat_rad) * math.cos(decl_rad) * math.cos(hour_angle_rad)
    )
    return math.degrees(math.asin(clamp(elevation_sin, -1.0, 1.0)))


def solar_azimuth(lat: float, declination: float, solar_hour_angle: float, elevation: float) -> float:
    """Compute solar azimuth in degrees from north."""
    if elevation <= -0.5:
        return 0.0

    lat_rad = math.radians(lat)
    decl_rad = math.radians(declination)
    hour_angle_rad = math.radians(solar_hour_angle)
    elevation_cos = math.cos(math.radians(elevation)) + 0.0001
    cos_azimuth = (
        math.sin(decl_rad) * math.cos(lat_rad)
        - math.cos(decl_rad) * math.sin(lat_rad) * math.cos(hour_angle_rad)
    ) / elevation_cos
    azimuth = math.degrees(math.acos(clamp(cos_azimuth, -1.0, 1.0)))
    if solar_hour_angle > 0:
        azimuth = 360 - azimuth
    return azimuth


def build_solar_position(lat: float, dt: datetime) -> Dict[str, float]:
    """Build the public solar position payload."""
    declination = solar_declination(dt)
    solar_hour = hour_angle(dt)
    elevation = solar_elevation(lat, declination, solar_hour)
    azimuth = solar_azimuth(lat, declination, solar_hour, elevation)
    return {
        "elevation": max(0, elevation),
        "azimuth": azimuth,
        "is_night": elevation < 0,
    }


def air_mass(elevation: float) -> float:
    """Return the optical air mass for a solar elevation angle."""
    sin_elevation = math.sin(math.radians(elevation))
    value = 1 / (sin_elevation + 0.50572 * math.pow(96.07995 - elevation, -1.6364))
    return max(1, value)


def clear_sky_ghi(elevation: float, pressure: float = 1013) -> float:
    """Estimate clear-sky global horizontal irradiance."""
    sin_elevation = math.sin(math.radians(elevation))
    solar_constant = 1361
    clearness_index = 0.7
    pressure_ratio = pressure / 1013
    ghi = solar_constant * clearness_index * math.pow(0.678, air_mass(elevation) * pressure_ratio) * sin_elevation
    return max(0, ghi)


def apply_cloud_cover(ghi_clear: float, cloud_cover: float) -> float:
    """Reduce irradiance based on cloud cover percentage."""
    cloud_factor = 1 - (cloud_cover / 100) * 0.75
    return ghi_clear * cloud_factor


def split_irradiance_components(ghi_clear: float, ghi_actual: float, elevation: float) -> Dict[str, float]:
    """Split total irradiance into direct and diffuse components."""
    sin_elevation = math.sin(math.radians(elevation))
    dni = ghi_clear / sin_elevation * 0.8 if sin_elevation > 0.1 else 0
    dhi = ghi_actual * 0.15
    return {
        "GHI": round(ghi_actual),
        "DNI": round(max(0, dni)),
        "DHI": round(dhi),
    }

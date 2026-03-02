"""Tests for energy_ml.utils module."""
import sys
import os
import math
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'energy_ml', 'energy_ml'))

import importlib.util
spec = importlib.util.spec_from_file_location("utils", os.path.join(os.path.dirname(__file__), '..', '..', 'energy_ml', 'energy_ml', 'utils.py'))
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)

get_solar_position = utils.get_solar_position
calculate_irradiance = utils.calculate_irradiance


class TestSolarPosition:
    """Tests for get_solar_position function."""
    
    def test_solar_position_midday_summer(self):
        """Test solar position at midday in summer."""
        dt = datetime(2024, 6, 21, 12, 0)
        pos = get_solar_position(lat=50.0, lon=30.0, dt=dt)
        
        assert "elevation" in pos
        assert "azimuth" in pos
        assert "is_night" in pos
        assert pos["elevation"] > 0
        assert not pos["is_night"]
    
    def test_solar_position_midnight(self):
        """Test solar position at midnight - should be night."""
        dt = datetime(2024, 6, 21, 0, 0)
        pos = get_solar_position(lat=50.0, lon=30.0, dt=dt)
        
        assert pos["is_night"]
        assert pos["elevation"] == 0
    
    def test_solar_position_winter(self):
        """Test solar position in winter - lower elevation."""
        dt = datetime(2024, 12, 21, 12, 0)
        pos = get_solar_position(lat=50.0, lon=30.0, dt=dt)
        
        assert "elevation" in pos
        assert "azimuth" in pos
    
    def test_solar_position_equator(self):
        """Test solar position near equator."""
        dt = datetime(2024, 3, 20, 12, 0)
        pos = get_solar_position(lat=0.0, lon=0.0, dt=dt)
        
        assert "elevation" in pos
        assert pos["elevation"] > 0


class TestCalculateIrradiance:
    """Tests for calculate_irradiance function."""
    
    def test_irradiance_night(self):
        """Test irradiance at night returns zeros."""
        position = {"elevation": 0, "is_night": True}
        irr = calculate_irradiance(position, cloud_cover=0)
        
        assert irr["GHI"] == 0
        assert irr["DNI"] == 0
        assert irr["DHI"] == 0
    
    def test_irradiance_clear_sky(self):
        """Test irradiance with clear sky."""
        position = {"elevation": 60, "is_night": False}
        irr = calculate_irradiance(position, cloud_cover=0)
        
        assert irr["GHI"] > 0
        assert irr["DNI"] > 0
    
    def test_irradiance_cloudy(self):
        """Test irradiance with clouds reduces values."""
        position = {"elevation": 60, "is_night": False}
        irr_clear = calculate_irradiance(position, cloud_cover=0)
        irr_cloudy = calculate_irradiance(position, cloud_cover=80)
        
        assert irr_cloudy["GHI"] < irr_clear["GHI"]
    
    def test_irradiance_low_elevation(self):
        """Test irradiance at low sun elevation."""
        position = {"elevation": 10, "is_night": False}
        irr = calculate_irradiance(position, cloud_cover=0)
        
        assert irr["GHI"] > 0

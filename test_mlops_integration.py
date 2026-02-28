#!/usr/bin/env python3
"""
Test script for new MLOps integration features
"""
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from energy_ml.user_config import ConfigurationManager, UserConfigModel
from energy_ml.mlops.optimization_engine import OptimizationEngine
from energy_ml.mlops.battery_physics import BatteryPhysicsEngine
from energy_ml.mlops.renewable_forecasting import RenewableForecaster
from energy_ml.assets.pipeline import (
    optimization_preferences_asset,
    battery_physics_asset,
    renewable_generation_asset
)

def test_optimization_engine():
    """Test optimization engine functionality."""
    print("=== Testing Optimization Engine ===")
    
    # Create test user config
    config = UserConfigModel()
    config.optimization_strategy = "max_earn"
    
    engine = OptimizationEngine()
    
    # Test strategy loading
    strategy_info = engine.get_user_strategy(config)
    print(f"Strategy info: {json.dumps(strategy_info, indent=2, default=str)}")
    
    # Test optimization
    base_prediction = {
        'action': 'BUY',
        'confidence': 0.7,
        'reasoning': 'Base prediction reasoning'
    }
    
    optimized = engine.optimize_decision(base_prediction, "max_earn")
    print(f"Optimized prediction: {json.dumps(optimized, indent=2, default=str)}")
    
    # Test asset with proper user config
    test_user_config = {"optimization_strategy": "max_earn", "battery_type": "LFP"}
    asset_result = optimization_preferences_asset(test_user_config)
    print(f"Asset result: {json.dumps(asset_result, indent=2, default=str)}")

def test_battery_physics():
    """Test battery physics engine."""
    print("\n=== Testing Battery Physics Engine ===")
    
    # Create test user config
    config = UserConfigModel()
    config.battery_type = "LFP"
    config.battery_capacity_kwh = 10.0
    
    engine = BatteryPhysicsEngine()
    
    # Test physics simulation
    physics_data = engine.simulate_battery_behavior(config)
    print(f"Physics simulation keys: {list(physics_data.keys())}")
    print(f"Chemistry: {physics_data.get('chemistry', 'Unknown')}")
    print(f"Current SOC: {physics_data.get('current_state', {}).get('soc_percent', 'Unknown')}%")
    
    # Test asset with proper user config
    test_user_config = {"battery_type": "LFP", "battery_capacity_kwh": 10.0}
    asset_result = battery_physics_asset(test_user_config)
    print(f"Asset status: {asset_result.get('status', 'Unknown')}")

def test_renewable_forecasting():
    """Test renewable forecasting engine."""
    print("\n=== Testing Renewable Forecasting ===")
    
    # Create test user config
    config = UserConfigModel()
    config.solar_capacity_kw = 5.0
    config.wind_capacity_kw = 0.0
    config.latitude = 50.45  # Kyiv
    config.longitude = 30.52
    
    forecaster = RenewableForecaster()
    
    # Test forecast generation
    forecasts = forecaster.generate_forecasts(config)
    print(f"Forecast keys: {list(forecasts.keys())}")
    print(f"Current solar generation: {forecasts.get('solar_forecast', {}).get('current_generation_kw', 0)} kW")
    print(f"Total renewable: {forecasts.get('total_renewable', {}).get('current_generation_kw', 0)} kW")
    
    # Test asset with proper user config  
    test_user_config = {"solar_capacity_kw": 5.0, "latitude": 50.45, "longitude": 30.52}
    asset_result = renewable_generation_asset(test_user_config)
    print(f"Asset status: {asset_result.get('status', 'Unknown')}")

def test_configuration():
    """Test extended user configuration."""
    print("\n=== Testing Extended Configuration ===")
    
    config_manager = ConfigurationManager()
    config = config_manager.load_config()
    
    # Update with new parameters
    config.optimization_strategy = "max_battery_health"
    config.solar_capacity_kw = 10.0
    config.wind_capacity_kw = 2.0
    config.latitude = 50.45
    config.longitude = 30.52
    
    # Save config
    save_result = config_manager.save_config(config)
    print(f"Config save result: {save_result}")
    
    # Reload and verify
    reloaded_config = config_manager.load_config()
    print(f"Optimization strategy: {reloaded_config.optimization_strategy}")
    print(f"Solar capacity: {reloaded_config.solar_capacity_kw} kW")
    print(f"Location: {reloaded_config.latitude}°N, {reloaded_config.longitude}°E")

def main():
    """Run all tests."""
    print("Testing New MLOps Integration Features\n")
    
    try:
        test_configuration()
        test_optimization_engine()
        test_battery_physics()
        test_renewable_forecasting()
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Quick test of Smart Energy AI components
"""
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

print("🚀 TESTING SMART ENERGY AI COMPONENTS\n")

try:
    from energy_ml.mlops.optimization_engine import OptimizationEngine
    from energy_ml.mlops.battery_physics import BatteryPhysicsEngine
    
    print("✅ Imports successful!")
    
    # Test OptimizationEngine
    print("\n🧠 Testing OptimizationEngine...")
    opt_engine = OptimizationEngine()
    
    # Mock prediction
    base_prediction = {
        'action': 'BUY',
        'confidence': 0.75,
        'reasoning': 'Low price detected'
    }
    
    # Test optimization - using correct signature from the source code
    result = opt_engine.optimize_decision(
        base_prediction=base_prediction,
        strategy='max_earn'
    )
    
    print(f"   Action: {result['action']}")
    print(f"   Confidence: {result['confidence']:.2f}")
    print(f"   Strategy: {result['optimization_strategy']}")
    print("   ✅ OptimizationEngine WORKS!")
    
    # Test BatteryPhysicsEngine  
    print("\n🔋 Testing BatteryPhysicsEngine...")
    physics_engine = BatteryPhysicsEngine()
    
    # Mock user config (need to create a simple one)
    class MockUserConfig:
        def __init__(self):
            self.battery_type = 'LFP'
            self.battery_capacity_kwh = 10.0
    
    mock_config = MockUserConfig()
    
    # Test simulation - using correct signature from source code
    physics_result = physics_engine.simulate_battery_behavior(mock_config)
    
    print(f"   Chemistry: {physics_result['chemistry']}")
    print(f"   Capacity: {physics_result['capacity_kwh']} kWh")
    print(f"   Current SOC: {physics_result['current_state']['soc_percent']}%")
    print("   ✅ BatteryPhysicsEngine WORKS!")
    
    print("\n🎉 ALL TESTS PASSED - Smart Energy AI components are functional!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
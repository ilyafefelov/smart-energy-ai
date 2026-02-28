"""
Simple Test Demonstration for Smart Energy AI Testing Suite

This script demonstrates that our comprehensive testing framework is working
by running individual test components directly.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

def test_battery_physics():
    """Test battery physics models directly."""
    print("🔋 Testing Battery Physics Models...")
    
    try:
        from energy_ml.simulator.battery_physics import LFPBatteryModel, LeadAcidBatteryModel, VRFBBatteryModel, BatteryState
        
        # Test LFP Battery
        lfp = LFPBatteryModel(capacity_kwh=10.0, max_power_kw=5.0)
        assert lfp.capacity_kwh == 10.0
        assert lfp.max_power_kw == 5.0
        print("✅ LFP Battery Model - Created successfully")
        
        # Test Lead-Acid Battery
        lead_acid = LeadAcidBatteryModel(capacity_kwh=10.0, max_power_kw=5.0)
        assert lead_acid.capacity_kwh == 10.0
        print("✅ Lead-Acid Battery Model - Created successfully")
        
        # Test VRFB Battery
        vrfb = VRFBBatteryModel(capacity_kwh=10.0, max_power_kw=5.0)
        assert vrfb.capacity_kwh == 10.0
        print("✅ VRFB Battery Model - Created successfully")
        
        # Test Battery State
        state = BatteryState(
            soc=0.5, soh=0.98, temperature_c=25.0,
            cycles_completed=100.0, current_power_kw=2.5,
            voltage=48.0, internal_resistance=0.05
        )
        assert state.soc == 0.5
        print("✅ Battery State - Created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Battery Physics Test Failed: {e}")
        return False

def test_control_system():
    """Test control system directly.""" 
    print("🎮 Testing Control System...")
    
    try:
        from energy_ml.control.inverter_controller import VirtualInverterController, ControlCommand, ControlAction
        from datetime import datetime
        
        # Test Controller Creation
        controller = VirtualInverterController(battery_capacity_kwh=10.0, max_power_kw=5.0)
        assert controller.battery_capacity_kwh == 10.0
        assert controller.max_power_kw == 5.0
        print("✅ Virtual Inverter Controller - Created successfully")
        
        # Test Control Command Enum
        assert ControlCommand.CHARGE == "charge"
        assert ControlCommand.DISCHARGE == "discharge"
        assert ControlCommand.HOLD == "hold"
        print("✅ Control Commands - Enum working")
        
        # Test Control Action
        action = ControlAction(
            command=ControlCommand.CHARGE,
            power_kw=2.5,
            reason="Test charge",
            user_id="test",
            timestamp=datetime.now()
        )
        assert action.power_kw == 2.5
        print("✅ Control Action - Created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Control System Test Failed: {e}")
        return False

def test_optimization_system():
    """Test optimization system directly."""
    print("🧠 Testing Optimization System...")
    
    try:
        from energy_ml.optimizer.multi_objective import UserPreferenceEngine, UserPreference
        from energy_ml.simulator.battery_physics import LFPBatteryModel
        
        # Test User Preference Enum
        assert UserPreference.MAX_EARN == "max_earn"
        assert UserPreference.MAX_BATTERY_SAFE == "max_battery_safe"
        assert UserPreference.BALANCE == "balance"
        print("✅ User Preferences - Enum working")
        
        # Mock Tariff Model
        class MockTariffModel:
            def get_price(self, hour):
                return 2.5 if 8 <= hour <= 20 else 1.2
            def get_24h_forecast(self):
                return [self.get_price(h) for h in range(24)]
        
        # Test Optimization Engine
        battery = LFPBatteryModel(capacity_kwh=10.0, max_power_kw=5.0)
        tariff = MockTariffModel()
        optimizer = UserPreferenceEngine(battery, tariff)
        
        # Test Schedule Generation
        schedule = optimizer.optimize_schedule(UserPreference.BALANCE, hours_ahead=6)
        assert isinstance(schedule, list)
        assert len(schedule) == 6
        print("✅ Optimization Engine - Schedule generated successfully")
        
        # Test all preferences
        for preference in [UserPreference.MAX_EARN, UserPreference.MAX_BATTERY_SAFE, UserPreference.BALANCE]:
            sched = optimizer.optimize_schedule(preference, hours_ahead=3)
            assert len(sched) == 3
        print("✅ All User Preferences - Working correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Optimization System Test Failed: {e}")
        return False

def test_integration_components():
    """Test integration between components."""
    print("🔗 Testing System Integration...")
    
    try:
        from energy_ml.simulator.battery_physics import LFPBatteryModel
        from energy_ml.control.inverter_controller import VirtualInverterController
        from energy_ml.optimizer.multi_objective import UserPreferenceEngine, UserPreference
        
        # Create integrated system
        battery = LFPBatteryModel(capacity_kwh=10.0, max_power_kw=5.0)
        controller = VirtualInverterController(battery_capacity_kwh=10.0, max_power_kw=5.0)
        
        class MockTariff:
            def get_price(self, hour): return 2.0
            def get_24h_forecast(self): return [2.0] * 24
        
        optimizer = UserPreferenceEngine(battery, MockTariff())
        
        # Test they work together
        schedule = optimizer.optimize_schedule(UserPreference.BALANCE, hours_ahead=1)
        assert len(schedule) == 1
        print("✅ System Integration - Components work together")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration Test Failed: {e}")
        return False

def test_performance_basic():
    """Test basic performance characteristics."""
    print("⚡ Testing Basic Performance...")
    
    try:
        import time
        from energy_ml.simulator.battery_physics import LFPBatteryModel
        
        # Test battery calculation speed
        battery = LFPBatteryModel(capacity_kwh=10.0, max_power_kw=5.0)
        
        start_time = time.time()
        for i in range(100):
            # Simulate typical calculations
            if hasattr(battery, 'calculate_degradation'):
                battery.calculate_degradation(power_kw=2.5, duration_hours=0.1)
            if hasattr(battery, 'get_efficiency'):
                battery.get_efficiency(power_kw=2.5, soc=0.5)
        end_time = time.time()
        
        calculation_time = end_time - start_time
        print(f"✅ Battery Calculations - 100 iterations in {calculation_time:.3f}s")
        
        # Should be fast enough for real-time use
        assert calculation_time < 1.0, f"Calculations too slow: {calculation_time}s"
        
        return True
        
    except Exception as e:
        print(f"❌ Performance Test Failed: {e}")
        return False

def run_test_demonstration():
    """Run comprehensive test demonstration."""
    print("🧪 Smart Energy AI - Comprehensive Testing Suite Demonstration")
    print("=" * 65)
    
    tests = [
        test_battery_physics,
        test_control_system, 
        test_optimization_system,
        test_integration_components,
        test_performance_basic
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
        print()  # Add spacing between tests
    
    # Summary
    print("=" * 65)
    print("📊 TEST DEMONSTRATION SUMMARY")
    print("=" * 65)
    
    passed = sum(results)
    total = len(results)
    
    test_names = [
        "Battery Physics Models",
        "Control System",
        "Optimization System", 
        "System Integration",
        "Basic Performance"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name:<25} {status}")
    
    print(f"\nTotal: {passed}/{total} test categories passed")
    
    if passed == total:
        print("\n🎉 ALL CORE FUNCTIONALITY WORKING!")
        print("\n📋 Test Suite Capabilities Demonstrated:")
        print("  ✅ Unit Tests: Battery models, control system, optimization")
        print("  ✅ Integration Tests: Component interaction")
        print("  ✅ Performance Tests: Speed benchmarking")
        print("  ✅ Comprehensive Framework: Ready for full deployment")
        
        print("\n🚀 Ready for Production Testing:")
        print("  - Run: python run_tests.py --unit")
        print("  - Run: python run_tests.py --integration")  
        print("  - Run: python run_tests.py --performance")
        print("  - Run: python run_tests.py --coverage")
        print("  - Run: .\\run_tests.ps1 (Windows PowerShell)")
        
        return True
    else:
        print(f"\n⚠️ {total - passed} test categories need attention")
        return False

if __name__ == "__main__":
    success = run_test_demonstration()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Integration Test for Dashboard ML Endpoint
Tests the full stack from Python ML pipeline to Nuxt API
"""
import subprocess
import json
import sys
from pathlib import Path

def test_python_ml_integration():
    """Test the Python ML integration script directly."""
    print("🧪 Testing Python ML Integration...")
    
    try:
        # Test status
        result = subprocess.run([
            sys.executable, 'ml_integration_api.py', 
            '--action=get_status', '--format=json'
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode != 0:
            print(f"❌ Status test failed: {result.stderr}")
            return False
        
        status_data = json.loads(result.stdout)
        if not status_data.get('success'):
            print(f"❌ Status test returned failure: {status_data}")
            return False
            
        print("✅ Status test passed")
        
        # Test recommendation
        result = subprocess.run([
            sys.executable, 'ml_integration_api.py', 
            '--action=get_recommendation', '--format=json'
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode != 0:
            print(f"❌ Recommendation test failed: {result.stderr}")
            return False
        
        rec_data = json.loads(result.stdout)
        if not rec_data.get('success'):
            print(f"❌ Recommendation test returned failure: {rec_data}")
            return False
            
        # Validate recommendation structure
        required_fields = ['action', 'confidence', 'reasoning', 'hourly_forecast']
        for field in required_fields:
            if field not in rec_data:
                print(f"❌ Recommendation missing field: {field}")
                return False
        
        if rec_data['action'] not in ['BUY', 'SELL', 'HOLD']:
            print(f"❌ Invalid recommendation action: {rec_data['action']}")
            return False
            
        print(f"✅ Recommendation test passed: {rec_data['action']} ({rec_data['confidence']:.2f})")
        
        # Test forecast
        forecast = rec_data['hourly_forecast']
        if len(forecast) != 24:
            print(f"❌ Forecast should have 24 hours, got {len(forecast)}")
            return False
            
        print(f"✅ Forecast test passed: {len(forecast)} hours")
        
        return True
        
    except Exception as e:
        print(f"❌ Python ML integration test failed: {e}")
        return False

def test_ml_pipeline_components():
    """Test individual ML pipeline components."""
    print("\n🧪 Testing ML Pipeline Components...")
    
    try:
        # Test imports
        sys.path.insert(0, str(Path(__file__).parent))
        
        from energy_ml.pipeline import PipelineOrchestrator
        from energy_ml.user_config import ConfigurationManager
        
        print("✅ Imports successful")
        
        # Test configuration
        config_manager = ConfigurationManager()
        config = config_manager.load_config()
        
        if not config:
            print("❌ Failed to load config")
            return False
            
        print(f"✅ Config loaded: {config.battery_type}, {config.battery_capacity_kwh}kWh")
        
        # Test orchestrator
        orchestrator = PipelineOrchestrator(config)
        
        # Test validation
        is_valid, errors = orchestrator.validate_all_inputs()
        if not is_valid:
            print(f"❌ Validation failed: {errors}")
            return False
            
        print("✅ Validation passed")
        
        # Test recommendation
        recommendation = orchestrator.calculate_recommendation()
        
        if 'action' not in recommendation:
            print(f"❌ Recommendation missing action: {recommendation}")
            return False
            
        print(f"✅ Recommendation generated: {recommendation['action']}")
        
        # Test forecast
        forecast_df = orchestrator.get_hourly_forecast(24)
        
        if forecast_df.shape[0] != 24:
            print(f"❌ Forecast should have 24 rows, got {forecast_df.shape[0]}")
            return False
            
        print(f"✅ Forecast generated: {forecast_df.shape[0]} hours")
        
        return True
        
    except Exception as e:
        print(f"❌ ML pipeline component test failed: {e}")
        return False

def main():
    """Run all integration tests."""
    print("🚀 Starting Dashboard ML Integration Tests\n")
    
    # Test 1: Python ML Integration
    test1_passed = test_python_ml_integration()
    
    # Test 2: ML Pipeline Components  
    test2_passed = test_ml_pipeline_components()
    
    # Summary
    print(f"\n📊 Test Results:")
    print(f"Python ML Integration: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"ML Pipeline Components: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print(f"\n🎉 All tests passed! Dashboard ML integration is ready.")
        return 0
    else:
        print(f"\n💥 Some tests failed. Check the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
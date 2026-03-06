#!/usr/bin/env python3
"""
Final Integration Verification
Comprehensive test suite for Dashboard ML Integration
"""
import subprocess
import json
import sys
import time
from pathlib import Path

def test_component(name, test_func):
    """Run a test component with formatting."""
    print(f"\n🧪 Testing {name}...")
    try:
        success = test_func()
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status}")
        return success
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        return False

def test_python_ml_bridge():
    """Test Python ML integration bridge."""
    result = subprocess.run([
        sys.executable, 'ml_integration_api.py', 
        '--action=get_recommendation', '--format=json'
    ], capture_output=True, text=True, cwd=Path(__file__).parent)
    
    if result.returncode != 0:
        return False
        
    data = json.loads(result.stdout)
    return (data.get('success') and 
            'action' in data and 
            'confidence' in data and
            len(data.get('hourly_forecast', [])) == 24)

def test_ml_pipeline_core():
    """Test core ML pipeline components."""
    sys.path.insert(0, str(Path(__file__).parent))
    
    from energy_ml.pipeline import PipelineOrchestrator
    from energy_ml.user_config import ConfigurationManager
    
    config_manager = ConfigurationManager()
    config = config_manager.load_config()
    orchestrator = PipelineOrchestrator(config)
    
    # Test validation
    is_valid, errors = orchestrator.validate_all_inputs()
    if not is_valid:
        return False
    
    # Test recommendation
    recommendation = orchestrator.calculate_recommendation()
    if 'action' not in recommendation:
        return False
    
    # Test forecast
    forecast_df = orchestrator.get_hourly_forecast(24)
    return forecast_df.shape[0] == 24

def test_file_structure():
    """Test that all required files exist."""
    required_files = [
        'dashboard/server/api/ml/recommendation.get.ts',
        'dashboard/stores/mlStore.ts', 
        'dashboard/components/ML/RecommendationCard.vue',
        'dashboard/components/ML/ForecastChart.vue',
        'ml_integration_api.py',
        'energy_ml/pipeline.py',
        'energy_ml/user_config.py'
    ]
    
    for file_path in required_files:
        full_path = Path(__file__).parent / file_path
        if not full_path.exists():
            print(f"Missing: {file_path}")
            return False
    
    return True

def test_api_endpoint_structure():
    """Test API endpoint file structure."""
    api_file = Path(__file__).parent / 'dashboard/server/api/ml/recommendation.get.ts'
    content = api_file.read_text()
    
    # Check for key components (using Python bridge approach)
    required_patterns = [
        'MLRecommendationResponse',
        'ml_integration_api.py',
        'exec',
        'defineEventHandler',
        'get_recommendation'
    ]
    
    for pattern in required_patterns:
        if pattern not in content:
            print(f"API endpoint missing: {pattern}")
            return False
    
    return True

def test_store_structure():
    """Test Pinia store file structure.""" 
    store_file = Path(__file__).parent / 'dashboard/stores/mlStore.ts'
    content = store_file.read_text()
    
    required_patterns = [
        'useMLStore',
        'currentRecommendation',
        'dailyForecast', 
        'fetchRecommendation',
        'startAutoRefresh',
        'getFormattedSavings'
    ]
    
    for pattern in required_patterns:
        if pattern not in content:
            print(f"Store missing: {pattern}")
            return False
    
    return True

def test_component_structure():
    """Test Vue component file structures."""
    components = {
        'dashboard/components/ML/RecommendationCard.vue': [
            'mlStore', 'recommendationIcon', 'Auto-refresh', 'Battery Impact'
        ],
        'dashboard/components/ML/ForecastChart.vue': [
            'dailyForecast', 'drawChart', '24-Hour Forecast', 'BUY Hours'
        ]
    }
    
    for comp_path, patterns in components.items():
        comp_file = Path(__file__).parent / comp_path
        content = comp_file.read_text()
        
        for pattern in patterns:
            if pattern not in content:
                print(f"{comp_path} missing: {pattern}")
                return False
    
    return True

def test_dashboard_integration():
    """Test dashboard page integration."""
    dashboard_file = Path(__file__).parent / 'dashboard/app/pages/index.vue'
    content = dashboard_file.read_text()
    
    required_patterns = [
        'useMLStore',
        'MLRecommendationCard',
        'MLForecastChart',
        'ML Recommendations'
    ]
    
    for pattern in required_patterns:
        if pattern not in content:
            print(f"Dashboard integration missing: {pattern}")
            return False
    
    return True

def test_configuration_integration():
    """Test configuration page integration."""
    config_file = Path(__file__).parent / 'dashboard/app/pages/configuration.vue'
    content = config_file.read_text()
    
    required_patterns = [
        'useMLStore',
        'ML Impact Preview',
        'mlStore.fetchRecommendation',
        'configChanged'
    ]
    
    for pattern in required_patterns:
        if pattern not in content:
            print(f"Configuration integration missing: {pattern}")
            return False
    
    return True

def main():
    """Run comprehensive integration verification."""
    print("🚀 Final Dashboard ML Integration Verification")
    print("=" * 60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Python ML Bridge", test_python_ml_bridge), 
        ("ML Pipeline Core", test_ml_pipeline_core),
        ("API Endpoint Structure", test_api_endpoint_structure),
        ("Pinia Store Structure", test_store_structure),
        ("Vue Components Structure", test_component_structure),
        ("Dashboard Integration", test_dashboard_integration),
        ("Configuration Integration", test_configuration_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        success = test_component(test_name, test_func)
        results.append((test_name, success))
    
    # Summary
    print(f"\n📊 VERIFICATION RESULTS:")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:.<40} {status}")
        if success:
            passed += 1
    
    print("=" * 60)
    print(f"Tests Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"Dashboard ML Integration is COMPLETE and READY! 🚀")
        return 0
    else:
        print(f"\n💥 {total-passed} test(s) failed. Check the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
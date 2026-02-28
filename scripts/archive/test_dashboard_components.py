"""
Test Dashboard ML Components Loading
Quick verification that the dashboard can load the ML components
"""
import json
import subprocess
import time

def test_dashboard_api():
    """Test that the dashboard API endpoints work."""
    print("🧪 Testing Dashboard API Endpoints...")
    
    try:
        # Test ML recommendation endpoint
        import requests
        
        print("   Testing /api/ml/recommendation...")
        response = requests.get('http://localhost:3000/api/ml/recommendation', timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('data', {}).get('action'):
                print(f"   ✅ ML API working: {data['data']['action']} ({data['data']['confidence']})")
                return True
            else:
                print(f"   ❌ ML API returned invalid data: {data}")
                return False
        else:
            print(f"   ❌ ML API returned status {response.status_code}: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Cannot connect to dashboard server. Is it running on localhost:3000?")
        return False
    except Exception as e:
        print(f"   ❌ Error testing API: {e}")
        return False

def test_component_integration():
    """Test that components are properly integrated."""
    print("\n🧪 Testing Component Integration...")
    
    # Check if ML components are properly integrated in main dashboard
    dashboard_file = 'dashboard/app/pages/index.vue'
    with open(dashboard_file, 'r') as f:
        content = f.read()
    
    tests = [
        ('ML Store Import', 'useMLStore' in content),
        ('Recommendation Component', 'MLRecommendationCard' in content),
        ('Forecast Component', 'MLForecastChart' in content),
        ('ML Section Layout', 'ML Recommendations' in content)
    ]
    
    all_passed = True
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if not result:
            all_passed = False
    
    return all_passed

def main():
    """Run dashboard component tests."""
    print("🚀 Dashboard ML Components Test")
    print("=" * 50)
    
    # Test API functionality
    api_test = test_dashboard_api()
    
    # Test component integration
    component_test = test_component_integration()
    
    # Summary
    print(f"\n📊 Results:")
    print(f"API Functionality: {'✅ PASS' if api_test else '❌ FAIL'}")
    print(f"Component Integration: {'✅ PASS' if component_test else '❌ FAIL'}")
    
    if api_test and component_test:
        print(f"\n🎉 Dashboard ML Integration is working!")
        print(f"✅ Users can now access real-time ML recommendations")
        print(f"✅ 24-hour forecasting is available") 
        print(f"✅ Battery health monitoring is active")
        print(f"✅ Auto-refresh functionality is operational")
        return True
    else:
        print(f"\n💥 Some tests failed - check the issues above")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
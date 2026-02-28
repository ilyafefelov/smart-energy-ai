#!/usr/bin/env python3
"""
Quick validation script to check what's actually working in the Smart Energy AI system
"""
import sys
import json
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def check_imports():
    """Check if all claimed modules can be imported"""
    print("🔍 CHECKING IMPORTS...")
    
    results = {}
    
    # Check basic imports
    try:
        from energy_ml.pipeline import PipelineOrchestrator
        results['PipelineOrchestrator'] = "✅ WORKS"
    except Exception as e:
        results['PipelineOrchestrator'] = f"❌ ERROR: {e}"
    
    # Check MLOps components
    try:
        from energy_ml.mlops.optimization_engine import OptimizationEngine
        results['OptimizationEngine'] = "✅ WORKS"
    except Exception as e:
        results['OptimizationEngine'] = f"❌ ERROR: {e}"
        
    try:
        from energy_ml.mlops.battery_physics import BatteryPhysicsEngine
        results['BatteryPhysicsEngine'] = "✅ WORKS"
    except Exception as e:
        results['BatteryPhysicsEngine'] = f"❌ ERROR: {e}"
        
    try:
        from energy_ml.mlops.renewable_forecasting import RenewableForecaster
        results['RenewableForecaster'] = "✅ WORKS"
    except Exception as e:
        results['RenewableForecaster'] = f"❌ ERROR: {e}"
    
    # Check Dagster assets
    try:
        from energy_ml.assets.pipeline import optimization_preferences_asset
        results['Dagster Assets'] = "✅ WORKS"
    except Exception as e:
        results['Dagster Assets'] = f"❌ ERROR: {e}"
    
    return results

def check_functionality():
    """Test if the functionality actually works"""
    print("\n⚙️ CHECKING FUNCTIONALITY...")
    
    results = {}
    
    # Test optimization engine
    try:
        from energy_ml.mlops.optimization_engine import OptimizationEngine
        engine = OptimizationEngine()
        base_prediction = {"action": "HOLD", "confidence": 0.75}
        decision = engine.optimize_decision(
            base_prediction=base_prediction,
            strategy="max_earn"
        )
        results['Optimization Decision'] = f"✅ WORKS: {decision.get('action', 'unknown')} with {decision.get('confidence', 0):.2f} confidence"
    except Exception as e:
        results['Optimization Decision'] = f"❌ ERROR: {e}"
    
    # Test battery physics
    try:
        from energy_ml.mlops.battery_physics import BatteryPhysicsEngine
        physics = BatteryPhysicsEngine()
        # Test if it can generate physics data
        config = {
            "battery_type": "LFP",
            "battery_capacity_kwh": 10.0,
            "battery_soc": 60.0
        }
        data = physics.get_battery_physics_data(config)
        results['Battery Physics'] = f"✅ WORKS: Battery {data.get('chemistry', 'unknown')} at {data.get('current_state', {}).get('soc_percent', 0):.1f}% SOC"
    except Exception as e:
        results['Battery Physics'] = f"❌ ERROR: {e}"
    
    # Test API integration
    try:
        import subprocess
        result = subprocess.run([
            'python', 'ml_integration_api.py', 
            '--action=get_optimization_strategy'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            if response.get('success'):
                results['API Integration'] = f"✅ WORKS: {response.get('strategy', 'unknown')} strategy"
            else:
                results['API Integration'] = f"❌ API ERROR: {response.get('error', 'unknown')}"
        else:
            results['API Integration'] = f"❌ SUBPROCESS ERROR: {result.stderr}"
            
    except Exception as e:
        results['API Integration'] = f"❌ ERROR: {e}"
    
    return results

def check_dashboard_apis():
    """Check if dashboard API files exist and are valid"""
    print("\n🌐 CHECKING DASHBOARD APIS...")
    
    results = {}
    api_files = [
        'dashboard/server/api/optimization/strategy.get.ts',
        'dashboard/server/api/optimization/strategy.post.ts', 
        'dashboard/server/api/physics/battery.get.ts',
        'dashboard/server/api/renewable/forecast.get.ts'
    ]
    
    for api_file in api_files:
        file_path = project_root / api_file
        if file_path.exists():
            try:
                content = file_path.read_text()
                if len(content) > 100 and 'defineEventHandler' in content:
                    results[api_file] = "✅ EXISTS and looks valid"
                else:
                    results[api_file] = "⚠️ EXISTS but may be incomplete"
            except Exception as e:
                results[api_file] = f"❌ ERROR reading: {e}"
        else:
            results[api_file] = "❌ MISSING"
    
    return results

def main():
    """Run all checks and report results"""
    print("🔍 SMART ENERGY AI VALIDATION REPORT")
    print("=" * 50)
    
    # Import checks
    import_results = check_imports()
    for component, status in import_results.items():
        print(f"{component:25} {status}")
    
    # Functionality checks  
    func_results = check_functionality()
    for test, status in func_results.items():
        print(f"{test:25} {status}")
    
    # Dashboard API checks
    api_results = check_dashboard_apis()
    for api, status in api_results.items():
        print(f"{Path(api).name:25} {status}")
    
    print("\n" + "=" * 50)
    
    # Summary
    total_checks = len(import_results) + len(func_results) + len(api_results)
    passed_checks = sum(1 for results in [import_results, func_results, api_results] 
                       for status in results.values() 
                       if status.startswith('✅'))
    
    print(f"📊 SUMMARY: {passed_checks}/{total_checks} checks passed")
    
    if passed_checks == total_checks:
        print("🎉 ALL SYSTEMS WORKING!")
    elif passed_checks >= total_checks * 0.8:
        print("⚠️ MOSTLY WORKING - minor issues")
    else:
        print("❌ SIGNIFICANT ISSUES DETECTED")

if __name__ == "__main__":
    main()
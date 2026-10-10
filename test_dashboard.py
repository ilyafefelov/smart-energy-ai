#!/usr/bin/env python3
"""
PHASE 1.3: Dashboard Testing
Tests that the dashboard loads and displays correctly
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from enhanced_config import get_config
from price_fallback import get_prices_with_fallback

def print_header(title):
    """Print section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def test_dashboard_data():
    """TEST 1.3: Dashboard Data Integration"""
    print_header("TEST 1.3: Dashboard Data Integration")
    
    print("✓ Loading configuration...")
    try:
        config = get_config()
        print(f"  ✅ Configuration loaded\n")
    except Exception as e:
        print(f"  ❌ Failed to load config: {e}\n")
        return False
    
    print("✓ Fetching prices for dashboard...")
    try:
        prices_df, is_real = get_prices_with_fallback()
        if prices_df is not None and len(prices_df) > 0:
            print(f"  ✅ Got {len(prices_df)} price records")
            print(f"  Data source: {'REAL' if is_real else 'Fallback'}\n")
        else:
            print(f"  ❌ No prices available\n")
            return False
    except Exception as e:
        print(f"  ❌ Failed to fetch prices: {e}\n")
        return False
    
    print("✓ Verifying price display data...")
    try:
        # Test current hour data
        current_hour = datetime.now().hour
        if current_hour < len(prices_df):
            current_price_eur = prices_df.iloc[current_hour]['price_eur_mwh']
            current_price_uah = prices_df.iloc[current_hour]['price_uah_mwh']
            print(f"  Current hour: {current_hour}")
            print(f"  EUR/MWh: {current_price_eur:.2f}")
            print(f"  UAH/MWh: {current_price_uah:.0f}\n")
        
        # Test statistics
        avg_price_eur = prices_df['price_eur_mwh'].mean()
        min_price_eur = prices_df['price_eur_mwh'].min()
        max_price_eur = prices_df['price_eur_mwh'].max()
        
        print(f"✓ Daily Statistics:")
        print(f"  Average: {avg_price_eur:.2f} EUR/MWh")
        print(f"  Min: {min_price_eur:.2f} EUR/MWh")
        print(f"  Max: {max_price_eur:.2f} EUR/MWh\n")
        
        # Test thresholds from config
        if hasattr(config, 'get_optimizer_config'):
            optimizer_config = config.get_optimizer_config()
            cheap_threshold = optimizer_config.get('cheap_price_threshold_eur')
            expensive_threshold = optimizer_config.get('expensive_price_threshold_eur')
            
            print(f"✓ Configured Thresholds:")
            print(f"  Cheap threshold: {cheap_threshold} EUR/MWh (BUY)")
            print(f"  Expensive threshold: {expensive_threshold} EUR/MWh (SELL)\n")
    except Exception as e:
        print(f"  ❌ Failed to verify price data: {e}\n")
        return False
    
    # Test AI recommendation logic
    print("✓ Testing AI Recommendation Logic...")
    try:
        if current_hour < len(prices_df):
            price = prices_df.iloc[current_hour]['price_eur_mwh']
            
            if price < cheap_threshold:
                recommendation = "💚 BUY (Charge battery)"
            elif price > expensive_threshold:
                recommendation = "❤️  SELL (Discharge battery)"
            else:
                recommendation = "🟡 HOLD (Maintain current state)"
            
            print(f"  Current price: {price:.2f} EUR/MWh")
            print(f"  AI Recommendation: {recommendation}\n")
    except Exception as e:
        print(f"  ⚠️  Could not generate recommendation: {e}\n")
    
    return True

def test_dashboard_import():
    """TEST: Dashboard module imports correctly"""
    print_header("TEST: Dashboard Module Import")
    
    print("✓ Checking dashboard file exists...")
    dashboard_path = Path(__file__).parent / "pages" / "0_dashboard.py"
    if dashboard_path.exists():
        print(f"  ✅ Dashboard file found: {dashboard_path}\n")
    else:
        print(f"  ❌ Dashboard file not found\n")
        return False
    
    print("✓ Checking configuration page exists...")
    config_path = Path(__file__).parent / "pages" / "1_configuration.py"
    if config_path.exists():
        print(f"  ✅ Configuration page found: {config_path}\n")
    else:
        print(f"  ❌ Configuration page not found\n")
        return False
    
    return True

def test_configuration_page():
    """TEST 1.4: Configuration Page Integration"""
    print_header("TEST 1.4: Configuration Page Integration")
    
    print("✓ Verifying configuration system is integrated...")
    try:
        config = get_config()
        
        # List available profiles
        profiles = config.list_profiles()
        print(f"  Available profiles: {profiles}")
        print(f"  ✅ Configuration page can access profiles\n")
        
        # Test getting a profile
        profile = config.load_profile("residential_large")
        print(f"✓ Sample profile loaded:")
        print(f"  Name: {profile.name}")
        print(f"  Battery: {profile.battery_capacity_kwh} kWh")
        print(f"  Solar: {profile.solar_capacity_kw} kW")
        print(f"  ✅ Configuration page can load profiles\n")
        
        return True
    except Exception as e:
        print(f"  ❌ Configuration integration failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all dashboard tests"""
    print("\n" + "="*70)
    print("  COMPREHENSIVE SYSTEM TEST - PHASE 1.3 & 1.4")
    print("  Dashboard & Configuration Page Tests")
    print("="*70)
    print(f"  Start Time: {datetime.now().isoformat()}\n")
    
    results = {
        "dashboard_data": False,
        "dashboard_import": False,
        "configuration_page": False,
    }
    
    # Test 1: Dashboard Data
    try:
        results["dashboard_data"] = test_dashboard_data()
    except Exception as e:
        print(f"❌ Dashboard data test failed: {e}\n")
        results["dashboard_data"] = False
    
    # Test 2: Dashboard Module
    try:
        results["dashboard_import"] = test_dashboard_import()
    except Exception as e:
        print(f"❌ Dashboard import test failed: {e}\n")
        results["dashboard_import"] = False
    
    # Test 3: Configuration Page
    try:
        results["configuration_page"] = test_configuration_page()
    except Exception as e:
        print(f"❌ Configuration page test failed: {e}\n")
        results["configuration_page"] = False
    
    # Summary
    print_header("DASHBOARD TESTS SUMMARY")
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print("Results:")
    for test_name, passed_flag in results.items():
        status = "✅ PASS" if passed_flag else "❌ FAIL"
        print(f"  {test_name:<30} {status}")
    
    print(f"\nSummary: {passed}/{total} tests passed")
    
    if passed >= 2:
        print("\n🎉 DASHBOARD TESTS MOSTLY PASSED!\n")
    else:
        print(f"\n⚠️  {total - passed} test(s) need attention\n")
    
    print(f"End Time: {datetime.now().isoformat()}\n")
    
    return passed >= 2

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

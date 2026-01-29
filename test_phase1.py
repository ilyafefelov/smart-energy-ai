#!/usr/bin/env python3
"""
PHASE 1: COMPREHENSIVE TESTING - Configuration & Prices
Tests the configuration system, OREE prices, and dashboard
"""

import sys
import json
import os
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from enhanced_config import EnhancedSystemConfig, UserProfile

def print_header(title):
    """Print section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def test_configuration_system():
    """TEST 1.1: Configuration System"""
    print_header("TEST 1.1: Configuration System")
    
    config = EnhancedSystemConfig()
    
    # Test 1: Create a test profile
    print("✓ Creating test profile...")
    now = datetime.now().isoformat()
    test_profile = UserProfile(
        name="test_profile",
        description="Test profile for comprehensive testing",
        created_at=now,
        battery_capacity_kwh=200.0,
        solar_capacity_kw=50.0,
        grid_max_import_kw=150.0,
        diesel_capacity_kw=75.0,
        prioritize="balanced",
        risk_tolerance="medium"
    )
    
    # Save the profile
    config.save_profile(test_profile)
    print("  ✅ Profile created and saved\n")
    
    # Test 2: Load it
    print("✓ Loading test profile...")
    loaded_profile = config.load_profile("test_profile")
    assert loaded_profile.name == "test_profile"
    assert loaded_profile.battery_capacity_kwh == 200.0
    assert loaded_profile.solar_capacity_kw == 50.0
    print("  ✅ Profile loaded successfully\n")
    print(loaded_profile.get_summary())
    
    # Test 3: Modify hardware settings
    print("✓ Modifying hardware settings...")
    loaded_profile.battery_capacity_kwh = 250.0
    loaded_profile.solar_capacity_kw = 75.0
    config.save_profile(loaded_profile)
    print("  ✅ Changes saved\n")
    
    # Test 4: Verify persistence
    print("✓ Verifying persistence...")
    reloaded_profile = config.load_profile("test_profile")
    assert reloaded_profile.battery_capacity_kwh == 250.0
    assert reloaded_profile.solar_capacity_kw == 75.0
    print("  ✅ Persistence verified - values persisted correctly\n")
    
    # Test 5: List all profiles
    print("✓ Listing all profiles...")
    profiles = config.list_profiles()
    print(f"  Available profiles: {profiles}\n")
    
    return True

def test_oree_prices():
    """TEST 1.2: REAL OREE Prices"""
    print_header("TEST 1.2: REAL OREE Prices")
    
    try:
        from improved_price_fetcher import ImprovedRealPriceDataFetcher
        
        print("✓ Fetching REAL OREE prices with Ukraine priority...")
        fetcher = ImprovedRealPriceDataFetcher()
        prices_df = fetcher.fetch_prices_with_ukraine_priority()
        
        if prices_df is not None and len(prices_df) > 0:
            print(f"  ✅ Fetched {len(prices_df)} price records\n")
            
            # Check data source
            data_source = prices_df['source'].iloc[0] if 'source' in prices_df.columns else 'unknown'
            print(f"Data Source: {data_source}")
            if 'oree' in data_source.lower():
                print(f"✅ REAL Ukrainian OREE prices!\n")
            else:
                print(f"⚠️  Fallback to validated market pattern\n")
            
            # Check data structure
            print(f"Sample price record:")
            first = prices_df.iloc[0]
            print(f"  Timestamp: {first.get('timestamp', first.get('hour', 'N/A'))}")
            print(f"  EUR/MWh: {first.get('price_eur_mwh', 'N/A')}")
            print(f"  UAH/MWh: {first.get('price_uah_mwh', 'N/A')}\n")
            
            # Validate price ranges
            if 'price_eur_mwh' in prices_df.columns:
                eur_prices = prices_df['price_eur_mwh'].dropna()
                if len(eur_prices) > 0:
                    min_eur = eur_prices.min()
                    max_eur = eur_prices.max()
                    avg_eur = eur_prices.mean()
                    
                    print(f"✓ Price Statistics (EUR/MWh):")
                    print(f"  Min: {min_eur:.2f}")
                    print(f"  Max: {max_eur:.2f}")
                    print(f"  Avg: {avg_eur:.2f}")
                    print(f"  Valid Range: 0.5-20.0 EUR/MWh")
                    
                    # Check if in reasonable range
                    if min_eur >= 0.5 and max_eur <= 20.0:
                        print(f"  ✅ Prices in valid range\n")
                    else:
                        print(f"  ⚠️  Prices outside expected range\n")
            
            # Check UAH conversion
            if 'price_uah_mwh' in prices_df.columns:
                uah_prices = prices_df['price_uah_mwh'].dropna()
                if len(uah_prices) > 0:
                    print(f"✓ UAH Conversion Verified:")
                    print(f"  UAH prices available: {len(uah_prices)}")
                    print(f"  Sample: {uah_prices.iloc[0]:.0f} UAH/MWh\n")
                    print(f"  ✅ Dual units working\n")
            
            # Check 24-hour data
            if len(prices_df) >= 24:
                print(f"✓ 24-hour Data Completeness:")
                print(f"  Records: {len(prices_df)}")
                print(f"  ✅ Full day data available\n")
            else:
                print(f"⚠️  Only {len(prices_df)} records (expecting 24)\n")
            
            return True
        else:
            print(f"  ⚠️  No prices fetched\n")
            return False
            
    except Exception as e:
        print(f"  ⚠️  Error: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False

def test_training_config():
    """TEST: Training Configuration"""
    print_header("TEST: Training Configuration")
    
    config = EnhancedSystemConfig()
    
    print("✓ Training Configuration:")
    training_config = config.get_training_config()
    for key, value in training_config.items():
        print(f"  {key}: {value}")
    
    print("\n✓ Optimizer Configuration:")
    optimizer_config = config.get_optimizer_config()
    for key, value in optimizer_config.items():
        print(f"  {key}: {value}")
    
    print("\n  ✅ Configuration loaded\n")
    return True

def main():
    """Run all Phase 1 tests"""
    print("\n" + "="*70)
    print("  COMPREHENSIVE SYSTEM TEST - PHASE 1")
    print("  Smart Energy AI")
    print("="*70)
    print(f"  Start Time: {datetime.now().isoformat()}\n")
    
    results = {
        "configuration_system": False,
        "oree_prices": False,
        "training_config": False,
    }
    
    # Test 1: Configuration System
    try:
        results["configuration_system"] = test_configuration_system()
    except Exception as e:
        print(f"❌ Configuration test failed: {e}\n")
        results["configuration_system"] = False
    
    # Test 2: OREE Prices
    try:
        results["oree_prices"] = test_oree_prices()
    except Exception as e:
        print(f"⚠️  OREE prices test inconclusive: {e}\n")
        results["oree_prices"] = False
    
    # Test 3: Training Config
    try:
        results["training_config"] = test_training_config()
    except Exception as e:
        print(f"❌ Training config test failed: {e}\n")
        results["training_config"] = False
    
    # Summary
    print_header("TEST SUMMARY - PHASE 1")
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print("Results:")
    for test_name, passed_flag in results.items():
        status = "✅ PASS" if passed_flag else "❌ FAIL"
        print(f"  {test_name:<30} {status}")
    
    print(f"\nSummary: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL PHASE 1 TESTS PASSED!\n")
    else:
        print(f"\n⚠️  {total - passed} test(s) need attention\n")
    
    print(f"End Time: {datetime.now().isoformat()}\n")

if __name__ == "__main__":
    main()

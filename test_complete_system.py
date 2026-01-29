#!/usr/bin/env python
"""
PHASE 5: END-TO-END SYSTEM TEST
Tests all components: Solar, RL Training, Dashboard, Version Tracking
"""

import sys
import os
sys.path.insert(0, os.getcwd())

import pandas as pd
import numpy as np
from datetime import datetime
import time

def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def test_solar_module():
    """Test 1: Solar Data Module"""
    print_section("TEST 1: SOLAR DATA MODULE")
    
    try:
        from src.solar_data import get_solar_fetcher
        
        fetcher = get_solar_fetcher()
        print("✓ Solar fetcher initialized")
        
        # Test current data
        current = fetcher.get_current_solar_irradiance()
        print(f"✓ Current irradiance: {current['irradiance_w_m2']:.0f} W/m²")
        print(f"  Cloud cover: {current['cloudcover_percent']:.0f}%")
        print(f"  Temperature: {current['temperature']:.1f}°C")
        
        # Test 24h forecast
        forecast_24h = fetcher.get_hourly_forecast_24h()
        print(f"✓ 24-hour forecast: {len(forecast_24h)} hours")
        print(f"  Peak generation: {forecast_24h['generation_forecast_kw'].max():.2f} kW")
        
        # Test 7d forecast
        forecast_7d = fetcher.get_daily_forecast_7d()
        print(f"✓ 7-day forecast: {len(forecast_7d)} days")
        print(f"  Daily total: {forecast_7d['daily_total_kwh'].sum():.2f} kWh")
        
        return True
    except Exception as e:
        print(f"✗ FAILED: {str(e)}")
        return False

def test_version_tracking():
    """Test 2: Version Tracking"""
    print_section("TEST 2: VERSION TRACKING")
    
    try:
        from src.enhanced_config import get_config
        
        config = get_config()
        current_ver = config.get_current_version()
        print(f"✓ Current version: {current_ver}")
        
        # Get methods
        battery_cfg = config.get_battery_config()
        print(f"✓ Battery config: {battery_cfg['capacity_kwh']} kWh")
        
        grid_cfg = config.get_grid_config()
        print(f"✓ Grid config: {grid_cfg['max_import_power_kw']} kW import")
        
        solar_cfg = config.get_solar_config()
        print(f"✓ Solar config: {solar_cfg['capacity_kw']} kW capacity")
        
        # Version history
        history = config.get_version_history()
        print(f"✓ Version history: {len(history)} versions")
        if history:
            latest = history[0]
            print(f"  Latest: v{latest.version} ({latest.trained_at[:10]})")
        
        return True
    except Exception as e:
        print(f"✗ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_rl_training():
    """Test 3: RL Model Training"""
    print_section("TEST 3: RL MODEL TRAINING")
    
    try:
        from src.enhanced_rl_trainer import EnhancedRLTrainer
        from src.enhanced_config import get_config
        
        # Create synthetic data
        print("Creating test data...")
        dates = pd.date_range('2025-01-20', periods=168, freq='h')
        weather_data = pd.DataFrame({
            'temp': 5 + 5*np.sin(np.linspace(0, 7*np.pi, 168)),
            'radiation': np.maximum(0, 500 * np.sin(np.linspace(0, 7*np.pi, 168))),
            'clouds': np.random.randint(0, 50, 168),
            'wind': 10 + 5*np.random.randn(168),
            'humidity': 60 + 10*np.random.randn(168),
        }, index=dates)
        
        price_data = pd.DataFrame({
            'price_normalized_minmax': np.random.uniform(0.3, 1.0, 168),
            'price_uah_original': np.random.uniform(100, 500, 168),
        }, index=dates)
        
        print("✓ Test data created")
        
        # Train
        config = get_config()
        initial_version = config.get_current_version()
        
        print(f"✓ Initial version: {initial_version}")
        print("Training model (20 episodes)...")
        
        trainer = EnhancedRLTrainer(weather_data, price_data, config=config, verbose=False)
        
        progress_updates = []
        def progress_cb(pct):
            progress_updates.append(pct)
        
        result = trainer.train(episodes=20, learning_rate=3e-4, progress_callback=progress_cb)
        
        print(f"✓ Training complete")
        print(f"  New version: {result['version']}")
        print(f"  Episodes: {result['episodes']}")
        print(f"  Avg reward: {result['avg_reward']:.2f}")
        print(f"  Best reward: {result['best_reward']:.2f}")
        print(f"  Training time: {result['training_time_seconds']:.1f}s")
        
        # Verify version incremented
        new_version = config.get_current_version()
        if new_version != initial_version:
            print(f"✓ Version incremented: {initial_version} → {new_version}")
        else:
            print(f"✗ Version NOT incremented")
            return False
        
        return True
    except Exception as e:
        print(f"✗ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_data_quality():
    """Test 4: Data Quality Verification"""
    print_section("TEST 4: DATA QUALITY VERIFICATION")
    
    try:
        from src.solar_data import get_solar_fetcher
        from src.enhanced_config import get_config
        
        # Solar data validation
        fetcher = get_solar_fetcher()
        current = fetcher.get_current_solar_irradiance()
        
        assert 'irradiance_w_m2' in current, "Missing irradiance"
        assert 'cloudcover_percent' in current, "Missing cloud cover"
        assert isinstance(current['irradiance_w_m2'], (int, float)), "Invalid irradiance type"
        assert 0 <= current['cloudcover_percent'] <= 100, "Invalid cloud cover range"
        print("✓ Solar data format valid")
        
        # Config validation
        config = get_config()
        battery_cfg = config.get_battery_config()
        assert battery_cfg['capacity_kwh'] > 0, "Invalid battery capacity"
        assert 0 < battery_cfg['min_soc'] < 1, "Invalid min SOC"
        print("✓ Config data valid")
        
        # Version history validation
        history = config.get_version_history()
        if history:
            for ver in history:
                assert ver.episodes > 0, f"Invalid episodes in {ver.version}"
                assert ver.training_time_seconds > 0, f"Invalid training time in {ver.version}"
                print(f"✓ v{ver.version} metrics valid")
        
        return True
    except Exception as e:
        print(f"✗ FAILED: {str(e)}")
        return False

def test_performance():
    """Test 5: Performance Verification"""
    print_section("TEST 5: PERFORMANCE VERIFICATION")
    
    try:
        import time
        
        # Test solar fetch speed
        from src.solar_data import get_solar_fetcher
        start = time.time()
        fetcher = get_solar_fetcher()
        current = fetcher.get_current_solar_irradiance()
        solar_time = time.time() - start
        
        print(f"✓ Solar fetch time: {solar_time:.3f}s", end="")
        if solar_time < 2.0:
            print(" ✓ PASS")
        else:
            print(" ⚠ SLOW")
        
        # Test config load time
        from src.enhanced_config import get_config
        start = time.time()
        config = get_config()
        config_time = time.time() - start
        
        print(f"✓ Config load time: {config_time:.3f}s", end="")
        if config_time < 0.5:
            print(" ✓ PASS")
        else:
            print(" ⚠ SLOW")
        
        # Test version history fetch
        start = time.time()
        history = config.get_version_history()
        history_time = time.time() - start
        
        print(f"✓ Version history fetch: {history_time:.3f}s", end="")
        if history_time < 0.5:
            print(" ✓ PASS")
        else:
            print(" ⚠ SLOW")
        
        return True
    except Exception as e:
        print(f"✗ FAILED: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("\n" + "█"*70)
    print("█" + " "*68 + "█")
    print("█  SMART ENERGY AI SYSTEM - END-TO-END TEST SUITE".ljust(69) + "█")
    print("█" + " "*68 + "█")
    print("█"*70)
    
    start_time = time.time()
    
    tests = [
        ("Solar Data Module", test_solar_module),
        ("Version Tracking", test_version_tracking),
        ("RL Model Training", test_rl_training),
        ("Data Quality", test_data_quality),
        ("Performance", test_performance),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n✗ EXCEPTION in {test_name}: {str(e)}")
            results[test_name] = False
    
    # Summary
    total_time = time.time() - start_time
    
    print_section("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{'─'*70}")
    print(f"Results: {passed}/{total} tests passed")
    print(f"Total time: {total_time:.1f}s")
    print(f"{'─'*70}\n")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! System is production-ready.")
        return True
    else:
        print(f"⚠️ {total - passed} test(s) failed. Review above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

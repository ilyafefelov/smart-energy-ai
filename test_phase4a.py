"""Test script for Phase 4A: Library upgrades verification.

This script tests that:
1. Polars migration is working correctly
2. Pydantic configuration models validate properly  
3. Tenacity retry logic is functional
4. New libraries are properly installed

Run: python test_phase4a.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import polars as pl
import pydantic
import tenacity
import duckdb
from datetime import datetime

from energy_ml.config_models import (
    BatteryConfig, LoadProfileConfig, UserProfile,
    GenerationConfig, UkraineTariffConfig
)

def test_polars_basic():
    """Test basic polars functionality."""
    print("🧪 Testing Polars...")
    
    df = pl.DataFrame({
        'timestamp': [datetime.now()],
        'temperature': [15.5],
        'humidity': [65.0]
    })
    
    assert len(df) == 1
    assert df['temperature'].item(0) == 15.5
    print("✅ Polars working correctly")

def test_pydantic_models():
    """Test Pydantic configuration models."""
    print("🧪 Testing Pydantic Models...")
    
    # Test Battery Configuration
    battery_config = BatteryConfig(
        type='LFP',
        capacity_kwh=50.0,
        max_charge_rate_kw=10.0,
        max_discharge_rate_kw=10.0
    )
    assert battery_config.type == 'LFP'
    assert battery_config.degradation_cost_per_cycle == 1.35  # LFP default
    assert battery_config.cycles_to_eol == 8000  # LFP default
    
    # Test Load Profile
    load_profile = LoadProfileConfig.create_standard_work_profile(peak_load_kw=25.0)
    assert load_profile.profile_type == 'standard'
    assert load_profile.hourly_coefficients[12] == 1.0  # 12 PM (work hours)
    assert load_profile.hourly_coefficients[2] == 0.1   # 2 AM (off hours)
    
    # Test Complete User Profile
    user_profile = UserProfile(
        user_id="test_user_001",
        profile_name="Test Profile",
        battery=battery_config,
        load_profile=load_profile,
        generation=GenerationConfig(solar_capacity_kw=30.0),
        tariff=UkraineTariffConfig()
    )
    assert user_profile.user_id == "test_user_001"
    assert user_profile.battery.type == 'LFP'
    
    print("✅ Pydantic models working correctly")

def test_tenacity_retry():
    """Test Tenacity retry functionality."""
    print("🧪 Testing Tenacity Retry Logic...")
    
    attempt_count = 0
    
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_fixed(0.1)  # Short wait for testing
    )
    def flaky_function():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 2:
            raise Exception("Simulated failure")
        return "Success!"
    
    result = flaky_function()
    assert result == "Success!"
    assert attempt_count == 2  # Should have failed once, then succeeded
    
    print("✅ Tenacity retry working correctly")

def test_duckdb_analytics():
    """Test DuckDB analytics functionality."""
    print("🧪 Testing DuckDB Analytics...")
    
    # Create test data
    df = pl.DataFrame({
        'hour': list(range(24)),
        'price': [10.0 + i * 0.5 for i in range(24)],
        'consumption': [5.0 + i * 0.2 for i in range(24)]
    })
    
    # Test DuckDB query on Polars DataFrame
    conn = duckdb.connect()
    result = conn.execute("""
        SELECT 
            avg(price) as avg_price,
            max(consumption) as max_consumption,
            count(*) as record_count
        FROM df
    """).fetchone()
    
    avg_price, max_consumption, record_count = result
    assert record_count == 24
    assert avg_price > 10.0
    assert max_consumption > 5.0
    
    print("✅ DuckDB analytics working correctly")

def test_library_versions():
    """Test that all required libraries are installed with correct versions."""
    print("🧪 Testing Library Versions...")
    
    import polars
    import pydantic 
    import tenacity
    import duckdb
    import optuna
    from packaging import version
    
    print(f"  Polars: {polars.__version__}")
    print(f"  Pydantic: {pydantic.__version__}")
    print(f"  Tenacity: {getattr(tenacity, '__version__', 'installed')}")
    print(f"  DuckDB: {duckdb.__version__}")  
    print(f"  Optuna: {optuna.__version__}")
    
    # Check minimum versions using proper version comparison
    assert version.parse(polars.__version__) >= version.parse("0.20.0"), \
        f"Polars version too low: {polars.__version__}"
    assert version.parse(pydantic.__version__) >= version.parse("2.6.0"), \
        f"Pydantic version too low: {pydantic.__version__}"
    assert version.parse(optuna.__version__) >= version.parse("4.7.0"), \
        f"Optuna version too low: {optuna.__version__}"
    
    print("✅ All library versions meet requirements")

def main():
    """Run all Phase 4A tests."""
    print("🚀 PHASE 4A VERIFICATION TESTS")
    print("=" * 50)
    
    try:
        test_library_versions()
        print()
        
        test_polars_basic()
        print()
        
        test_pydantic_models()
        print()
        
        test_tenacity_retry()
        print()
        
        test_duckdb_analytics()
        print()
        
        print("🎉 ALL PHASE 4A TESTS PASSED!")
        print("✅ Library upgrades successful")
        print("✅ Polars migration ready")
        print("✅ Pydantic models functional") 
        print("✅ Tenacity retry working")
        print("✅ DuckDB analytics ready")
        
        return 0
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
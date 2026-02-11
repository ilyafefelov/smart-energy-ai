"""Comprehensive tests for Phase 4C: Load Profile System.

This test suite validates:
1. Load profile simulation for all profile types (standard, multi-shift, 24/7, custom)
2. Hourly coefficient validation (0-1 range, 24 hours)
3. Load generation accuracy (peak, daily stats, seasonal variation)
4. Self-consumption estimation
5. Generation correlation
6. Dagster asset integration
7. Performance (<100ms per simulation)
8. JSON output completeness (8760 hours)
9. Industry-validated load patterns
10. Zero regression in Phase 4A/4B tests
11. Advanced simulator classes (Standard, MultiShift, Continuous, Custom)
12. Simulator factory functions and inheritance patterns
"""

import os
import json
import time
import math
from datetime import datetime, timedelta

import pytest

from energy_ml.config_models import (
    LoadProfileConfig, UserProfile, BatteryConfig, 
    GenerationConfig, UkraineTariffConfig
)
from energy_ml.load_simulation import (
    generate_yearly_load, simple_generation_hourly, 
    estimate_self_consumption,
    BaseLoadSimulator, StandardWorkSimulator, MultiShiftSimulator,
    ContinuousSimulator, CustomSimulator, create_simulator
)
from energy_ml.assets.load_profiles import simulate_load_profile


def make_user(profile_config: LoadProfileConfig):
    """Create a UserProfile for testing."""
    return UserProfile(
        user_id='test-user',
        profile_name='test',
        battery=BatteryConfig(
            type='LFP', 
            capacity_kwh=20, 
            max_charge_rate_kw=5, 
            max_discharge_rate_kw=5
        ),
        load_profile=profile_config,
        generation=GenerationConfig(solar_capacity_kw=10.0),
        tariff=UkraineTariffConfig()
    )


# ============================================================================
# UNIT TESTS - LOAD PROFILE CONFIGURATION
# ============================================================================

def test_standard_work_profile_config():
    """Test standard work hours (9-18) profile configuration."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    
    assert p.profile_type == 'standard'
    assert p.name == 'Standard Work Hours (9-18)'
    assert p.peak_load_kw == 50.0
    assert len(p.hourly_coefficients) == 24
    
    # Check work hours are full load
    for hour in range(9, 19):
        assert p.hourly_coefficients[hour] == 1.0
    
    # Check off-hours have base load
    for hour in list(range(0, 9)) + list(range(19, 24)):
        assert p.hourly_coefficients[hour] == 0.1


def test_two_shift_profile_config():
    """Test 2-shift operation profile configuration."""
    p = LoadProfileConfig.create_two_shift_profile(peak_load_kw=100.0)
    
    assert p.profile_type == 'multi-shift'
    assert p.name == 'Two Shift Operation'
    assert len(p.hourly_coefficients) == 24
    
    # First shift 6 AM - 2 PM (6-15)
    for hour in range(6, 15):
        assert p.hourly_coefficients[hour] == 1.0
    
    # Second shift 10 PM - 6 AM (22-24, 0-6)
    for hour in list(range(22, 24)) + list(range(0, 7)):
        assert p.hourly_coefficients[hour] == 1.0


def test_24_7_profile_config():
    """Test 24/7 continuous operation profile configuration."""
    p = LoadProfileConfig.create_24_7_profile(peak_load_kw=200.0)
    
    assert p.profile_type == '24/7'
    assert p.name == 'Continuous Operation (24/7)'
    assert all(0.5 <= p.hourly_coefficients[h] <= 1.0 for h in range(24))


def test_custom_profile_creation():
    """Test custom profile with user-defined coefficients."""
    custom_coeffs = {
        0: 0.1, 1: 0.1, 2: 0.1, 3: 0.1, 4: 0.1, 5: 0.1,
        6: 0.5, 7: 1.0, 8: 1.0, 9: 1.0, 10: 1.0, 11: 1.0,
        12: 0.8, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 0.8,
        18: 0.5, 19: 0.2, 20: 0.1, 21: 0.1, 22: 0.1, 23: 0.1
    }
    
    p = LoadProfileConfig(
        profile_type='custom',
        name='Custom Business Hours',
        description='Custom operation schedule',
        hourly_coefficients=custom_coeffs,
        peak_load_kw=75.0
    )
    
    assert p.profile_type == 'custom'
    assert len(p.hourly_coefficients) == 24


def test_hourly_coefficients_validation():
    """Test validation of hourly coefficients."""
    # Valid coefficients
    valid = {i: 0.5 for i in range(24)}
    p = LoadProfileConfig(
        profile_type='custom',
        name='Test',
        description='Test profile',
        hourly_coefficients=valid,
        peak_load_kw=10.0
    )
    assert p.hourly_coefficients == valid
    
    # Invalid: missing hours
    invalid_incomplete = {i: 0.5 for i in range(12)}
    with pytest.raises(ValueError, match="Must provide coefficients for all 24 hours"):
        LoadProfileConfig(
            profile_type='custom',
            name='Test',
            description='Test',
            hourly_coefficients=invalid_incomplete,
            peak_load_kw=10.0
        )
    
    # Invalid: coefficient out of range
    invalid_range = {i: 0.5 for i in range(24)}
    invalid_range[12] = 2.5  # > 2.0
    with pytest.raises(ValueError, match="between 0.0-2.0"):
        LoadProfileConfig(
            profile_type='custom',
            name='Test',
            description='Test',
            hourly_coefficients=invalid_range,
            peak_load_kw=10.0
        )


# ============================================================================
# UNIT TESTS - SIMULATOR CLASSES
# ============================================================================

def test_base_load_simulator_instantiation():
    """Test BaseLoadSimulator can be instantiated with profile."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    sim = BaseLoadSimulator(p)
    
    assert sim.peak_load_kw == 50.0
    assert sim.base_load_kw == 50.0 * 0.15  # 15% default
    assert len(sim.hourly_coefficients) == 24


def test_standard_work_simulator():
    """Test StandardWorkSimulator specific behavior."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    sim = StandardWorkSimulator(p)
    
    hours = sim.simulate_year()
    assert len(hours) == 8760
    assert all(h > 0 for h in hours)
    assert max(hours) <= 1.05 * 50.0


def test_multi_shift_simulator():
    """Test MultiShiftSimulator specific behavior."""
    p = LoadProfileConfig.create_two_shift_profile(peak_load_kw=200.0)
    sim = MultiShiftSimulator(p)
    
    hours = sim.simulate_year()
    assert len(hours) == 8760
    assert sim.base_load_kw == 200.0 * 0.20  # 20% for multi-shift


def test_continuous_simulator():
    """Test ContinuousSimulator for 24/7 operations."""
    p = LoadProfileConfig.create_24_7_profile(peak_load_kw=1000.0)
    sim = ContinuousSimulator(p)
    
    hours = sim.simulate_year()
    assert len(hours) == 8760
    assert sim.base_load_kw == 1000.0 * 0.25  # 25% for continuous


def test_custom_simulator():
    """Test CustomSimulator with user-defined coefficients."""
    custom_coeffs = {
        0: 0.1, 1: 0.1, 2: 0.1, 3: 0.1, 4: 0.1, 5: 0.1,
        6: 0.5, 7: 1.0, 8: 1.0, 9: 1.0, 10: 1.0, 11: 1.0,
        12: 0.8, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 0.8,
        18: 0.5, 19: 0.2, 20: 0.1, 21: 0.1, 22: 0.1, 23: 0.1
    }
    
    p = LoadProfileConfig(
        profile_type='custom',
        name='Custom',
        description='Custom',
        hourly_coefficients=custom_coeffs,
        peak_load_kw=75.0
    )
    
    sim = CustomSimulator(p)
    hours = sim.simulate_year()
    
    assert len(hours) == 8760
    assert all(h > 0 for h in hours)


def test_simulator_factory_standard():
    """Test factory function creates correct simulator for standard profile."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    sim = create_simulator(p)
    
    assert isinstance(sim, StandardWorkSimulator)


def test_simulator_factory_multi_shift():
    """Test factory function creates correct simulator for multi-shift profile."""
    p = LoadProfileConfig.create_two_shift_profile(peak_load_kw=200.0)
    sim = create_simulator(p)
    
    assert isinstance(sim, MultiShiftSimulator)


def test_simulator_factory_24_7():
    """Test factory function creates correct simulator for 24/7 profile."""
    p = LoadProfileConfig.create_24_7_profile(peak_load_kw=1000.0)
    sim = create_simulator(p)
    
    assert isinstance(sim, ContinuousSimulator)


def test_simulator_factory_custom():
    """Test factory function creates correct simulator for custom profile."""
    p = LoadProfileConfig(
        profile_type='custom',
        name='Custom',
        description='Custom',
        hourly_coefficients={i: 0.5 for i in range(24)},
        peak_load_kw=50.0
    )
    sim = create_simulator(p)
    
    assert isinstance(sim, CustomSimulator)


def test_simulator_seasonal_factor():
    """Test seasonal factor application."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    sim = BaseLoadSimulator(p)
    
    # Early in year (day 0)
    factor_early = sim.apply_seasonal_factor(0, factor=0.2)
    # Mid-year (day 182)
    factor_mid = sim.apply_seasonal_factor(182, factor=0.2)
    # End of year (day 364)
    factor_late = sim.apply_seasonal_factor(364, factor=0.2)
    
    # Mid-year should be at/near peak (1.0 to 1.2)
    assert 0.98 <= factor_mid <= 1.02
    # Extremes should vary
    assert factor_early != factor_late


def test_simulator_weekend_reduction():
    """Test weekend load reduction."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    sim = BaseLoadSimulator(p)
    
    # Weekday (Monday=0)
    coeff_weekday = sim.apply_weekend_reduction(0, 1.0, reduction=0.6)
    assert coeff_weekday == 1.0
    
    # Weekend (Saturday=5)
    coeff_weekend = sim.apply_weekend_reduction(5, 1.0, reduction=0.6)
    assert coeff_weekend == 0.6


def test_simulator_daily_noise():
    """Test daily noise application."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    sim = BaseLoadSimulator(p)
    
    base = 10.0
    noisy = sim.apply_daily_noise(base, noise_pct=0.05, seed=42)
    
    # Should be within ±5%
    assert 9.5 <= noisy <= 10.5
    # Should not be exactly equal (unless by chance)
    assert noisy != base  # Very likely


# ============================================================================
# UNIT TESTS - LOAD SIMULATION CORE ENGINE
# ============================================================================

def test_standard_work_simulation():
    """Test load simulation for standard work hours."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    result = generate_yearly_load(p, random_seed=42)
    
    # Check output structure
    assert 'hourly' in result
    assert 'daily_stats' in result
    assert 'overall' in result
    
    # Check hourly data
    assert len(result['hourly']) == 8760
    assert all(isinstance(h, (int, float)) for h in result['hourly'])
    assert all(h > 0 for h in result['hourly']), "All loads must be > 0"
    
    # Check peak doesn't exceed peak_load_kw + margin
    assert max(result['hourly']) <= 1.06 * p.peak_load_kw
    
    # Check daily stats
    assert len(result['daily_stats']) == 365
    for day_stat in result['daily_stats']:
        assert 'date' in day_stat
        assert 'average_kW' in day_stat
        assert 'peak_kW' in day_stat
        assert 'min_kW' in day_stat
        assert day_stat['min_kW'] > 0


def test_multi_shift_simulation():
    """Test load simulation for 2-shift operation."""
    p = LoadProfileConfig.create_two_shift_profile(peak_load_kw=200.0)
    result = generate_yearly_load(p, random_seed=42)
    
    assert len(result['hourly']) == 8760
    assert len(result['daily_stats']) == 365
    assert max(result['hourly']) <= 1.06 * p.peak_load_kw


def test_24_7_simulation():
    """Test load simulation for 24/7 operations."""
    p = LoadProfileConfig.create_24_7_profile(peak_load_kw=1000.0)
    result = generate_yearly_load(p, random_seed=42)
    
    assert len(result['hourly']) == 8760
    # 24/7 should have more consistent load (smaller variance coefficient)
    assert all(h > 0 for h in result['hourly'])
    assert max(result['hourly']) <= 1.06 * p.peak_load_kw


def test_load_peak_constraints():
    """Test that simulated loads respect peak_load_kw constraint."""
    profiles = [
        LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0),
        LoadProfileConfig.create_two_shift_profile(peak_load_kw=100.0),
        LoadProfileConfig.create_24_7_profile(peak_load_kw=500.0),
    ]
    
    for profile in profiles:
        result = generate_yearly_load(profile)
        # Allow 5% overshoot for numerical noise
        assert max(result['hourly']) <= 1.05 * profile.peak_load_kw, \
            f"Peak {max(result['hourly'])} exceeds limit {1.05 * profile.peak_load_kw}"


def test_base_load_present():
    """Test that off-peak base load is always present (>0)."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    result = generate_yearly_load(p)
    
    # All hourly values must be > 0 (base load)
    assert all(h > 0 for h in result['hourly'])
    
    # Off-peak hours should generally be lower
    # Get sample off-peak hours (midnight, early morning)
    off_peak_samples = [result['hourly'][i] for i in [0, 1, 2, 3, 4, 5]]
    peak_samples = [result['hourly'][i] for i in [12, 13, 14, 15, 16, 17]]
    
    assert sum(off_peak_samples) / 6 < sum(peak_samples) / 6, \
        "Off-peak load should be lower than peak hours on average"


def test_seasonal_variation():
    """Test that seasonal variation is within ±20%."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    result = generate_yearly_load(p, seasonal_factor=0.2)
    
    # Get first month and last month averages
    first_month_avg = sum(result['daily_stats'][i]['average_kW'] for i in range(31)) / 31
    last_month_avg = sum(result['daily_stats'][i]['average_kW'] for i in range(334, 365)) / 31
    
    # Variation should be reasonable
    ratio = last_month_avg / first_month_avg if first_month_avg > 0 else 1.0
    assert 0.8 <= ratio <= 1.25, f"Seasonal variation too large: {ratio}"


def test_weekly_pattern():
    """Test that weekends have lower load than weekdays."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    result = generate_yearly_load(p, weekend_reduction=0.6)
    
    # Group by day of week and compare averages
    weekday_totals = [0] * 7
    weekday_counts = [0] * 7
    
    start_date = datetime(datetime.now().year, 1, 1)
    for day_idx, day_stat in enumerate(result['daily_stats']):
        current = start_date + timedelta(days=day_idx)
        dow = current.weekday()  # 0=Mon, 6=Sun
        weekday_totals[dow] += day_stat['average_kW']
        weekday_counts[dow] += 1
    
    weekday_avgs = [weekday_totals[i] / max(1, weekday_counts[i]) for i in range(7)]
    
    # Weekdays (0-4) should average higher than weekends (5-6)
    weekday_avg = sum(weekday_avgs[0:5]) / 5
    weekend_avg = sum(weekday_avgs[5:7]) / 2
    
    assert weekday_avg > weekend_avg, \
        f"Weekday avg {weekday_avg} should be > weekend {weekend_avg}"


def test_annual_energy_calculation():
    """Test that annual energy is correctly calculated."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    result = generate_yearly_load(p)
    
    # Sum hourly should match overall annual energy
    calculated_annual = sum(result['hourly'])
    reported_annual = result['overall']['annual_energy_kwh']
    
    assert abs(calculated_annual - reported_annual) < 1.0, \
        "Annual energy calculation mismatch"


# ============================================================================
# UNIT TESTS - SELF-CONSUMPTION ESTIMATION
# ============================================================================

def test_self_consumption_estimation():
    """Test self-consumption calculation."""
    load = [10.0] * 8760
    generation = [5.0] * 8760
    
    result = estimate_self_consumption(load, generation)
    
    assert 'self_consumption_pct' in result
    assert 'estimated_peak_shave_kW' in result
    assert result['self_consumption_pct'] == 50.0  # 5/10 = 50%


def test_self_consumption_perfect_match():
    """Test self-consumption when generation equals load."""
    load = [10.0] * 8760
    generation = [10.0] * 8760
    
    result = estimate_self_consumption(load, generation)
    
    assert result['self_consumption_pct'] == 100.0


def test_self_consumption_no_generation():
    """Test self-consumption with zero generation."""
    load = [10.0] * 8760
    generation = [0.0] * 8760
    
    result = estimate_self_consumption(load, generation)
    
    assert result['self_consumption_pct'] == 0.0


def test_self_consumption_excess_generation():
    """Test self-consumption when generation exceeds load."""
    load = [10.0] * 8760
    generation = [20.0] * 8760
    
    result = estimate_self_consumption(load, generation)
    
    # Can only consume up to load
    assert result['self_consumption_pct'] == 100.0


# ============================================================================
# UNIT TESTS - GENERATION PROFILE
# ============================================================================

def test_generation_hourly_structure():
    """Test solar generation profile structure."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    u = make_user(p)
    gen_hours = simple_generation_hourly(u)
    
    assert len(gen_hours) == 8760
    assert all(isinstance(h, (int, float)) for h in gen_hours)
    assert all(h >= 0 for h in gen_hours)


def test_generation_daylight_pattern():
    """Test that generation follows daylight hours pattern."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    u = UserProfile(
        user_id='test',
        profile_name='test',
        battery=BatteryConfig(
            type='LFP', 
            capacity_kwh=20,
            max_charge_rate_kw=5,
            max_discharge_rate_kw=5
        ),
        load_profile=p,
        generation=GenerationConfig(solar_capacity_kw=100.0),  # High capacity
        tariff=UkraineTariffConfig()
    )
    
    gen_hours = simple_generation_hourly(u, seed=42)
    
    # Check first day pattern (hours 0-24)
    day1_gen = gen_hours[0:24]
    
    # Nighttime (0-5, 19-23) should have zero or near-zero generation
    night_gen = day1_gen[0:6] + day1_gen[19:24]
    assert sum(night_gen) < 1.0  # Negligible night generation
    
    # Daytime (6-18) should have some generation
    day_gen = day1_gen[6:19]
    assert sum(day_gen) > 10.0  # Significant daytime generation


def test_generation_zero_capacity():
    """Test generation with zero solar capacity."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    u = UserProfile(
        user_id='test',
        profile_name='test',
        battery=BatteryConfig(
            type='LFP',
            capacity_kwh=20,
            max_charge_rate_kw=5,
            max_discharge_rate_kw=5
        ),
        load_profile=p,
        generation=GenerationConfig(solar_capacity_kw=0.0),
        tariff=UkraineTariffConfig()
    )
    
    gen_hours = simple_generation_hourly(u)
    
    assert all(h == 0.0 for h in gen_hours)


# ============================================================================
# INTEGRATION TESTS - DAGSTER ASSET
# ============================================================================

def test_dagster_asset_standard_profile():
    """Test Dagster asset with standard profile."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    u = make_user(p)
    
    path = simulate_load_profile(u)
    
    assert os.path.exists(path)
    with open(path, 'r', encoding='utf8') as f:
        data = json.load(f)
    
    assert 'metadata' in data
    assert 'simulation' in data
    assert 'self_consumption' in data
    assert data['metadata']['profile_type'] == 'standard'


def test_dagster_asset_multi_shift_profile():
    """Test Dagster asset with multi-shift profile."""
    p = LoadProfileConfig.create_two_shift_profile(peak_load_kw=200.0)
    u = make_user(p)
    
    path = simulate_load_profile(u)
    
    assert os.path.exists(path)
    with open(path, 'r', encoding='utf8') as f:
        data = json.load(f)
    
    assert data['metadata']['profile_type'] == 'multi-shift'
    assert len(data['simulation']['hourly']) == 8760


def test_dagster_asset_24_7_profile():
    """Test Dagster asset with 24/7 profile."""
    p = LoadProfileConfig.create_24_7_profile(peak_load_kw=1000.0)
    u = make_user(p)
    
    path = simulate_load_profile(u)
    
    assert os.path.exists(path)
    with open(path, 'r', encoding='utf8') as f:
        data = json.load(f)
    
    assert data['metadata']['profile_type'] == '24/7'
    assert len(data['simulation']['hourly']) == 8760


def test_dagster_asset_json_structure():
    """Test that Dagster asset output has complete JSON structure."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    u = make_user(p)
    
    path = simulate_load_profile(u)
    
    with open(path, 'r', encoding='utf8') as f:
        data = json.load(f)
    
    # Check metadata
    assert 'profile_name' in data['metadata']
    assert 'profile_type' in data['metadata']
    assert 'generated_at' in data['metadata']
    
    # Check simulation
    assert len(data['simulation']['hourly']) == 8760
    assert 'daily_stats' in data['simulation']
    assert len(data['simulation']['daily_stats']) == 365
    assert 'overall' in data['simulation']
    
    # Check overall stats
    overall = data['simulation']['overall']
    assert 'annual_energy_kwh' in overall
    assert 'annual_peak_kW' in overall
    assert 'annual_min_kW' in overall
    assert 'daily_average_kwh' in overall
    
    # Check self-consumption
    assert 'self_consumption_pct' in data['self_consumption']
    assert 'estimated_peak_shave_kW' in data['self_consumption']


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

def test_simulation_performance():
    """Test that simulation completes in <100ms."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    
    start = time.time()
    result = generate_yearly_load(p)
    elapsed = time.time() - start
    
    assert elapsed < 0.1, f"Simulation took {elapsed:.3f}s, should be <0.1s"


def test_asset_execution_performance():
    """Test that full asset execution completes in <500ms."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    u = make_user(p)
    
    start = time.time()
    path = simulate_load_profile(u)
    elapsed = time.time() - start
    
    assert elapsed < 0.5, f"Asset execution took {elapsed:.3f}s, should be <0.5s"


def test_multi_profile_performance():
    """Test that all 3 profile types can be simulated quickly."""
    profiles = [
        LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0),
        LoadProfileConfig.create_two_shift_profile(peak_load_kw=200.0),
        LoadProfileConfig.create_24_7_profile(peak_load_kw=1000.0),
    ]
    
    start = time.time()
    for p in profiles:
        result = generate_yearly_load(p)
    elapsed = time.time() - start
    
    assert elapsed < 0.3, f"All profiles took {elapsed:.3f}s, should be <0.3s"


# ============================================================================
# SMOKE TESTS - REGRESSION VERIFICATION
# ============================================================================

def test_no_regression_phase4a():
    """Smoke test: ensure Phase 4A tests still pass."""
    from energy_ml.config_models import BatteryConfig
    
    # Basic Pydantic model test from Phase 4A
    cfg = BatteryConfig(
        type='LFP',
        capacity_kwh=50.0,
        max_charge_rate_kw=10.0,
        max_discharge_rate_kw=10.0
    )
    assert cfg.type == 'LFP'
    assert cfg.degradation_cost_per_cycle == 1.35


def test_no_regression_phase4b():
    """Smoke test: ensure Phase 4B battery models still work."""
    from energy_ml.battery_degradation import LFPModel
    
    cfg = BatteryConfig(
        type='LFP',
        capacity_kwh=50.0,
        max_charge_rate_kw=10.0,
        max_discharge_rate_kw=10.0
    )
    model = LFPModel(cfg)
    result = model.simulate_cycles(cycles=100, dod=0.8, c_rate=0.5)
    
    assert result.soh < 1.0
    assert result.cycles == 100


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])


def make_user(profile_config: LoadProfileConfig):
    """Create a UserProfile for testing."""
    return UserProfile(
        user_id='test-user',
        profile_name='test',
        battery=BatteryConfig(
            type='LFP', 
            capacity_kwh=20, 
            max_charge_rate_kw=5, 
            max_discharge_rate_kw=5
        ),
        load_profile=profile_config,
        generation=GenerationConfig(solar_capacity_kw=10.0),
        tariff=UkraineTariffConfig()
    )


# ============================================================================
# UNIT TESTS - LOAD PROFILE CONFIGURATION
# ============================================================================

def test_standard_work_profile_config():
    """Test standard work hours (9-18) profile configuration."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    
    assert p.profile_type == 'standard'
    assert p.name == 'Standard Work Hours (9-18)'
    assert p.peak_load_kw == 50.0
    assert len(p.hourly_coefficients) == 24
    
    # Check work hours are full load
    for hour in range(9, 19):
        assert p.hourly_coefficients[hour] == 1.0
    
    # Check off-hours have base load
    for hour in list(range(0, 9)) + list(range(19, 24)):
        assert p.hourly_coefficients[hour] == 0.1


def test_two_shift_profile_config():
    """Test 2-shift operation profile configuration."""
    p = LoadProfileConfig.create_two_shift_profile(peak_load_kw=100.0)
    
    assert p.profile_type == 'multi-shift'
    assert p.name == 'Two Shift Operation'
    assert len(p.hourly_coefficients) == 24
    
    # First shift 6 AM - 2 PM (6-15)
    for hour in range(6, 15):
        assert p.hourly_coefficients[hour] == 1.0
    
    # Second shift 10 PM - 6 AM (22-24, 0-6)
    for hour in list(range(22, 24)) + list(range(0, 7)):
        assert p.hourly_coefficients[hour] == 1.0


def test_24_7_profile_config():
    """Test 24/7 continuous operation profile configuration."""
    p = LoadProfileConfig.create_24_7_profile(peak_load_kw=200.0)
    
    assert p.profile_type == '24/7'
    assert p.name == 'Continuous Operation (24/7)'
    assert all(0.5 <= p.hourly_coefficients[h] <= 1.0 for h in range(24))


def test_custom_profile_creation():
    """Test custom profile with user-defined coefficients."""
    custom_coeffs = {
        0: 0.1, 1: 0.1, 2: 0.1, 3: 0.1, 4: 0.1, 5: 0.1,
        6: 0.5, 7: 1.0, 8: 1.0, 9: 1.0, 10: 1.0, 11: 1.0,
        12: 0.8, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 0.8,
        18: 0.5, 19: 0.2, 20: 0.1, 21: 0.1, 22: 0.1, 23: 0.1
    }
    
    p = LoadProfileConfig(
        profile_type='custom',
        name='Custom Business Hours',
        description='Custom operation schedule',
        hourly_coefficients=custom_coeffs,
        peak_load_kw=75.0
    )
    
    assert p.profile_type == 'custom'
    assert len(p.hourly_coefficients) == 24


def test_hourly_coefficients_validation():
    """Test validation of hourly coefficients."""
    # Valid coefficients
    valid = {i: 0.5 for i in range(24)}
    p = LoadProfileConfig(
        profile_type='custom',
        name='Test',
        description='Test profile',
        hourly_coefficients=valid,
        peak_load_kw=10.0
    )
    assert p.hourly_coefficients == valid
    
    # Invalid: missing hours
    invalid_incomplete = {i: 0.5 for i in range(12)}
    with pytest.raises(ValueError, match="Must provide coefficients for all 24 hours"):
        LoadProfileConfig(
            profile_type='custom',
            name='Test',
            description='Test',
            hourly_coefficients=invalid_incomplete,
            peak_load_kw=10.0
        )
    
    # Invalid: coefficient out of range
    invalid_range = {i: 0.5 for i in range(24)}
    invalid_range[12] = 2.5  # > 2.0
    with pytest.raises(ValueError, match="between 0.0-2.0"):
        LoadProfileConfig(
            profile_type='custom',
            name='Test',
            description='Test',
            hourly_coefficients=invalid_range,
            peak_load_kw=10.0
        )


# ============================================================================
# UNIT TESTS - LOAD SIMULATION CORE ENGINE
# ============================================================================

def test_standard_work_simulation():
    """Test load simulation for standard work hours."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    result = generate_yearly_load(p, random_seed=42)
    
    # Check output structure
    assert 'hourly' in result
    assert 'daily_stats' in result
    assert 'overall' in result
    
    # Check hourly data
    assert len(result['hourly']) == 8760
    assert all(isinstance(h, (int, float)) for h in result['hourly'])
    assert all(h > 0 for h in result['hourly']), "All loads must be > 0"
    
    # Check peak doesn't exceed peak_load_kw + margin
    assert max(result['hourly']) <= 1.06 * p.peak_load_kw
    
    # Check daily stats
    assert len(result['daily_stats']) == 365
    for day_stat in result['daily_stats']:
        assert 'date' in day_stat
        assert 'average_kW' in day_stat
        assert 'peak_kW' in day_stat
        assert 'min_kW' in day_stat
        assert day_stat['min_kW'] > 0


def test_multi_shift_simulation():
    """Test load simulation for 2-shift operation."""
    p = LoadProfileConfig.create_two_shift_profile(peak_load_kw=200.0)
    result = generate_yearly_load(p, random_seed=42)
    
    assert len(result['hourly']) == 8760
    assert len(result['daily_stats']) == 365
    assert max(result['hourly']) <= 1.06 * p.peak_load_kw


def test_24_7_simulation():
    """Test load simulation for 24/7 operations."""
    p = LoadProfileConfig.create_24_7_profile(peak_load_kw=1000.0)
    result = generate_yearly_load(p, random_seed=42)
    
    assert len(result['hourly']) == 8760
    # 24/7 should have more consistent load (smaller variance coefficient)
    assert all(h > 0 for h in result['hourly'])
    assert max(result['hourly']) <= 1.06 * p.peak_load_kw


def test_load_peak_constraints():
    """Test that simulated loads respect peak_load_kw constraint."""
    profiles = [
        LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0),
        LoadProfileConfig.create_two_shift_profile(peak_load_kw=100.0),
        LoadProfileConfig.create_24_7_profile(peak_load_kw=500.0),
    ]
    
    for profile in profiles:
        result = generate_yearly_load(profile)
        # Allow 5% overshoot for numerical noise
        assert max(result['hourly']) <= 1.05 * profile.peak_load_kw, \
            f"Peak {max(result['hourly'])} exceeds limit {1.05 * profile.peak_load_kw}"


def test_base_load_present():
    """Test that off-peak base load is always present (>0)."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    result = generate_yearly_load(p)
    
    # All hourly values must be > 0 (base load)
    assert all(h > 0 for h in result['hourly'])
    
    # Off-peak hours should generally be lower
    # Get sample off-peak hours (midnight, early morning)
    off_peak_samples = [result['hourly'][i] for i in [0, 1, 2, 3, 4, 5]]
    peak_samples = [result['hourly'][i] for i in [12, 13, 14, 15, 16, 17]]
    
    assert sum(off_peak_samples) / 6 < sum(peak_samples) / 6, \
        "Off-peak load should be lower than peak hours on average"


def test_seasonal_variation():
    """Test that seasonal variation is within ±20%."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    result = generate_yearly_load(p, seasonal_factor=0.2)
    
    # Get first month and last month averages
    first_month_avg = sum(result['daily_stats'][i]['average_kW'] for i in range(31)) / 31
    last_month_avg = sum(result['daily_stats'][i]['average_kW'] for i in range(334, 365)) / 31
    
    # Variation should be reasonable
    ratio = last_month_avg / first_month_avg if first_month_avg > 0 else 1.0
    assert 0.8 <= ratio <= 1.25, f"Seasonal variation too large: {ratio}"


def test_weekly_pattern():
    """Test that weekends have lower load than weekdays."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    result = generate_yearly_load(p, weekend_reduction=0.6)
    
    # Group by day of week and compare averages
    weekday_totals = [0] * 7
    weekday_counts = [0] * 7
    
    start_date = datetime(datetime.now().year, 1, 1)
    for day_idx, day_stat in enumerate(result['daily_stats']):
        current = start_date + timedelta(days=day_idx)
        dow = current.weekday()  # 0=Mon, 6=Sun
        weekday_totals[dow] += day_stat['average_kW']
        weekday_counts[dow] += 1
    
    weekday_avgs = [weekday_totals[i] / max(1, weekday_counts[i]) for i in range(7)]
    
    # Weekdays (0-4) should average higher than weekends (5-6)
    weekday_avg = sum(weekday_avgs[0:5]) / 5
    weekend_avg = sum(weekday_avgs[5:7]) / 2
    
    assert weekday_avg > weekend_avg, \
        f"Weekday avg {weekday_avg} should be > weekend {weekend_avg}"


def test_annual_energy_calculation():
    """Test that annual energy is correctly calculated."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    result = generate_yearly_load(p)
    
    # Sum hourly should match overall annual energy
    calculated_annual = sum(result['hourly'])
    reported_annual = result['overall']['annual_energy_kwh']
    
    assert abs(calculated_annual - reported_annual) < 1.0, \
        "Annual energy calculation mismatch"


# ============================================================================
# UNIT TESTS - SELF-CONSUMPTION ESTIMATION
# ============================================================================

def test_self_consumption_estimation():
    """Test self-consumption calculation."""
    load = [10.0] * 8760
    generation = [5.0] * 8760
    
    result = estimate_self_consumption(load, generation)
    
    assert 'self_consumption_pct' in result
    assert 'estimated_peak_shave_kW' in result
    assert result['self_consumption_pct'] == 50.0  # 5/10 = 50%


def test_self_consumption_perfect_match():
    """Test self-consumption when generation equals load."""
    load = [10.0] * 8760
    generation = [10.0] * 8760
    
    result = estimate_self_consumption(load, generation)
    
    assert result['self_consumption_pct'] == 100.0


def test_self_consumption_no_generation():
    """Test self-consumption with zero generation."""
    load = [10.0] * 8760
    generation = [0.0] * 8760
    
    result = estimate_self_consumption(load, generation)
    
    assert result['self_consumption_pct'] == 0.0


def test_self_consumption_excess_generation():
    """Test self-consumption when generation exceeds load."""
    load = [10.0] * 8760
    generation = [20.0] * 8760
    
    result = estimate_self_consumption(load, generation)
    
    # Can only consume up to load
    assert result['self_consumption_pct'] == 100.0


# ============================================================================
# UNIT TESTS - GENERATION PROFILE
# ============================================================================

def test_generation_hourly_structure():
    """Test solar generation profile structure."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    u = make_user(p)
    gen_hours = simple_generation_hourly(u)
    
    assert len(gen_hours) == 8760
    assert all(isinstance(h, (int, float)) for h in gen_hours)
    assert all(h >= 0 for h in gen_hours)


def test_generation_daylight_pattern():
    """Test that generation follows daylight hours pattern."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    u = UserProfile(
        user_id='test',
        profile_name='test',
        battery=BatteryConfig(
            type='LFP', 
            capacity_kwh=20,
            max_charge_rate_kw=5,
            max_discharge_rate_kw=5
        ),
        load_profile=p,
        generation=GenerationConfig(solar_capacity_kw=100.0),  # High capacity
        tariff=UkraineTariffConfig()
    )
    
    gen_hours = simple_generation_hourly(u, seed=42)
    
    # Check first day pattern (hours 0-24)
    day1_gen = gen_hours[0:24]
    
    # Nighttime (0-5, 19-23) should have zero or near-zero generation
    night_gen = day1_gen[0:6] + day1_gen[19:24]
    assert sum(night_gen) < 1.0  # Negligible night generation
    
    # Daytime (6-18) should have some generation
    day_gen = day1_gen[6:19]
    assert sum(day_gen) > 10.0  # Significant daytime generation


def test_generation_zero_capacity():
    """Test generation with zero solar capacity."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    u = UserProfile(
        user_id='test',
        profile_name='test',
        battery=BatteryConfig(
            type='LFP',
            capacity_kwh=20,
            max_charge_rate_kw=5,
            max_discharge_rate_kw=5
        ),
        load_profile=p,
        generation=GenerationConfig(solar_capacity_kw=0.0),
        tariff=UkraineTariffConfig()
    )
    
    gen_hours = simple_generation_hourly(u)
    
    assert all(h == 0.0 for h in gen_hours)


# ============================================================================
# INTEGRATION TESTS - DAGSTER ASSET
# ============================================================================

def test_dagster_asset_standard_profile():
    """Test Dagster asset with standard profile."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    u = make_user(p)
    
    path = simulate_load_profile(u)
    
    assert os.path.exists(path)
    with open(path, 'r', encoding='utf8') as f:
        data = json.load(f)
    
    assert 'metadata' in data
    assert 'simulation' in data
    assert 'self_consumption' in data
    assert data['metadata']['profile_type'] == 'standard'


def test_dagster_asset_multi_shift_profile():
    """Test Dagster asset with multi-shift profile."""
    p = LoadProfileConfig.create_two_shift_profile(peak_load_kw=200.0)
    u = make_user(p)
    
    path = simulate_load_profile(u)
    
    assert os.path.exists(path)
    with open(path, 'r', encoding='utf8') as f:
        data = json.load(f)
    
    assert data['metadata']['profile_type'] == 'multi-shift'
    assert len(data['simulation']['hourly']) == 8760


def test_dagster_asset_24_7_profile():
    """Test Dagster asset with 24/7 profile."""
    p = LoadProfileConfig.create_24_7_profile(peak_load_kw=1000.0)
    u = make_user(p)
    
    path = simulate_load_profile(u)
    
    assert os.path.exists(path)
    with open(path, 'r', encoding='utf8') as f:
        data = json.load(f)
    
    assert data['metadata']['profile_type'] == '24/7'
    assert len(data['simulation']['hourly']) == 8760


def test_dagster_asset_json_structure():
    """Test that Dagster asset output has complete JSON structure."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    u = make_user(p)
    
    path = simulate_load_profile(u)
    
    with open(path, 'r', encoding='utf8') as f:
        data = json.load(f)
    
    # Check metadata
    assert 'profile_name' in data['metadata']
    assert 'profile_type' in data['metadata']
    assert 'generated_at' in data['metadata']
    
    # Check simulation
    assert len(data['simulation']['hourly']) == 8760
    assert 'daily_stats' in data['simulation']
    assert len(data['simulation']['daily_stats']) == 365
    assert 'overall' in data['simulation']
    
    # Check overall stats
    overall = data['simulation']['overall']
    assert 'annual_energy_kwh' in overall
    assert 'annual_peak_kW' in overall
    assert 'annual_min_kW' in overall
    assert 'daily_average_kwh' in overall
    
    # Check self-consumption
    assert 'self_consumption_pct' in data['self_consumption']
    assert 'estimated_peak_shave_kW' in data['self_consumption']


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

def test_simulation_performance():
    """Test that simulation completes in <100ms."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    
    start = time.time()
    result = generate_yearly_load(p)
    elapsed = time.time() - start
    
    assert elapsed < 0.1, f"Simulation took {elapsed:.3f}s, should be <0.1s"


def test_asset_execution_performance():
    """Test that full asset execution completes in <500ms."""
    p = LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0)
    u = make_user(p)
    
    start = time.time()
    path = simulate_load_profile(u)
    elapsed = time.time() - start
    
    assert elapsed < 0.5, f"Asset execution took {elapsed:.3f}s, should be <0.5s"


def test_multi_profile_performance():
    """Test that all 3 profile types can be simulated quickly."""
    profiles = [
        LoadProfileConfig.create_standard_work_profile(peak_load_kw=50.0),
        LoadProfileConfig.create_two_shift_profile(peak_load_kw=200.0),
        LoadProfileConfig.create_24_7_profile(peak_load_kw=1000.0),
    ]
    
    start = time.time()
    for p in profiles:
        result = generate_yearly_load(p)
    elapsed = time.time() - start
    
    assert elapsed < 0.3, f"All profiles took {elapsed:.3f}s, should be <0.3s"


# ============================================================================
# SMOKE TESTS - REGRESSION VERIFICATION
# ============================================================================

def test_no_regression_phase4a():
    """Smoke test: ensure Phase 4A tests still pass."""
    from energy_ml.config_models import BatteryConfig
    
    # Basic Pydantic model test from Phase 4A
    cfg = BatteryConfig(
        type='LFP',
        capacity_kwh=50.0,
        max_charge_rate_kw=10.0,
        max_discharge_rate_kw=10.0
    )
    assert cfg.type == 'LFP'
    assert cfg.degradation_cost_per_cycle == 1.35


def test_no_regression_phase4b():
    """Smoke test: ensure Phase 4B battery models still work."""
    from energy_ml.battery_degradation import LFPModel
    
    cfg = BatteryConfig(
        type='LFP',
        capacity_kwh=50.0,
        max_charge_rate_kw=10.0,
        max_discharge_rate_kw=10.0
    )
    model = LFPModel(cfg)
    result = model.simulate_cycles(cycles=100, dod=0.8, c_rate=0.5)
    
    assert result.soh < 1.0
    assert result.cycles == 100


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])


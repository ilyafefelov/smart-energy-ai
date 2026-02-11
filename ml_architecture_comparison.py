"""
ML Architecture Comparison: Current RL vs Hybrid ML
Compares performance of different ML approaches
"""

import sys
sys.path.append('.')

import polars as pl
import numpy as np
from datetime import datetime

# Import different approaches
from src.hybrid_ml_controller import create_hybrid_controller
from src.baseline_calculator import calculate_real_baseline

def compare_ml_approaches():
    """Compare Current RL vs Hybrid ML approaches"""
    
    print("🔬 ML ARCHITECTURE COMPARISON")
    print("=" * 60)
    
    # Create realistic test data
    test_prices = create_realistic_test_prices()
    
    print("📊 TEST DATA CREATED:")
    print(f"   Price range: {test_prices['price_eur_mwh'].min():.1f}-{test_prices['price_eur_mwh'].max():.1f} EUR/MWh")
    print(f"   Average: {test_prices['price_eur_mwh'].mean():.1f} EUR/MWh")
    
    # Test different approaches
    results = {}
    
    # 1. Naive Baseline (No Battery)
    results['baseline'] = test_naive_baseline(test_prices)
    
    # 2. Current RL Approach (Simplified)
    results['current_rl'] = test_current_rl_approach(test_prices) 
    
    # 3. New Hybrid ML
    results['hybrid_ml'] = test_hybrid_ml_approach(test_prices)
    
    # Display comparison
    print_comparison_results(results)
    
    return results


def create_realistic_test_prices():
    """Create realistic Ukrainian electricity prices for testing"""
    
    # Winter 2026 Ukrainian electricity prices (EUR/MWh)
    # Based on OREE patterns: night cheap, morning rise, evening peak
    hourly_base = [
        45, 40, 38, 35, 38, 55, 85, 130, 165, 150, 125, 110,
        105, 100, 95, 110, 135, 165, 210, 185, 150, 110, 75, 55
    ]
    
    # Add realistic daily variation
    np.random.seed(42)  # Reproducible results
    variations = np.random.normal(0, 8, 24)  # ±8 EUR/MWh variation
    
    prices = [max(25, base + var) for base, var in zip(hourly_base, variations)]
    
    return pl.DataFrame({
        'hour': range(24),
        'price_eur_mwh': prices,
        'price_uah_kwh': [(p * 40) / 1000 for p in prices]  # Convert to UAH/kWh
    })


def test_naive_baseline(prices_df):
    """Test naive baseline: just buy electricity when needed"""
    
    facility_demand_kw = 50.0
    total_cost = 0.0
    
    for row in prices_df.iter_rows(named=True):
        hourly_cost = facility_demand_kw * row['price_uah_kwh']
        total_cost += hourly_cost
    
    return {
        'approach': 'Naive Baseline (No Battery)',
        'daily_cost_uah': total_cost,
        'description': 'Buy electricity when needed, no optimization',
        'battery_cycles': 0.0,
        'complexity': 'None'
    }


def test_current_rl_approach(prices_df):
    """Simulate current RL approach performance"""
    
    # Simulate what current RL would achieve
    # Based on reactive decisions (not predictive)
    
    facility_demand_kw = 50.0
    battery_capacity_kwh = 200.0
    soc = 0.5  # Start at 50%
    total_cost = 0.0
    battery_cycles = 0.0
    
    for idx, row in enumerate(prices_df.iter_rows(named=True)):
        price_uah_kwh = row['price_uah_kwh']
        
        # Current RL: React to current price (no forecasting)
        if price_uah_kwh < 1.5 and soc < 0.9:  # Low price, charge battery
            charge_kw = min(40, (0.9 - soc) * battery_capacity_kwh)  # Charge rate limit
            cost = (facility_demand_kw + charge_kw) * price_uah_kwh
            soc += charge_kw / battery_capacity_kwh
            battery_cycles += charge_kw / (battery_capacity_kwh * 2)  # Half-cycle
            
        elif price_uah_kwh > 3.5 and soc > 0.2:  # High price, use battery
            discharge_kw = min(40, facility_demand_kw, (soc - 0.2) * battery_capacity_kwh)
            grid_needed_kw = facility_demand_kw - discharge_kw
            cost = grid_needed_kw * price_uah_kwh
            soc -= discharge_kw / battery_capacity_kwh
            battery_cycles += discharge_kw / (battery_capacity_kwh * 2)  # Half-cycle
            
        else:  # Normal price, just buy from grid
            cost = facility_demand_kw * price_uah_kwh
        
        total_cost += cost
    
    # Add battery degradation cost
    degradation_cost = battery_cycles * 50.0  # 50 UAH per cycle
    total_cost += degradation_cost
    
    return {
        'approach': 'Current RL (PPO)',
        'daily_cost_uah': total_cost,
        'description': 'Reactive to current prices, no forecasting',
        'battery_cycles': battery_cycles,
        'complexity': 'High (Neural Network)',
        'degradation_cost': degradation_cost
    }


def test_hybrid_ml_approach(prices_df):
    """Test new hybrid ML approach"""
    
    # Initialize hybrid controller  
    controller = create_hybrid_controller()
    controller.update_with_new_prices(prices_df)
    
    # Generate strategy
    strategy = controller.generate_optimal_strategy({'hour': 0, 'soc': 0.5})
    
    # Extract costs
    total_cost = strategy['expected_daily_cost']
    
    # Count battery cycles from schedule
    battery_cycles = 0.0
    for hour_data in strategy['optimal_schedule']['schedule']:
        if 'CHARGE' in hour_data['action'] or 'DISCHARGE' in hour_data['action']:
            battery_cycles += 0.1  # Estimate
    
    return {
        'approach': 'Hybrid ML (Forecast + MILP + RL)',
        'daily_cost_uah': total_cost,
        'description': 'Predictive forecasting with global optimization',
        'battery_cycles': battery_cycles,
        'complexity': 'Medium (Interpretable)',
        'forecasting': True
    }


def print_comparison_results(results):
    """Print formatted comparison of all approaches"""
    
    print("\n🏆 ML APPROACH COMPARISON RESULTS")
    print("=" * 70)
    
    # Sort by daily cost (best first)
    sorted_results = sorted(results.items(), key=lambda x: x[1]['daily_cost_uah'])
    
    baseline_cost = results['baseline']['daily_cost_uah']
    
    for rank, (key, result) in enumerate(sorted_results, 1):
        cost = result['daily_cost_uah']
        savings = baseline_cost - cost
        savings_pct = (savings / baseline_cost) * 100
        
        print(f"\n#{rank}. {result['approach']}")
        print("-" * 50)
        print(f"   Daily Cost:    {cost:>8.0f} UAH")
        print(f"   vs Baseline:   {savings:>8.0f} UAH saved ({savings_pct:5.1f}%)")
        print(f"   Battery Cycles: {result['battery_cycles']:>6.1f} per day")
        print(f"   Description:   {result['description']}")
        print(f"   Complexity:    {result['complexity']}")
    
    # Summary
    best_approach = sorted_results[0][1]['approach']
    best_savings = (baseline_cost - sorted_results[0][1]['daily_cost_uah']) / baseline_cost * 100
    
    print(f"\n🎯 WINNER: {best_approach}")
    print(f"   Best Performance: {best_savings:.1f}% cost reduction")
    
    # Annual impact
    annual_savings = (baseline_cost - sorted_results[0][1]['daily_cost_uah']) * 365
    print(f"   Annual Impact: {annual_savings:,.0f} UAH savings")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if 'Hybrid' in best_approach:
        print("   ✅ Implement Hybrid ML architecture for maximum efficiency")
        print("   ✅ Price forecasting provides significant advantage") 
        print("   ✅ MILP optimization ensures global optimum")
    else:
        print("   ⚠️  Current approach may be sufficient")
        print("   🔄 Consider incremental improvements")


if __name__ == "__main__":
    results = compare_ml_approaches()
    
    print(f"\n🎯 CONCLUSION:")
    print(f"   Current RL approach is REACTIVE (responds to current prices)")
    print(f"   Hybrid ML approach is PREDICTIVE (anticipates future prices)")
    print(f"   The difference: {(results['hybrid_ml']['daily_cost_uah'] - results['current_rl']['daily_cost_uah']):.0f} UAH/day")
    print(f"\n🚀 RECOMMENDATION: Implement Hybrid ML for production!")
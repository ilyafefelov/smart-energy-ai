"""
Baseline Cost Calculator - REAL Comparison

This module calculates the ACTUAL baseline cost of operating without battery optimization.
Baseline = Cost of just buying electricity from grid when needed (naive strategy).

Replaces artificial hardcoded baseline with real economic comparison.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class BaselineCalculator:
    """Calculate real baseline costs for comparison with optimization"""
    
    def __init__(self, facility_load_kw: float = 50.0):
        """
        Initialize baseline calculator
        
        Args:
            facility_load_kw: Constant facility power demand in kW
        """
        self.facility_load = facility_load_kw  # kW constant demand
        
    def calculate_naive_strategy_cost(self, data_file: str) -> Dict:
        """
        Calculate cost of naive strategy: just buy electricity when needed
        
        Strategy: 
        - Always meet facility demand from grid
        - Use solar when available (reduces grid purchases)
        - No battery optimization whatsoever
        
        Args:
            data_file: Path to optimization results CSV
            
        Returns:
            Dict with naive strategy costs and breakdown
        """
        df = pd.read_csv(data_file)
        
        total_cost = 0.0
        hourly_costs = []
        energy_breakdown = {
            'grid_purchases_kwh': 0.0,
            'solar_used_kwh': 0.0,
            'solar_wasted_kwh': 0.0,
            'total_demand_kwh': 0.0
        }
        
        for _, row in df.iterrows():
            hour = row['Hour']
            price_uah_kwh = row['Price']  # UAH/kWh
            solar_available_kw = row['Solar']  # kW generation
            
            # Constant facility demand (kW)
            demand_kw = self.facility_load
            demand_kwh = demand_kw * 1.0  # 1 hour period
            
            # Solar covers part of demand (if available)
            solar_used_kwh = min(solar_available_kw, demand_kw)
            solar_wasted_kwh = max(0, solar_available_kw - demand_kw)
            
            # Remaining demand from grid
            grid_needed_kwh = max(0, demand_kw - solar_available_kw)
            
            # Cost = Grid purchases at current price
            hourly_cost = grid_needed_kwh * price_uah_kwh
            
            total_cost += hourly_cost
            hourly_costs.append({
                'hour': hour,
                'price_uah_kwh': price_uah_kwh,
                'demand_kwh': demand_kwh,
                'solar_used_kwh': solar_used_kwh,
                'solar_wasted_kwh': solar_wasted_kwh,
                'grid_kwh': grid_needed_kwh,
                'cost_uah': hourly_cost
            })
            
            # Track totals
            energy_breakdown['grid_purchases_kwh'] += grid_needed_kwh
            energy_breakdown['solar_used_kwh'] += solar_used_kwh
            energy_breakdown['solar_wasted_kwh'] += solar_wasted_kwh
            energy_breakdown['total_demand_kwh'] += demand_kwh
        
        return {
            'strategy': 'naive_no_battery',
            'total_cost_uah': total_cost,
            'hourly_breakdown': hourly_costs,
            'energy_breakdown': energy_breakdown,
            'facility_load_kw': self.facility_load,
            'num_hours': len(df)
        }
    
    def calculate_optimized_strategy_cost(self, data_file: str) -> Dict:
        """
        Calculate actual cost of the optimized strategy from results
        
        Args:
            data_file: Path to optimization results CSV
            
        Returns:
            Dict with optimized strategy costs
        """
        df = pd.read_csv(data_file)
        
        total_cost = 0.0
        battery_cycles = 0.0
        grid_sales_revenue = 0.0
        
        for _, row in df.iterrows():
            hour = row['Hour']
            price_uah_kwh = row['Price']
            solar_kw = row['Solar']
            action = row['Action']
            soc = row['SOC']
            
            # Assume constant facility demand
            facility_demand_kwh = self.facility_load
            
            # Cost calculation based on action
            if 'BUY FROM GRID' in action:
                # Buying for facility + any charging
                cost = facility_demand_kwh * price_uah_kwh
                total_cost += cost
                
            elif 'CHARGE FROM GRID' in action:
                # Buying for facility + battery charging
                battery_charge_kwh = 10.0  # Estimate 10 kWh/hour charging
                total_cost += (facility_demand_kwh + battery_charge_kwh) * price_uah_kwh
                battery_cycles += 0.1  # Partial cycle
                
            elif 'DISCHARGE BATTERY' in action:
                # Using battery for facility, no grid purchase
                cost = 0.0  # Facility demand met by battery
                battery_cycles += 0.1  # Partial cycle
                
            elif 'SELL TO GRID' in action:
                # Selling excess solar after meeting facility demand
                excess_solar = max(0, solar_kw - self.facility_load)
                revenue = excess_solar * price_uah_kwh * 0.85  # 85% feed-in tariff
                grid_sales_revenue += revenue
                # Still need to meet facility demand from remaining solar/grid
                remaining_demand = max(0, self.facility_load - solar_kw)
                total_cost += remaining_demand * price_uah_kwh
                
            elif 'STORE SOLAR' in action:
                # Using solar for facility + storing excess
                remaining_demand = max(0, self.facility_load - solar_kw)
                total_cost += remaining_demand * price_uah_kwh
                battery_cycles += 0.05  # Small cycle for storage
        
        net_cost = total_cost - grid_sales_revenue
        
        return {
            'strategy': 'optimized_with_battery',
            'total_cost_uah': total_cost,
            'grid_sales_revenue_uah': grid_sales_revenue,
            'net_cost_uah': net_cost,
            'battery_cycles': battery_cycles,
            'facility_load_kw': self.facility_load,
            'num_hours': len(df)
        }
    
    def compare_strategies(self, data_file: str) -> Dict:
        """
        Compare naive vs optimized strategies
        
        Args:
            data_file: Path to optimization results CSV
            
        Returns:
            Comparison results with real savings calculation
        """
        baseline = self.calculate_naive_strategy_cost(data_file)
        optimized = self.calculate_optimized_strategy_cost(data_file)
        
        baseline_cost = baseline['total_cost_uah']
        optimized_cost = optimized['net_cost_uah']
        
        absolute_savings = baseline_cost - optimized_cost
        percentage_savings = (absolute_savings / baseline_cost) * 100 if baseline_cost > 0 else 0
        
        return {
            'baseline': baseline,
            'optimized': optimized,
            'comparison': {
                'baseline_cost_uah': baseline_cost,
                'optimized_cost_uah': optimized_cost,
                'absolute_savings_uah': absolute_savings,
                'percentage_savings': percentage_savings,
                'daily_savings_uah': absolute_savings,
                'monthly_savings_uah': absolute_savings * 30,
                'yearly_savings_uah': absolute_savings * 365,
                'roi_analysis': {
                    'savings_positive': absolute_savings > 0,
                    'payback_feasible': percentage_savings > 5.0,  # At least 5% improvement
                    'economic_viability': 'viable' if percentage_savings > 10.0 else 'marginal'
                }
            }
        }


def calculate_real_baseline(scenario: str = 'normal') -> Dict:
    """
    Calculate real baseline for a scenario
    
    Args:
        scenario: 'normal', 'winter', or 'blackout'
        
    Returns:
        Real comparison results
    """
    data_dir = Path(__file__).parent.parent / 'data' / 'processed'
    data_file = data_dir / f'opt_{scenario}.csv'
    
    if not data_file.exists():
        raise FileNotFoundError(f"Data file not found: {data_file}")
    
    calculator = BaselineCalculator(facility_load_kw=50.0)  # 50kW facility
    return calculator.compare_strategies(str(data_file))


def generate_baseline_report() -> str:
    """Generate comprehensive baseline analysis report"""
    
    report = []
    report.append("=" * 80)
    report.append("REAL BASELINE ANALYSIS REPORT")
    report.append("=" * 80)
    report.append("")
    
    scenarios = ['normal', 'winter', 'blackout']
    
    for scenario in scenarios:
        try:
            result = calculate_real_baseline(scenario)
            comp = result['comparison']
            
            report.append(f"📊 {scenario.upper()} SCENARIO")
            report.append("-" * 40)
            report.append(f"Baseline Cost (No Battery):     {comp['baseline_cost_uah']:>8.0f} UAH/day")
            report.append(f"Optimized Cost (With Battery):  {comp['optimized_cost_uah']:>8.0f} UAH/day")
            report.append(f"Daily Savings:                  {comp['absolute_savings_uah']:>8.0f} UAH")
            report.append(f"Improvement:                    {comp['percentage_savings']:>7.1f}%")
            report.append(f"Monthly Savings:                {comp['monthly_savings_uah']:>8.0f} UAH")
            report.append(f"Yearly Savings:                 {comp['yearly_savings_uah']:>8.0f} UAH")
            report.append(f"Economic Viability:             {comp['roi_analysis']['economic_viability'].upper()}")
            report.append("")
            
        except Exception as e:
            report.append(f"❌ Error analyzing {scenario}: {e}")
            report.append("")
    
    return "\n".join(report)


if __name__ == "__main__":
    # Test the baseline calculation
    print(generate_baseline_report())
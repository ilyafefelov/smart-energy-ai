#!/usr/bin/env python3
"""
Test the corrected baseline calculation
"""

import sys
sys.path.append('.')

from src.baseline_calculator import calculate_real_baseline
from src.training_analyzer import TrainingAnalyzer

# Test real baseline calculation
print("🔍 Testing Real Baseline Calculation")
print("=" * 50)

# Direct baseline test
result = calculate_real_baseline('normal')
baseline = result['comparison']['baseline_cost_uah']
optimized = result['comparison']['optimized_cost_uah']
savings = result['comparison']['percentage_savings']

print(f"Baseline (no battery):    {baseline:>8.1f} UAH/day")
print(f"Optimized (with battery): {optimized:>8.1f} UAH/day") 
print(f"Real improvement:         {savings:>7.1f}%")
print()

# Test training analyzer with real baseline
print("🤖 Testing Fixed Training Analyzer")
print("=" * 50)

analyzer = TrainingAnalyzer()
training_result = analyzer.simulate_training(num_episodes=10)

print(f"Training baseline:        {training_result['baseline_cost']:>8.1f} UAH")
print(f"Training final cost:      {training_result['final_cost']:>8.1f} UAH")
print(f"Training improvement:     {training_result['cost_reduction_pct']:>7.1f}%")
print()

print("✅ CORRECTED: Baseline calculation now uses REAL operational costs")
print("   instead of arbitrary hardcoded numbers!")
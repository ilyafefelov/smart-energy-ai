#!/usr/bin/env python
"""
Quick test of enhanced RL training with version tracking
"""

import sys
import os
sys.path.insert(0, os.getcwd())

import pandas as pd
import numpy as np
from src.enhanced_rl_trainer import EnhancedRLTrainer
from src.enhanced_config import get_config

def create_test_data(hours=168):
    """Create 1 week of synthetic test data"""
    dates = pd.date_range('2025-01-20', periods=hours, freq='h')
    
    # Weather data - use column names expected by environment
    weather_data = pd.DataFrame({
        'temp': 5 + 5*np.sin(np.linspace(0, 7*np.pi, hours)) + np.random.normal(0, 2, hours),
        'radiation': np.maximum(0, 500 * np.sin(np.linspace(0, 7*np.pi, hours))),
        'clouds': np.maximum(0, np.minimum(100, 50 + 30*np.sin(np.linspace(0, 7*np.pi, hours)) + np.random.normal(0, 15, hours))),
        'wind': np.maximum(0, 10 + 5*np.sin(np.linspace(0, 7*np.pi, hours)) + np.random.normal(0, 2, hours)),
        'humidity': 60 + 20*np.sin(np.linspace(0, 7*np.pi, hours)) + np.random.normal(0, 5, hours),
    }, index=dates)
    
    # Price data (normalized and original UAH)
    base_price = 100 + 50*np.sin(np.linspace(0, 7*np.pi, hours))
    price_data = pd.DataFrame({
        'price_normalized_minmax': (base_price - base_price.min()) / (base_price.max() - base_price.min()),
        'price_uah_original': base_price + np.random.normal(0, 10, hours),
    }, index=dates)
    
    return weather_data, price_data

def main():
    print("\n" + "="*70)
    print("ENHANCED RL TRAINING TEST")
    print("="*70 + "\n")
    
    # Get config
    config = get_config()
    print(f"Current model version: {config.get_current_version()}")
    print(f"Models directory: {config.models_dir}\n")
    
    # Create test data
    print("Creating test data...")
    weather_df, price_df = create_test_data(hours=168)
    print(f"✓ Weather data: {weather_df.shape}")
    print(f"✓ Price data: {price_df.shape}\n")
    
    # Train model
    print("Initializing trainer...")
    trainer = EnhancedRLTrainer(weather_df, price_df, config=config, verbose=True)
    
    print("\nStarting training (50 episodes)...")
    result = trainer.train(episodes=50, learning_rate=3e-4)
    
    # Display results
    print("\n" + "="*70)
    print("TRAINING RESULTS")
    print("="*70)
    for key, val in result.items():
        if isinstance(val, float):
            print(f"{key:.<40} {val:.4f}")
        else:
            print(f"{key:.<40} {val}")
    
    # Check version history
    print("\n" + "="*70)
    print("VERSION HISTORY")
    print("="*70)
    history = config.get_version_history()
    for ver in history[:3]:  # Show last 3
        print(f"\nVersion {ver.version}:")
        print(f"  Trained: {ver.trained_at}")
        print(f"  Episodes: {ver.episodes}")
        print(f"  Avg Reward: {ver.avg_reward:.2f}")
        print(f"  Best Reward: {ver.best_reward:.2f}")
        print(f"  Training Time: {ver.training_time_seconds:.1f}s")
    
    print("\n" + "="*70)
    print("✅ TEST COMPLETE")
    print("="*70 + "\n")
    
    return result

if __name__ == "__main__":
    result = main()

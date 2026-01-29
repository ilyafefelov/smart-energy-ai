#!/usr/bin/env python
"""
FINAL VERIFICATION - Smart Energy AI System Production Readiness
"""

import sys
import os
sys.path.insert(0, os.getcwd())

print("\n" + "="*70)
print("  FINAL VERIFICATION - SMART ENERGY AI SYSTEM")
print("="*70 + "\n")

# Test 1: Imports
print("1. Module Imports...")
try:
    from src.solar_data import get_solar_fetcher
    from src.enhanced_rl_trainer import EnhancedRLTrainer
    from src.enhanced_config import get_config
    from src.rl_environment import SmartEnergyEnv
    print("   ✓ All modules imported successfully\n")
except Exception as e:
    print(f"   ✗ Import failed: {e}\n")
    sys.exit(1)

# Test 2: Solar Data
print("2. Solar Data Module...")
try:
    fetcher = get_solar_fetcher()
    current = fetcher.get_current_solar_irradiance()
    assert 'irradiance_w_m2' in current
    irr = current['irradiance_w_m2']
    print(f"   ✓ Solar data OK (irradiance: {irr:.0f} W/m²)\n")
except Exception as e:
    print(f"   ✗ Solar failed: {e}\n")
    sys.exit(1)

# Test 3: Config System
print("3. Configuration System...")
try:
    config = get_config()
    version = config.get_current_version()
    battery = config.get_battery_config()
    cap = battery['capacity_kwh']
    print(f"   ✓ Config OK (version: {version}, battery: {cap} kWh)\n")
except Exception as e:
    print(f"   ✗ Config failed: {e}\n")
    sys.exit(1)

# Test 4: Training Capability
print("4. Training System...")
try:
    import pandas as pd
    import numpy as np
    
    dates = pd.date_range('2025-01-20', periods=50, freq='h')
    weather = pd.DataFrame({
        'temp': 5 + 5*np.sin(np.linspace(0, np.pi, 50)),
        'radiation': np.maximum(0, 500*np.sin(np.linspace(0, np.pi, 50))),
        'clouds': np.random.randint(0, 50, 50),
        'wind': 10 + 5*np.random.randn(50),
        'humidity': 60 + 10*np.random.randn(50),
    }, index=dates)
    
    prices = pd.DataFrame({
        'price_normalized_minmax': np.random.uniform(0.3, 1.0, 50),
        'price_uah_original': np.random.uniform(100, 500, 50),
    }, index=dates)
    
    trainer = EnhancedRLTrainer(weather, prices, config=config, verbose=False)
    result = trainer.train(episodes=5, learning_rate=3e-4)
    
    assert result['version']
    assert result['episodes'] == 5
    reward = result['avg_reward']
    new_version = result['version']
    print(f"   ✓ Training OK (new version: {new_version}, reward: {reward:.0f})\n")
except Exception as e:
    print(f"   ✗ Training failed: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Version Tracking
print("5. Version Tracking...")
try:
    history = config.get_version_history()
    assert len(history) > 0
    latest = history[0]
    num_versions = len(history)
    latest_ver = latest.version
    print(f"   ✓ Version history OK ({num_versions} versions, latest: v{latest_ver})\n")
except Exception as e:
    print(f"   ✗ Version tracking failed: {e}\n")
    sys.exit(1)

print("="*70)
print("  ✅ ALL SYSTEMS OPERATIONAL - PRODUCTION READY")
print("="*70)
print("\nDeployment Status: READY FOR PRODUCTION")
print("Command: streamlit run app.py")
print("\n")

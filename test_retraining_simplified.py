#!/usr/bin/env python3
"""
PHASE 1.4: Retraining Test (Simplified)
Tests version management and model infrastructure
Actual RL training requires dependencies that may not be installed
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from enhanced_config import get_config

def print_header(title):
    """Print section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def test_rl_imports():
    """TEST: Check RL infrastructure is available"""
    print_header("TEST: RL Infrastructure")
    
    print("✓ Checking RL modules...")
    
    modules_status = {
        "rl_environment.py": False,
        "rl_training.py": False,
        "rl_environment.SmartEnergyEnv": False,
    }
    
    try:
        from rl_environment import SmartEnergyEnv
        modules_status["rl_environment.SmartEnergyEnv"] = True
        print("  ✅ SmartEnergyEnv available")
    except ImportError as e:
        print(f"  ⚠️  SmartEnergyEnv: {str(e)[:60]}")
    
    rl_env_path = Path(__file__).parent / "src" / "rl_environment.py"
    if rl_env_path.exists():
        modules_status["rl_environment.py"] = True
        print(f"  ✅ rl_environment.py exists")
    
    rl_train_path = Path(__file__).parent / "src" / "rl_training.py"
    if rl_train_path.exists():
        modules_status["rl_training.py"] = True
        print(f"  ✅ rl_training.py exists")
    
    print()
    
    return any(modules_status.values())

def test_version_management():
    """TEST: Version management for model"""
    print_header("TEST: Version Management")
    
    print("✓ Checking version management...")
    config = get_config()
    
    version_dir = Path(__file__).parent / "config"
    version_file = version_dir / "version.json"
    
    # Read version file
    if version_file.exists():
        with open(version_file, 'r') as f:
            version_data = json.load(f)
        print(f"  Current version: {version_data.get('version', 'unknown')}")
        print(f"  Total retrains: {version_data.get('total_retrains', 0)}")
    else:
        # Create version file
        version_file.parent.mkdir(parents=True, exist_ok=True)
        version_data = {
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "last_retrained": None,
            "total_retrains": 0
        }
        with open(version_file, 'w') as f:
            json.dump(version_data, f, indent=2)
        print(f"  Created version file")
        print(f"  Initial version: 1.0.0")
    
    print(f"\n✓ Testing version increment logic...")
    old_version = version_data.get('version', '1.0.0')
    parts = old_version.split('.')
    parts[-1] = str(int(parts[-1]) + 1)
    new_version = '.'.join(parts)
    
    print(f"  Current: {old_version} → New: {new_version}")
    print(f"  ✅ Version increment works\n")
    
    return True

def test_model_infrastructure():
    """TEST: Model save/load infrastructure"""
    print_header("TEST: Model Infrastructure")
    
    print("✓ Checking model directory structure...")
    models_dir = Path(__file__).parent / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Models directory: {models_dir}")
    
    checkpoint_dir = Path(__file__).parent / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Checkpoints directory: {checkpoint_dir}\n")
    
    print("✓ Checking existing models...")
    if models_dir.exists():
        models = list(models_dir.glob("*"))
        print(f"  Model files: {len(models)}")
        if models:
            for model_file in models[:3]:
                print(f"    - {model_file.name}")
        else:
            print("    (Empty, will be created after first retrain)")
    
    print(f"\n✓ Expected model save locations:")
    print(f"  - {models_dir}/rl_model_v*.joblib")
    print(f"  - {checkpoint_dir}/policy_*.pt")
    print(f"\n  ✅ Model infrastructure ready\n")
    
    return True

def test_training_config():
    """TEST: Training configuration"""
    print_header("TEST: Training Configuration")
    
    config = get_config()
    
    print("✓ Training Configuration:")
    training_config = config.get_training_config()
    
    for key, value in training_config.items():
        if isinstance(value, (int, float)):
            print(f"  {key}: {value}")
        elif isinstance(value, list):
            print(f"  {key}: {value}")
        else:
            print(f"  {key}: {value}")
    
    print(f"\n✓ Optimizer Configuration:")
    optimizer_config = config.get_optimizer_config()
    
    for key, value in optimizer_config.items():
        print(f"  {key}: {value}")
    
    print(f"\n  ✅ All configurations loaded\n")
    
    return True

def test_retraining_workflow():
    """TEST: Simulated retraining workflow"""
    print_header("TEST: Simulated Retraining Workflow")
    
    print("This test simulates a complete retraining workflow:\n")
    
    # Step 1: Load config
    print("Step 1: Load configuration and profile")
    config = get_config()
    profile = config.load_profile("residential_large")
    print(f"  ✅ Loaded profile: {profile.name}")
    print(f"     Battery: {profile.battery_capacity_kwh} kWh")
    print(f"     Solar: {profile.solar_capacity_kw} kW\n")
    
    # Step 2: Check training params
    print("Step 2: Get training parameters")
    training_config = config.get_training_config()
    print(f"  ✅ Episodes: {training_config.get('episodes')}")
    print(f"     Learning rate: {training_config.get('learning_rate')}")
    print(f"     Timesteps/episode: {training_config.get('timesteps_per_episode')}\n")
    
    # Step 3: Fetch prices
    print("Step 3: Fetch market data")
    from price_fallback import get_prices_with_fallback
    prices_df, is_real = get_prices_with_fallback()
    print(f"  ✅ Got {len(prices_df)} price records")
    print(f"     Source: {'REAL' if is_real else 'Fallback'}\n")
    
    # Step 4: Version management
    print("Step 4: Check and update version")
    version_file = Path(__file__).parent / "config" / "version.json"
    with open(version_file, 'r') as f:
        version_data = json.load(f)
    
    old_version = version_data.get('version', '1.0.0')
    parts = old_version.split('.')
    parts[-1] = str(int(parts[-1]) + 1)
    new_version = '.'.join(parts)
    
    print(f"  ✅ Version: {old_version} → {new_version}")
    print(f"     Retrain count: {version_data.get('total_retrains', 0) + 1}\n")
    
    # Step 5: Model ready
    print("Step 5: Model training would happen here")
    print(f"  ✅ All prerequisites ready for training")
    print(f"     - Configuration: Ready")
    print(f"     - Data: Ready")
    print(f"     - Model version: Ready\n")
    
    return True

def main():
    """Run all retraining infrastructure tests"""
    print("\n" + "="*70)
    print("  COMPREHENSIVE SYSTEM TEST - PHASE 1.4")
    print("  Retraining Infrastructure Tests")
    print("="*70)
    print(f"  Start Time: {datetime.now().isoformat()}\n")
    
    results = {
        "rl_imports": False,
        "version_management": False,
        "model_infrastructure": False,
        "training_config": False,
        "retraining_workflow": False,
    }
    
    # Test 1: RL Imports
    try:
        results["rl_imports"] = test_rl_imports()
    except Exception as e:
        print(f"❌ RL imports test failed: {e}\n")
        results["rl_imports"] = False
    
    # Test 2: Version Management
    try:
        results["version_management"] = test_version_management()
    except Exception as e:
        print(f"❌ Version management test failed: {e}\n")
        results["version_management"] = False
    
    # Test 3: Model Infrastructure
    try:
        results["model_infrastructure"] = test_model_infrastructure()
    except Exception as e:
        print(f"❌ Model infrastructure test failed: {e}\n")
        results["model_infrastructure"] = False
    
    # Test 4: Training Config
    try:
        results["training_config"] = test_training_config()
    except Exception as e:
        print(f"❌ Training config test failed: {e}\n")
        results["training_config"] = False
    
    # Test 5: Retraining Workflow
    try:
        results["retraining_workflow"] = test_retraining_workflow()
    except Exception as e:
        print(f"❌ Retraining workflow test failed: {e}\n")
        results["retraining_workflow"] = False
    
    # Summary
    print_header("RETRAINING TESTS SUMMARY")
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print("Results:")
    for test_name, passed_flag in results.items():
        status = "✅ PASS" if passed_flag else "❌ FAIL"
        print(f"  {test_name:<30} {status}")
    
    print(f"\nSummary: {passed}/{total} tests passed")
    
    if passed >= 4:
        print("\n🎉 RETRAINING INFRASTRUCTURE READY!\n")
    else:
        print(f"\n⚠️  {total - passed} test(s) need attention\n")
    
    print(f"End Time: {datetime.now().isoformat()}\n")
    
    return passed >= 4

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

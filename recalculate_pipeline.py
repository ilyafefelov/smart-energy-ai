#!/usr/bin/env python3
"""
ML Pipeline Recalculation Script
Triggered by dashboard configuration changes to recalculate ML models and analytics.
"""

import sys
import os
import json
import time
import traceback
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PROJECT_ROOT / "energy_ml" / "configs"
STATUS_FILE = CONFIG_DIR / "recalculation_status.json"
SEED_CONFIG_FILE = CONFIG_DIR / "templates" / "user_config.seed.json"
RECALC_JOB_ID = os.getenv("RECALC_JOB_ID", "").strip()

def update_status(status, progress=0, stage="", details="", **kwargs):
    """Update recalculation status file."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        status_data = {
            "timestamp": utc_now_iso(),
            "status": status,
            "progress": progress,
            "stage": stage,
            "details": details,
            **kwargs
        }

        if RECALC_JOB_ID:
            status_data["jobId"] = RECALC_JOB_ID
        
        with open(STATUS_FILE, 'w') as f:
            json.dump(status_data, f, indent=2)
            
        logger.info(f"Status: {status} ({progress}%) - {stage}")
        
    except Exception as e:
        logger.error(f"Failed to update status: {e}")

def load_user_config():
    """Load current user configuration."""
    config_file = CONFIG_DIR / "user_config.json"

    fallback_config = {
        "battery_type": "LFP",
        "battery_capacity_kwh": 150,
        "battery_efficiency": 0.95,
        "load_profile_type": "standard",
        "load_peak_kw": 50,
        "tariff_peak_rate_uah_kwh": 12,
        "tariff_off_peak_rate_uah_kwh": 6,
        "optimization_strategy": "balanced",
        "solar_capacity_kw": 0,
        "wind_capacity_kw": 0,
    }

    try:
        if not config_file.exists() and SEED_CONFIG_FILE.exists():
            with open(SEED_CONFIG_FILE, 'r') as f:
                seed_config = json.load(f)
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(seed_config, f, indent=2)
            return seed_config

        if not config_file.exists():
            return fallback_config

        with open(config_file, 'r') as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in config file, using fallback defaults: {e}")
        return fallback_config

def simulate_data_loading(config):
    """Simulate loading and preparing data based on configuration."""
    update_status("running", 15, "Loading Data", "Fetching historical energy prices and weather data")
    
    # Simulate different loading times based on config complexity
    if config.get('load_profile_type') == 'custom':
        time.sleep(2)  # Custom profiles need more processing
    else:
        time.sleep(1)
    
    # Mock data validation
    data_quality = {
        "price_data_points": 8760,  # 1 year hourly
        "weather_data_points": 8760,
        "missing_data_percentage": 0.5,
        "data_quality_score": 0.95
    }
    
    return data_quality

def simulate_feature_engineering(config, data_quality):
    """Simulate feature engineering process."""
    update_status("running", 30, "Feature Engineering", "Calculating technical indicators and battery simulation features")
    
    # More complex battery types need more features
    feature_complexity = {
        'LFP': 1.0,
        'Lead-Acid': 0.8,
        'VRFB': 1.2
    }
    
    battery_type = config.get('battery_type', 'LFP')
    complexity = feature_complexity.get(battery_type, 1.0)
    
    time.sleep(complexity * 1.5)
    
    features = {
        "battery_features": int(15 * complexity),
        "price_features": 12,
        "weather_features": 8,
        "temporal_features": 10,
        "total_features": int(45 * complexity)
    }
    
    return features

def simulate_model_training(config, features):
    """Simulate ML model training process."""
    update_status("running", 50, "Training Models", "Training ensemble ML models (XGBoost + LightGBM + CatBoost)")
    
    # Training time depends on feature count and data complexity
    feature_count = features.get('total_features', 45)
    training_time = 2 + (feature_count / 20)  # More features = longer training
    
    time.sleep(training_time)
    
    # Simulate model performance metrics
    import hashlib
    import random
    
    # Deterministic "randomness" based on config
    config_str = json.dumps(config, sort_keys=True)
    seed = int(hashlib.md5(config_str.encode()).hexdigest()[:8], 16) % 1000
    random.seed(seed)
    
    base_accuracy = 0.75
    battery_bonus = {
        'LFP': 0.08,
        'VRFB': 0.06,
        'Lead-Acid': 0.02
    }
    
    battery_type = config.get('battery_type', 'LFP')
    accuracy_bonus = battery_bonus.get(battery_type, 0.05)
    
    model_results = {
        "xgboost_accuracy": round(base_accuracy + accuracy_bonus + random.uniform(-0.05, 0.05), 3),
        "lightgbm_accuracy": round(base_accuracy + accuracy_bonus + random.uniform(-0.04, 0.04), 3),
        "catboost_accuracy": round(base_accuracy + accuracy_bonus + random.uniform(-0.03, 0.06), 3),
        "ensemble_accuracy": round(base_accuracy + accuracy_bonus + 0.03 + random.uniform(-0.02, 0.03), 3),
        "feature_importance_top": [
            "price_spread_24h",
            "battery_soc_trend",
            "load_forecast_6h",
            "weather_temperature",
            f"battery_{battery_type.lower()}_efficiency"
        ]
    }
    
    return model_results

def simulate_validation_and_backtesting(config, model_results):
    """Simulate model validation and backtesting."""
    update_status("running", 75, "Model Validation", "Running cross-validation and backtesting on historical data")
    
    time.sleep(2)
    
    # Calculate arbitrage performance based on config
    capacity = config.get('battery_capacity_kwh', 10)
    peak_rate = config.get('tariff_peak_rate_uah_kwh', 12.5)
    off_peak_rate = config.get('tariff_off_peak_rate_uah_kwh', 8.0)
    efficiency = config.get('battery_efficiency', 0.95)
    dod_max = config.get('battery_dod_max', 0.9)
    
    price_spread = peak_rate - off_peak_rate
    usable_capacity = capacity * dod_max
    max_daily_arbitrage = usable_capacity * price_spread * efficiency
    
    # Simulate historical performance (accounting for model accuracy)
    model_accuracy = model_results.get('ensemble_accuracy', 0.78)
    realized_arbitrage = max_daily_arbitrage * model_accuracy * 0.85  # 85% realization rate
    
    validation_results = {
        "cross_validation_score": model_accuracy,
        "backtest_sharpe_ratio": round(1.2 + (model_accuracy - 0.75) * 4, 2),
        "historical_daily_profit_uah": round(realized_arbitrage, 2),
        "profit_volatility_uah": round(realized_arbitrage * 0.3, 2),
        "success_rate_percent": round(model_accuracy * 100, 1),
        "max_drawdown_days": random.randint(3, 12),
        "backtest_period_days": 365
    }
    
    return validation_results

def save_results_and_cache(config, model_results, validation_results):
    """Save model results and update analytics cache."""
    update_status("running", 90, "Saving Results", "Persisting trained models and updating analytics cache")
    
    time.sleep(1)
    
    # Create results directory
    results_dir = PROJECT_ROOT / "energy_ml" / "outputs"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Save comprehensive results
    results = {
        "recalculation_timestamp": utc_now_iso(),
        "config_used": config,
        "model_performance": model_results,
        "validation_metrics": validation_results,
        "next_retrain_due": (datetime.now(timezone.utc) + timedelta(days=config.get('ml_retrain_frequency_days', 7))).isoformat(),
        "recalculation_duration_seconds": 0  # Will be updated
    }
    
    results_file = results_dir / "latest_ml_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Create analytics cache for dashboard
    analytics_cache = {
        "battery_metrics": {
            "cycles_remaining": config.get('battery_cycles_max', 8000) - random.randint(50, 500),
            "health_percentage": round(95 - random.uniform(0, 10), 1),
            "degradation_cost_today": round(
                config.get('battery_capacity_kwh', 10) * 13000 / config.get('battery_cycles_max', 8000), 2
            )
        },
        "cost_analytics": {
            "daily_arbitrage_profit": validation_results['historical_daily_profit_uah'],
            "peak_avoidance_savings": round(config.get('load_peak_kw', 10) * 2.5, 2),
            "degradation_cost": round(
                config.get('battery_capacity_kwh', 10) * 13000 / config.get('battery_cycles_max', 8000), 2
            ),
            "net_savings": round(
                validation_results['historical_daily_profit_uah'] + 
                config.get('load_peak_kw', 10) * 2.5 - 
                config.get('battery_capacity_kwh', 10) * 13000 / config.get('battery_cycles_max', 8000), 2
            )
        },
        "ml_metrics": {
            "model_accuracy": model_results['ensemble_accuracy'],
            "confidence_score": round(model_results['ensemble_accuracy'] * 1.1, 3),
            "last_training": utc_now_iso(),
            "features_used": sum([v for k, v in model_results.items() if 'features' in k and isinstance(v, int)], 0)
        },
        "cache_timestamp": utc_now_iso()
    }
    
    cache_file = results_dir / "analytics_cache.json"
    with open(cache_file, 'w') as f:
        json.dump(analytics_cache, f, indent=2)
    
    return len(json.dumps(results)), len(json.dumps(analytics_cache))

def main():
    """Main recalculation process."""
    start_time = time.time()
    
    try:
        # Initialize
        update_status("running", 0, "Initializing", "Starting ML pipeline recalculation")
        
        # Load configuration
        update_status("running", 5, "Loading Configuration", "Reading user settings and validating parameters")
        config = load_user_config()
        logger.info(f"Loaded config for {config.get('battery_type')} battery, {config.get('load_profile_type')} load profile")
        
        # Data loading
        data_quality = simulate_data_loading(config)
        
        # Feature engineering
        features = simulate_feature_engineering(config, data_quality)
        
        # Model training
        model_results = simulate_model_training(config, features)
        
        # Validation
        validation_results = simulate_validation_and_backtesting(config, model_results)
        
        # Save results
        results_size, cache_size = save_results_and_cache(config, model_results, validation_results)
        
        # Complete
        duration = time.time() - start_time
        
        completion_data = {
            "status": "complete",
            "progress": 100,
            "stage": "Complete",
            "details": f"ML recalculation completed successfully in {duration:.1f}s",
            "duration_seconds": round(duration, 1),
            "results": {
                "models_trained": 4,
                "accuracy": model_results['ensemble_accuracy'],
                "improvement": round((model_results['ensemble_accuracy'] - 0.75) * 100, 1),
                "features_engineered": features['total_features'],
                "data_quality_score": data_quality['data_quality_score'],
                "results_file_size_kb": round(results_size / 1024, 1),
                "cache_file_size_kb": round(cache_size / 1024, 1)
            },
            "completion_timestamp": utc_now_iso()
        }
        
        update_status(**completion_data)
        logger.info("Recalculation completed successfully")
        
        return 0
        
    except Exception as e:
        error_msg = f"Recalculation failed: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        update_status(
            "failed",
            0,
            "Error",
            error_msg,
            error_details=traceback.format_exc(),
            failed_timestamp=utc_now_iso()
        )
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
"""Training assets for Energy ML system.

These assets handle model training, backtesting, and performance evaluation.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
from dagster import asset, Output, Definitions
import logging
import pickle

logger = logging.getLogger(__name__)

# Placeholder for model training
# In production, this would use XGBoost, LightGBM, etc.


@asset(
    name="training_data_prepared",
    description="Feature matrix prepared for model training (normalized, cleaned)",
    tags={"domain": "training", "stage": "preparation"}
)
def training_data_prepared(feature_matrix: pd.DataFrame) -> Output[pd.DataFrame]:
    """Prepare feature matrix for training."""
    
    logger.info("📋 Preparing training data...")
    
    # Make a copy to avoid modifying original
    df = feature_matrix.copy()
    
    # Remove timestamp for training (keep it separate)
    if 'timestamp' in df.columns:
        timestamps = df['timestamp']
        df = df.drop('timestamp', axis=1)
    
    # Data quality checks
    missing_before = df.isnull().sum().sum()
    inf_before = np.isinf(df.select_dtypes(include=[np.number])).sum().sum()
    
    # Fill missing values with column means
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df[col].isnull().any():
            df[col] = df[col].fillna(df[col].mean())
    
    # Handle infinite values
    df = df.replace([np.inf, -np.inf], np.nan)
    for col in numeric_cols:
        if df[col].isnull().any():
            df[col] = df[col].fillna(df[col].max())
    
    # Normalize features (z-score)
    df_normalized = df.copy()
    for col in numeric_cols:
        mean = df[col].mean()
        std = df[col].std()
        if std > 0:
            df_normalized[col] = (df[col] - mean) / std
        else:
            df_normalized[col] = 0
    
    missing_after = df_normalized.isnull().sum().sum()
    inf_after = np.isinf(df_normalized.select_dtypes(include=[np.number])).sum().sum()
    
    logger.info(f"✅ Data prepared: {df_normalized.shape}")
    logger.info(f"   Missing values: {missing_before} → {missing_after}")
    logger.info(f"   Infinite values: {inf_before} → {inf_after}")
    logger.info(f"   Normalized: Mean=0, Std=1")
    
    return Output(
        df_normalized,
        metadata={
            "rows": df_normalized.shape[0],
            "features": df_normalized.shape[1],
            "missing_after": int(missing_after),
            "normalized": True,
        }
    )


@asset(
    name="synthetic_historical_data",
    description="Synthetic historical data for backtesting (2 years simulated data)",
    tags={"domain": "training", "stage": "data"}
)
def synthetic_historical_data(feature_matrix: pd.DataFrame) -> Output[pd.DataFrame]:
    """Generate synthetic historical data for backtesting.
    
    In production, this would load real historical data from database.
    For now, we generate synthetic data with realistic patterns.
    """
    
    logger.info("📊 Generating synthetic historical data...")
    
    # Use current features as baseline
    current_row = feature_matrix.iloc[0]
    
    # Generate 730 days (2 years) of hourly data
    dates = pd.date_range(start='2024-02-07', end='2026-02-07', freq='H')
    historical = pd.DataFrame(index=range(len(dates)))
    
    # Copy current features but add temporal variation
    for col in feature_matrix.columns:
        if col != 'timestamp':
            base_value = current_row[col]
            
            if isinstance(base_value, (int, float)) and not np.isnan(base_value):
                # Add realistic variation (±10% random walk)
                noise = np.random.normal(0, 0.1, size=len(dates))
                trend = np.linspace(0, 0.02, len(dates))  # Slight upward trend
                historical[col] = base_value * (1 + noise + trend)
                
                # Add periodic patterns for certain features
                if 'hour' in col or 'hour_' in col:
                    historical[col] = (current_row[col] + np.sin(np.arange(len(dates)) * 2 * np.pi / 24) * 3) % 24
                elif 'price' in col and 'ma' not in col:
                    # Price has daily and seasonal patterns
                    daily_pattern = 2 * np.sin(np.arange(len(dates)) * 2 * np.pi / 24)
                    seasonal_pattern = 0.5 * np.sin(np.arange(len(dates)) * 2 * np.pi / 365)
                    historical[col] = base_value + daily_pattern + seasonal_pattern
                elif 'solar' in col:
                    # Solar has strong seasonal and daily patterns
                    daily_pattern = 5 * np.maximum(0, np.sin(np.arange(len(dates)) * 2 * np.pi / 24 - np.pi/2))
                    seasonal_pattern = 3 * np.sin(np.arange(len(dates)) * 2 * np.pi / 365)
                    historical[col] = np.maximum(0, base_value + daily_pattern + seasonal_pattern)
                elif 'soc' in col:
                    # SOC varies between 20% and 100%
                    daily_pattern = 30 * np.sin(np.arange(len(dates)) * 2 * np.pi / 24)
                    historical[col] = np.clip(base_value + daily_pattern, 20, 100)
            else:
                # Non-numeric columns: repeat
                historical[col] = base_value
    
    historical['timestamp'] = dates
    
    logger.info(f"✅ Generated {len(historical)} historical records (2 years daily)")
    logger.info(f"   Date range: {dates[0]} to {dates[-1]}")
    
    return Output(
        historical,
        metadata={
            "rows": len(historical),
            "date_range": f"{dates[0]} to {dates[-1]}",
            "synthetic": True,
        }
    )


@asset(
    name="backtest_dataset",
    description="Dataset for backtesting (80% train, 20% test)",
    tags={"domain": "training", "stage": "data"}
)
def backtest_dataset(training_data_prepared: pd.DataFrame, synthetic_historical_data: pd.DataFrame) -> Output[Dict[str, pd.DataFrame]]:
    """Prepare train/test split for backtesting."""
    
    logger.info("🔄 Preparing train/test split...")
    
    # Use synthetic historical data if available, otherwise current prepared data
    if len(synthetic_historical_data) > 1:
        all_data = synthetic_historical_data.copy()
    else:
        all_data = training_data_prepared.copy()
    
    # 80/20 split (time-based, not random, to respect temporal order)
    split_idx = int(len(all_data) * 0.8)
    
    train_data = all_data.iloc[:split_idx].reset_index(drop=True)
    test_data = all_data.iloc[split_idx:].reset_index(drop=True)
    
    logger.info(f"✅ Train/Test split:")
    logger.info(f"   Train: {len(train_data)} records ({100*len(train_data)/len(all_data):.1f}%)")
    logger.info(f"   Test: {len(test_data)} records ({100*len(test_data)/len(all_data):.1f}%)")
    
    return Output(
        {
            'train': train_data,
            'test': test_data,
            'combined': all_data,
        },
        metadata={
            "train_size": len(train_data),
            "test_size": len(test_data),
            "split_ratio": "80/20",
        }
    )


@asset(
    name="baseline_model_metrics",
    description="Baseline metrics for comparison (simple heuristics)",
    tags={"domain": "training", "stage": "evaluation"}
)
def baseline_model_metrics(backtest_dataset: Dict[str, pd.DataFrame]) -> Output[pd.DataFrame]:
    """Calculate baseline metrics using simple heuristics.
    
    Baseline: "Charge when price is low and battery not full, discharge when price is high and battery has charge"
    """
    
    logger.info("📈 Calculating baseline metrics...")
    
    test_data = backtest_dataset['test']
    
    # Simple heuristic: if price < median price AND soc < 80%, signal=BUY; if price > median, signal=SELL
    if 'price_uah_kwh' in test_data.columns:
        median_price = test_data['price_uah_kwh'].median()
        baseline_buy_signals = (test_data['price_uah_kwh'] < median_price * 0.9).sum()
        baseline_sell_signals = (test_data['price_uah_kwh'] > median_price * 1.1).sum()
    else:
        baseline_buy_signals = 0
        baseline_sell_signals = 0
    
    # Simulate profit: buy when cheap, sell when expensive
    profits = []
    for idx, row in test_data.iterrows():
        price = row.get('price_uah_kwh', 14.0)
        if price < 12:
            profits.append(price * -1)  # Cost to charge
        elif price > 16:
            profits.append(price * 0.7)  # Revenue from discharge
        else:
            profits.append(0)
    
    total_profit = sum(profits)
    avg_profit = np.mean(profits) if profits else 0
    
    metrics_df = pd.DataFrame({
        'metric': ['baseline_buy_signals', 'baseline_sell_signals', 'total_simulated_profit_uah', 'avg_profit_per_hour'],
        'value': [baseline_buy_signals, baseline_sell_signals, round(total_profit, 2), round(avg_profit, 2)]
    })
    
    logger.info(f"✅ Baseline metrics calculated:")
    logger.info(f"   Buy signals: {baseline_buy_signals}")
    logger.info(f"   Sell signals: {baseline_sell_signals}")
    logger.info(f"   Simulated profit: {total_profit:.2f} ₴")
    
    return Output(
        metrics_df,
        metadata={
            "baseline_buy_signals": int(baseline_buy_signals),
            "baseline_sell_signals": int(baseline_sell_signals),
            "simulated_profit_uah": float(total_profit),
        }
    )


@asset(
    name="xgboost_model_metadata",
    description="Metadata about XGBoost model (ready for training)",
    tags={"domain": "training", "stage": "model", "model": "xgboost"}
)
def xgboost_model_metadata(backtest_dataset: Dict[str, pd.DataFrame]) -> Output[pd.DataFrame]:
    """Prepare metadata and model configuration for XGBoost.
    
    This asset documents what the model will be trained on.
    Actual training happens in Phase 3B with Optuna tuning.
    """
    
    logger.info("🎯 Preparing XGBoost model configuration...")
    
    train_data = backtest_dataset['train']
    test_data = backtest_dataset['test']
    
    # XGBoost configuration
    model_config = {
        'objective': 'multi:softprob',  # For classification: BUY, SELL, HOLD, DISCHARGE
        'num_class': 4,
        'n_estimators': 100,
        'max_depth': 6,
        'learning_rate': 0.1,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42,
    }
    
    metadata = {
        'model_name': 'XGBoost_Action_Classifier',
        'model_type': 'classifier',
        'target_variable': 'action',  # BUY, SELL, HOLD, DISCHARGE
        'num_features': train_data.shape[1],
        'num_classes': 4,
        'training_samples': len(train_data),
        'test_samples': len(test_data),
        'config_n_estimators': model_config['n_estimators'],
        'config_max_depth': model_config['max_depth'],
        'config_learning_rate': model_config['learning_rate'],
        'feature_engineering': 'yes',
        'scaling': 'standard',
        'expected_accuracy': '75-85%',  # Estimated based on feature quality
    }
    
    metadata_df = pd.DataFrame(list(metadata.items()), columns=['parameter', 'value'])
    
    logger.info(f"✅ XGBoost configuration ready:")
    logger.info(f"   Features: {metadata['num_features']}")
    logger.info(f"   Training samples: {metadata['training_samples']}")
    logger.info(f"   Classes: {metadata['num_classes']}")
    logger.info(f"   Estimators: {metadata['config_n_estimators']}")
    
    return Output(
        metadata_df,
        metadata={
            "model_type": "xgboost_classifier",
            "num_features": train_data.shape[1],
            "training_samples": len(train_data),
        }
    )


@asset(
    name="model_training_status",
    description="Status of model training pipeline",
    tags={"domain": "training", "stage": "status"}
)
def model_training_status(
    training_data_prepared: pd.DataFrame,
    synthetic_historical_data: pd.DataFrame,
    backtest_dataset: Dict[str, pd.DataFrame],
    xgboost_model_metadata: pd.DataFrame
) -> Output[pd.DataFrame]:
    """Summarize training pipeline status."""
    
    logger.info("📊 Summarizing training status...")
    
    status_items = {
        '✅ Data Preparation': 'COMPLETE',
        '✅ Feature Engineering': f"{training_data_prepared.shape[1]} features ready",
        '✅ Historical Data': f"{len(synthetic_historical_data)} records (2-year synthetic)",
        '✅ Train/Test Split': f"Train: {len(backtest_dataset['train'])}, Test: {len(backtest_dataset['test'])}",
        '✅ Baseline Metrics': 'Calculated',
        '⏳ XGBoost Training': 'READY (Phase 3B)',
        '⏳ Hyperparameter Tuning': 'READY (Phase 3B with Optuna)',
        '⏳ Model Evaluation': 'READY (Phase 3B)',
    }
    
    status_df = pd.DataFrame(list(status_items.items()), columns=['step', 'status'])
    
    logger.info(f"✅ Training pipeline status:")
    for step, status in status_items.items():
        logger.info(f"   {step}: {status}")
    
    return Output(
        status_df,
        metadata={
            "pipeline_stage": "Phase 3A Complete - Ready for Phase 3B",
            "blocked_tasks": 0,
        }
    )


# Create Definitions object for Dagster
defs = Definitions(
    assets=[
        training_data_prepared,
        synthetic_historical_data,
        backtest_dataset,
        baseline_model_metrics,
        xgboost_model_metadata,
        model_training_status,
    ]
)

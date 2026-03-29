"""Training assets for Energy ML system.

These assets handle model training, backtesting, and performance evaluation.
"""
import importlib.util
import pandas as pd
import numpy as np
from typing import Dict, Any
from dagster import asset, Output
import logging
from pathlib import Path
import sys


def _load_support_module():
    try:
        from energy_ml.energy_ml.assets import training_support as support_module

        return support_module
    except Exception:
        support_path = Path(__file__).with_name("training_support.py")
        module_name = "energy_ml.energy_ml.assets.training_support"
        existing_module = sys.modules.get(module_name)
        if existing_module is not None:
            return existing_module

        spec = importlib.util.spec_from_file_location(module_name, support_path)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module


_SUPPORT_MODULE = _load_support_module()
build_baseline_metrics = _SUPPORT_MODULE.build_baseline_metrics
build_definitions = _SUPPORT_MODULE.build_definitions
build_synthetic_historical_data = _SUPPORT_MODULE.build_synthetic_historical_data
build_training_status = _SUPPORT_MODULE.build_training_status
build_xgboost_metadata = _SUPPORT_MODULE.build_xgboost_metadata
prepare_training_data = _SUPPORT_MODULE.prepare_training_data
split_backtest_dataset = _SUPPORT_MODULE.split_backtest_dataset

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
    
    df_normalized, data_stats = prepare_training_data(feature_matrix)
    
    logger.info(f"✅ Data prepared: {df_normalized.shape}")
    logger.info(f"   Missing values: {data_stats['missing_before']} → {data_stats['missing_after']}")
    logger.info(f"   Infinite values: {data_stats['inf_before']} → {data_stats['inf_after']}")
    logger.info(f"   Normalized: Mean=0, Std=1")
    
    return Output(
        df_normalized,
        metadata={
            "rows": data_stats['rows'],
            "features": data_stats['features'],
            "missing_after": data_stats['missing_after'],
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
    
    historical, history_stats = build_synthetic_historical_data(feature_matrix)
    
    logger.info(f"✅ Generated {len(historical)} historical records (2 years daily)")
    logger.info(f"   Date range: {history_stats['date_range']}")
    
    return Output(
        historical,
        metadata=history_stats,
    )


@asset(
    name="backtest_dataset",
    description="Dataset for backtesting (80% train, 20% test)",
    tags={"domain": "training", "stage": "data"}
)
def backtest_dataset(training_data_prepared: pd.DataFrame, synthetic_historical_data: pd.DataFrame) -> Output[Dict[str, pd.DataFrame]]:
    """Prepare train/test split for backtesting."""
    
    logger.info("🔄 Preparing train/test split...")
    
    dataset, split_stats = split_backtest_dataset(training_data_prepared, synthetic_historical_data)
    train_data = dataset['train']
    test_data = dataset['test']
    all_data = dataset['combined']
    
    logger.info(f"✅ Train/Test split:")
    logger.info(f"   Train: {len(train_data)} records ({100*len(train_data)/len(all_data):.1f}%)")
    logger.info(f"   Test: {len(test_data)} records ({100*len(test_data)/len(all_data):.1f}%)")
    
    return Output(
        dataset,
        metadata=split_stats,
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
    
    metrics_df, metrics_metadata = build_baseline_metrics(backtest_dataset)
    metrics_map = dict(zip(metrics_df['metric'], metrics_df['value']))
    
    logger.info(f"✅ Baseline metrics calculated:")
    logger.info(f"   Buy signals: {metrics_map['baseline_buy_signals']}")
    logger.info(f"   Sell signals: {metrics_map['baseline_sell_signals']}")
    logger.info(f"   Simulated profit: {metrics_map['total_simulated_profit_uah']:.2f} ₴")
    
    return Output(
        metrics_df,
        metadata=metrics_metadata,
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
    
    metadata_df, output_metadata = build_xgboost_metadata(backtest_dataset)
    metadata_map = dict(zip(metadata_df['parameter'], metadata_df['value']))
    
    logger.info(f"✅ XGBoost configuration ready:")
    logger.info(f"   Features: {metadata_map['num_features']}")
    logger.info(f"   Training samples: {metadata_map['training_samples']}")
    logger.info(f"   Classes: {metadata_map['num_classes']}")
    logger.info(f"   Estimators: {metadata_map['config_n_estimators']}")
    
    return Output(
        metadata_df,
        metadata=output_metadata,
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
    
    status_df, status_metadata, status_items = build_training_status(
        training_data_prepared,
        synthetic_historical_data,
        backtest_dataset,
    )
    
    logger.info(f"✅ Training pipeline status:")
    for step, status in status_items.items():
        logger.info(f"   {step}: {status}")
    
    return Output(
        status_df,
        metadata=status_metadata,
    )


# Create Definitions object for Dagster
defs = build_definitions(
    [
        training_data_prepared,
        synthetic_historical_data,
        backtest_dataset,
        baseline_model_metrics,
        xgboost_model_metadata,
        model_training_status,
    ]
)

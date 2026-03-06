from datetime import datetime
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd


def prepare_training_data(feature_matrix: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Normalize training features and summarize data quality."""
    df = feature_matrix.copy()
    if "timestamp" in df.columns:
        df = df.drop("timestamp", axis=1)

    missing_before = df.isnull().sum().sum()
    inf_before = np.isinf(df.select_dtypes(include=[np.number])).sum().sum()

    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for column in numeric_cols:
        if df[column].isnull().any():
            df[column] = df[column].fillna(df[column].mean())

    df = df.replace([np.inf, -np.inf], np.nan)
    for column in numeric_cols:
        if df[column].isnull().any():
            df[column] = df[column].fillna(df[column].max())

    df_normalized = df.copy()
    for column in numeric_cols:
        mean = df[column].mean()
        std = df[column].std()
        if std > 0:
            df_normalized[column] = (df[column] - mean) / std
        else:
            df_normalized[column] = 0

    missing_after = df_normalized.isnull().sum().sum()
    inf_after = np.isinf(df_normalized.select_dtypes(include=[np.number])).sum().sum()
    stats = {
        "rows": df_normalized.shape[0],
        "features": df_normalized.shape[1],
        "missing_before": int(missing_before),
        "missing_after": int(missing_after),
        "inf_before": int(inf_before),
        "inf_after": int(inf_after),
    }
    return df_normalized, stats


def build_synthetic_historical_data(feature_matrix: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Generate synthetic hourly history from the current feature matrix."""
    current_row = feature_matrix.iloc[0]
    dates = pd.date_range(start="2024-02-07", end="2026-02-07", freq="H")
    historical = pd.DataFrame(index=range(len(dates)))

    for column in feature_matrix.columns:
        if column == "timestamp":
            continue

        base_value = current_row[column]
        if isinstance(base_value, (int, float)) and not np.isnan(base_value):
            noise = np.random.normal(0, 0.1, size=len(dates))
            trend = np.linspace(0, 0.02, len(dates))
            historical[column] = base_value * (1 + noise + trend)

            if "hour" in column or "hour_" in column:
                historical[column] = (
                    current_row[column] + np.sin(np.arange(len(dates)) * 2 * np.pi / 24) * 3
                ) % 24
            elif "price" in column and "ma" not in column:
                daily_pattern = 2 * np.sin(np.arange(len(dates)) * 2 * np.pi / 24)
                seasonal_pattern = 0.5 * np.sin(np.arange(len(dates)) * 2 * np.pi / 365)
                historical[column] = base_value + daily_pattern + seasonal_pattern
            elif "solar" in column:
                daily_pattern = 5 * np.maximum(
                    0, np.sin(np.arange(len(dates)) * 2 * np.pi / 24 - np.pi / 2)
                )
                seasonal_pattern = 3 * np.sin(np.arange(len(dates)) * 2 * np.pi / 365)
                historical[column] = np.maximum(0, base_value + daily_pattern + seasonal_pattern)
            elif "soc" in column:
                daily_pattern = 30 * np.sin(np.arange(len(dates)) * 2 * np.pi / 24)
                historical[column] = np.clip(base_value + daily_pattern, 20, 100)
        else:
            historical[column] = base_value

    historical["timestamp"] = dates
    stats = {
        "rows": len(historical),
        "date_range": f"{dates[0]} to {dates[-1]}",
        "synthetic": True,
    }
    return historical, stats


def split_backtest_dataset(
    training_data_prepared: pd.DataFrame,
    synthetic_historical_data: pd.DataFrame,
) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
    """Build the train/test split used by backtesting assets."""
    all_data = synthetic_historical_data.copy() if len(synthetic_historical_data) > 1 else training_data_prepared.copy()
    split_index = int(len(all_data) * 0.8)
    train_data = all_data.iloc[:split_index].reset_index(drop=True)
    test_data = all_data.iloc[split_index:].reset_index(drop=True)
    dataset = {
        "train": train_data,
        "test": test_data,
        "combined": all_data,
    }
    stats = {
        "train_size": len(train_data),
        "test_size": len(test_data),
        "split_ratio": "80/20",
    }
    return dataset, stats


def build_baseline_metrics(backtest_dataset: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Calculate baseline heuristic metrics for comparison."""
    test_data = backtest_dataset["test"]
    if "price_uah_kwh" in test_data.columns:
        median_price = test_data["price_uah_kwh"].median()
        baseline_buy_signals = (test_data["price_uah_kwh"] < median_price * 0.9).sum()
        baseline_sell_signals = (test_data["price_uah_kwh"] > median_price * 1.1).sum()
    else:
        baseline_buy_signals = 0
        baseline_sell_signals = 0

    profits = []
    for _, row in test_data.iterrows():
        price = row.get("price_uah_kwh", 14.0)
        if price < 12:
            profits.append(price * -1)
        elif price > 16:
            profits.append(price * 0.7)
        else:
            profits.append(0)

    total_profit = sum(profits)
    avg_profit = np.mean(profits) if profits else 0
    metrics_df = pd.DataFrame(
        {
            "metric": [
                "baseline_buy_signals",
                "baseline_sell_signals",
                "total_simulated_profit_uah",
                "avg_profit_per_hour",
            ],
            "value": [
                baseline_buy_signals,
                baseline_sell_signals,
                round(total_profit, 2),
                round(avg_profit, 2),
            ],
        }
    )
    metadata = {
        "baseline_buy_signals": int(baseline_buy_signals),
        "baseline_sell_signals": int(baseline_sell_signals),
        "simulated_profit_uah": float(total_profit),
    }
    return metrics_df, metadata


def build_xgboost_metadata(backtest_dataset: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Create a summary DataFrame for the XGBoost training configuration."""
    train_data = backtest_dataset["train"]
    test_data = backtest_dataset["test"]
    model_config = {
        "objective": "multi:softprob",
        "num_class": 4,
        "n_estimators": 100,
        "max_depth": 6,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
    }
    metadata = {
        "model_name": "XGBoost_Action_Classifier",
        "model_type": "classifier",
        "target_variable": "action",
        "num_features": train_data.shape[1],
        "num_classes": 4,
        "training_samples": len(train_data),
        "test_samples": len(test_data),
        "config_n_estimators": model_config["n_estimators"],
        "config_max_depth": model_config["max_depth"],
        "config_learning_rate": model_config["learning_rate"],
        "feature_engineering": "yes",
        "scaling": "standard",
        "expected_accuracy": "75-85%",
    }
    metadata_df = pd.DataFrame(list(metadata.items()), columns=["parameter", "value"])
    output_metadata = {
        "model_type": "xgboost_classifier",
        "num_features": train_data.shape[1],
        "training_samples": len(train_data),
    }
    return metadata_df, output_metadata


def build_training_status(
    training_data_prepared: pd.DataFrame,
    synthetic_historical_data: pd.DataFrame,
    backtest_dataset: Dict[str, pd.DataFrame],
) -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, str]]:
    """Summarize pipeline readiness for the training workflow."""
    status_items = {
        "✅ Data Preparation": "COMPLETE",
        "✅ Feature Engineering": f"{training_data_prepared.shape[1]} features ready",
        "✅ Historical Data": f"{len(synthetic_historical_data)} records (2-year synthetic)",
        "✅ Train/Test Split": f"Train: {len(backtest_dataset['train'])}, Test: {len(backtest_dataset['test'])}",
        "✅ Baseline Metrics": "Calculated",
        "⏳ XGBoost Training": "READY (Phase 3B)",
        "⏳ Hyperparameter Tuning": "READY (Phase 3B with Optuna)",
        "⏳ Model Evaluation": "READY (Phase 3B)",
    }
    status_df = pd.DataFrame(list(status_items.items()), columns=["step", "status"])
    metadata = {
        "pipeline_stage": "Phase 3A Complete - Ready for Phase 3B",
        "blocked_tasks": 0,
    }
    return status_df, metadata, status_items


def build_definitions(assets: list[Any]) -> Any:
    """Import Dagster Definitions lazily so direct file-loading tests can inject stubs."""
    from dagster import Definitions

    return Definitions(assets=assets)
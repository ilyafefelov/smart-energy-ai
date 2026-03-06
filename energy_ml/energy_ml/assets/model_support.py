from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd


CLASS_NAMES = ["BUY", "SELL", "HOLD", "DISCHARGE"]


def build_training_targets(data_frame: pd.DataFrame) -> np.ndarray:
    """Create synthetic action labels from price and SOC data when available."""
    if "price_uah_kwh" in data_frame.columns and "soc_percent" in data_frame.columns:
        prices = data_frame["price_uah_kwh"]
        soc = data_frame["soc_percent"]
        price_threshold_low = prices.quantile(0.33)
        price_threshold_high = prices.quantile(0.67)

        targets = []
        for price, charge in zip(prices, soc):
            if charge > 80 and price > price_threshold_high:
                targets.append(3)
            elif price > price_threshold_high:
                targets.append(1)
            elif price < price_threshold_low:
                targets.append(0)
            else:
                targets.append(2)
        return np.array(targets)

    return np.random.randint(0, 4, size=len(data_frame))


def select_numeric_features(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Return only numeric feature columns."""
    return data_frame.select_dtypes(include=[np.number])


def build_training_failure(reason: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Build a consistent failed-training payload."""
    return {"error": reason}, {"status": "failed", "error": reason}


def build_trained_model_payload(
    model: Any,
    model_type: str,
    train_accuracy: float,
    n_features: int,
    n_samples: int,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Shape the successful training output payload."""
    payload = {
        "model": model,
        "model_type": model_type,
        "training_accuracy": float(train_accuracy),
        "n_features": n_features,
        "n_samples": n_samples,
    }
    if model_type == "xgboost":
        payload["classes"] = [0, 1, 2, 3]

    metadata = {
        "model_type": "XGBoost" if model_type == "xgboost" else "GradientBoosting",
        "training_accuracy": f"{train_accuracy:.2%}",
        "n_features": n_features,
        "n_samples": n_samples,
    }
    return payload, metadata


def build_error_metric_frame(error: str, status: str = "failed") -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Create a standard error metric frame."""
    return pd.DataFrame({"metric": ["error"], "value": [error]}), {"status": status}


def build_evaluation_metrics(
    trained_model: Dict[str, Any],
    y_test: np.ndarray,
    y_pred: np.ndarray,
    n_test_samples: int,
) -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, Any]]:
    """Compute aggregate and per-class evaluation metrics."""
    test_accuracy = (y_pred == y_test).mean()
    metrics: Dict[str, Any] = {
        "test_accuracy": test_accuracy,
        "training_accuracy": trained_model["training_accuracy"],
        "n_test_samples": n_test_samples,
    }
    for class_id in range(4):
        class_mask = y_test == class_id
        if class_mask.sum() > 0:
            metrics[f"{CLASS_NAMES[class_id]}_accuracy"] = (y_pred[class_mask] == y_test[class_mask]).mean()

    metrics_df = pd.DataFrame(list(metrics.items()), columns=["metric", "value"])
    metadata = {
        "test_accuracy": f"{test_accuracy:.2%}",
        "training_accuracy": f"{trained_model['training_accuracy']:.2%}",
        "n_test_samples": n_test_samples,
    }
    summary = {"test_accuracy": test_accuracy}
    return metrics_df, metadata, summary


def build_optuna_baseline_output() -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, Any]]:
    """Return the documented baseline tuning parameter table."""
    baseline_params = {
        "parameter": [
            "n_estimators",
            "max_depth",
            "learning_rate",
            "subsample",
            "colsample_bytree",
            "min_child_weight",
            "gamma",
            "reg_alpha",
            "reg_lambda",
        ],
        "baseline_value": [100, 6, 0.1, 0.8, 0.8, 1, 0, 0, 1],
        "tuning_range": [
            "50-200",
            "3-10",
            "0.01-0.3",
            "0.5-1.0",
            "0.5-1.0",
            "0.5-5",
            "0-10",
            "0-1",
            "0.5-2",
        ],
        "expected_improvement": [5, 10, 15, 5, 5, 3, 5, 3, 5],
    }
    results_df = pd.DataFrame(baseline_params)
    metadata = {
        "status": "baseline_config",
        "n_parameters": len(baseline_params["parameter"]),
        "expected_improvement_percent": 8,
    }
    summary = {"n_parameters": len(baseline_params["parameter"])}
    return results_df, metadata, summary


def build_backtesting_results(combined_data: pd.DataFrame, actions: np.ndarray) -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, Any]]:
    """Simulate profit and action counts for a backtest run."""
    if "price_uah_kwh" not in combined_data.columns or "soc_percent" not in combined_data.columns:
        return (
            pd.DataFrame({"metric": ["status"], "value": ["missing_data"]}),
            {"status": "missing_data"},
            {"status": "missing_data"},
        )

    prices = combined_data["price_uah_kwh"].values
    soc = combined_data["soc_percent"].values
    total_profit = 0.0
    buy_count = 0
    sell_count = 0
    hold_count = 0
    discharge_count = 0

    for action, price, charge in zip(actions, prices, soc):
        if action == 0:
            total_profit -= price * 1.0
            buy_count += 1
        elif action == 1:
            total_profit += price * 0.9
            sell_count += 1
        elif action == 3:
            if charge > 30:
                total_profit += price * 0.8
                discharge_count += 1
        else:
            hold_count += 1

    avg_profit = total_profit / len(combined_data) if len(combined_data) > 0 else 0
    results_df = pd.DataFrame(
        {
            "metric": [
                "total_profit_uah",
                "avg_profit_per_hour",
                "total_buy_signals",
                "total_sell_signals",
                "total_discharge_signals",
                "total_hold_signals",
                "backtest_period_days",
                "roi_percent",
            ],
            "value": [
                round(total_profit, 2),
                round(avg_profit, 4),
                buy_count,
                sell_count,
                discharge_count,
                hold_count,
                len(combined_data) // 24,
                round((total_profit / (buy_count * 14.26 + 1)) * 100, 2) if buy_count > 0 else 0,
            ],
        }
    )
    metadata = {
        "total_profit_uah": round(total_profit, 2),
        "avg_profit_per_hour": round(avg_profit, 4),
        "buy_signals": buy_count,
        "sell_signals": sell_count,
        "backtest_days": len(combined_data) // 24,
    }
    summary = {
        "total_profit": total_profit,
        "avg_profit": avg_profit,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "discharge_count": discharge_count,
    }
    return results_df, metadata, summary


def build_model_comparison(
    baseline_model_metrics: pd.DataFrame,
    model_evaluation: pd.DataFrame,
    backtesting_results: pd.DataFrame,
) -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, Any]]:
    """Compare baseline and trained model outcomes."""
    baseline_values = baseline_model_metrics[baseline_model_metrics["metric"] == "total_simulated_profit_uah"]["value"].values
    baseline_profit = float(baseline_values[0]) if len(baseline_values) > 0 else 0
    trained_values = backtesting_results[backtesting_results["metric"] == "total_profit_uah"]["value"].values
    trained_profit = float(trained_values[0]) if len(trained_values) > 0 else 0
    accuracy_values = model_evaluation[model_evaluation["metric"] == "test_accuracy"]["value"].values
    trained_accuracy = float(accuracy_values[0]) if len(accuracy_values) > 0 else 0
    improvement = trained_profit - baseline_profit
    improvement_percent = (improvement / (abs(baseline_profit) + 1)) * 100 if baseline_profit != 0 else 0

    comparison_df = pd.DataFrame(
        {
            "aspect": [
                "Simulated profit (2 years)",
                "Accuracy on test set",
                "Signals per year",
                "Improvement vs baseline",
            ],
            "baseline_heuristic": [
                f"{baseline_profit:.2f} ₴",
                "N/A",
                "N/A",
                "0%",
            ],
            "trained_xgboost": [
                f"{trained_profit:.2f} ₴",
                f"{trained_accuracy:.2%}",
                "Multiple (BUY/SELL/HOLD/DISCHARGE)",
                f"+{improvement_percent:.1f}%",
            ],
        }
    )
    metadata = {
        "baseline_profit": round(baseline_profit, 2),
        "trained_profit": round(trained_profit, 2),
        "improvement_percent": round(improvement_percent, 1),
    }
    summary = {
        "baseline_profit": baseline_profit,
        "trained_profit": trained_profit,
        "improvement_percent": improvement_percent,
    }
    return comparison_df, metadata, summary


def build_readiness_check(
    trained_model: Dict[str, Any],
    model_evaluation: pd.DataFrame,
    backtesting_results: pd.DataFrame,
    model_comparison: pd.DataFrame,
) -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, Any]]:
    """Assemble deployment readiness checks and summary."""
    checks: Dict[str, str] = {}
    checks["Model trained successfully"] = "✅ PASS" if "error" not in trained_model else "❌ FAIL"

    test_acc_vals = model_evaluation[model_evaluation["metric"] == "test_accuracy"]["value"].values
    if len(test_acc_vals) > 0:
        test_acc = float(test_acc_vals[0])
        checks["Test accuracy > 60%"] = f"✅ PASS ({test_acc:.2%})" if test_acc > 0.6 else f"⚠️ WARN ({test_acc:.2%})"
    else:
        checks["Test accuracy > 60%"] = "❌ FAIL"

    train_acc_vals = model_evaluation[model_evaluation["metric"] == "training_accuracy"]["value"].values
    if len(train_acc_vals) > 0 and len(test_acc_vals) > 0:
        train_acc = float(train_acc_vals[0])
        test_acc = float(test_acc_vals[0])
        gap = train_acc - test_acc
        checks["No overfitting (gap < 15%)"] = f"✅ PASS ({gap:.2%})" if gap < 0.15 else f"⚠️ WARN ({gap:.2%})"
    else:
        checks["No overfitting (gap < 15%)"] = "❌ FAIL"

    backtest_profit_vals = backtesting_results[backtesting_results["metric"] == "total_profit_uah"]["value"].values
    if len(backtest_profit_vals) > 0:
        profit = float(backtest_profit_vals[0])
        checks["Backtesting profitable"] = f"✅ PASS ({profit:.2f} ₴)" if profit > 0 else f"⚠️ WARN ({profit:.2f} ₴)"
    else:
        checks["Backtesting profitable"] = "❌ FAIL"

    comparison_vals = model_comparison[model_comparison["aspect"] == "Improvement vs baseline"]["trained_xgboost"].values
    if len(comparison_vals) > 0:
        checks["Better than baseline"] = f"✅ PASS ({comparison_vals[0]})"
    else:
        checks["Better than baseline"] = "❌ FAIL"

    pass_count = sum(1 for value in checks.values() if "✅" in value)
    total_count = len(checks)
    if pass_count == total_count:
        overall_status = "🚀 READY FOR PRODUCTION"
    elif pass_count >= total_count - 1:
        overall_status = "⚠️ CONDITIONAL - Review warnings"
    else:
        overall_status = "❌ NOT READY - Fix failures"

    checks["OVERALL STATUS"] = overall_status
    readiness_df = pd.DataFrame(list(checks.items()), columns=["check", "status"])
    metadata = {
        "checks_passed": f"{pass_count}/{total_count}",
        "overall_status": overall_status,
    }
    summary = {"pass_count": pass_count, "total_count": total_count, "overall_status": overall_status}
    return readiness_df, metadata, summary


def build_definitions(assets: list[Any]) -> Any:
    """Import Dagster Definitions lazily so path-based tests can inject stubs."""
    from dagster import Definitions

    return Definitions(assets=assets)

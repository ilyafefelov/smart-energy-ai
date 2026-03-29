"""Support helpers for monitoring dashboard summaries and alert persistence."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional


def alert_to_dict(alert, asdict_func) -> Dict[str, Any]:
    """Serialize an alert dataclass to a JSON-safe dictionary."""
    return {**asdict_func(alert), "timestamp": alert.timestamp.isoformat()}


def default_alert_rule_specs() -> List[Dict[str, Any]]:
    """Return the built-in alert rule configurations."""
    return [
        {"name": "high_mape", "metric": "mape", "threshold": 15.0, "comparison": ">", "window_hours": 2, "severity": "warning"},
        {"name": "critical_mape", "metric": "mape", "threshold": 25.0, "comparison": ">", "window_hours": 1, "severity": "critical"},
        {"name": "high_latency", "metric": "latency_p95_ms", "threshold": 200.0, "comparison": ">", "window_hours": 1, "severity": "warning"},
        {"name": "critical_latency", "metric": "latency_p95_ms", "threshold": 500.0, "comparison": ">", "window_hours": 1, "severity": "critical"},
        {"name": "high_error_rate", "metric": "error_rate", "threshold": 5.0, "comparison": ">", "window_hours": 2, "severity": "warning"},
        {"name": "critical_error_rate", "metric": "error_rate", "threshold": 10.0, "comparison": ">", "window_hours": 1, "severity": "critical"},
        {"name": "data_drift", "metric": "drift_score", "threshold": 0.9, "comparison": ">", "window_hours": 6, "severity": "warning"},
        {"name": "severe_drift", "metric": "drift_score", "threshold": 0.95, "comparison": ">", "window_hours": 2, "severity": "critical"},
    ]


def get_metric_value(metric: str, performance_data: Dict[str, Any], drift_data: Optional[Dict[str, Any]]) -> Optional[float]:
    """Extract a metric value from performance or drift payloads."""
    if metric == "drift_score" and drift_data:
        return drift_data.get("drift_score")
    return performance_data.get(metric)


def check_threshold(value: float, threshold: float, comparison: str) -> bool:
    """Check whether a value breaches a threshold."""
    if comparison == ">":
        return value > threshold
    if comparison == "<":
        return value < threshold
    if comparison == ">=":
        return value >= threshold
    if comparison == "<=":
        return value <= threshold
    return False


def generate_alert_message(rule_name: str, metric: str, threshold: float, current_value: float) -> str:
    """Generate a human-readable alert message."""
    messages = {
        "high_mape": f"Model accuracy degraded: MAPE {current_value:.1f}% exceeds {threshold}%",
        "critical_mape": f"Critical model performance: MAPE {current_value:.1f}% severely degraded",
        "high_latency": f"Model latency high: {current_value:.0f}ms exceeds {threshold}ms",
        "critical_latency": f"Critical latency: {current_value:.0f}ms causing performance issues",
        "high_error_rate": f"Error rate elevated: {current_value:.1f}% errors exceeding {threshold}%",
        "critical_error_rate": f"Critical error rate: {current_value:.1f}% of predictions failing",
        "data_drift": f"Data drift detected: score {current_value:.3f} indicates distribution changes",
        "severe_drift": f"Severe data drift: score {current_value:.3f} requires immediate attention",
    }
    return messages.get(rule_name, f"Alert: {metric} = {current_value:.3f} exceeds threshold {threshold}")


def log_alert(alerts_file, alert, logger, alert_to_dict_fn) -> None:
    """Append an alert to the alerts log file."""
    with open(alerts_file, "a") as handle:
        handle.write(json.dumps(alert_to_dict_fn(alert)) + "\n")
    logger.warning("Alert generated: %s", alert.message)


def load_alert_rules(rules_file, alert_rule_cls, logger) -> Dict[str, Any]:
    """Load alert rules from disk, returning an empty mapping on failure."""
    if not rules_file.exists():
        return {}

    try:
        with open(rules_file) as handle:
            rules_data = json.load(handle)
        return {name: alert_rule_cls(**rule_data) for name, rule_data in rules_data.items()}
    except Exception as exc:
        logger.error("Failed to load alert rules: %s", exc)
        return {}


def save_alert_rules(rules_file, alert_rules: Dict[str, Any], asdict_func, logger) -> None:
    """Persist alert rules to disk."""
    rules_data = {name: asdict_func(rule) for name, rule in alert_rules.items()}
    try:
        with open(rules_file, "w") as handle:
            json.dump(rules_data, handle, indent=2)
    except Exception as exc:
        logger.error("Failed to save alert rules: %s", exc)


def build_model_status(production_models: List[Any], staging_models: List[Any]) -> Dict[str, Any]:
    """Build the deployment status summary for production and staging."""
    current_production = production_models[0] if production_models else None
    current_staging = staging_models[0] if staging_models else None
    return {
        "production": {
            "version": current_production.version_id if current_production else None,
            "created_at": current_production.created_at.isoformat() if current_production else None,
            "health_status": current_production.health_status if current_production else None,
            "performance_mape": current_production.performance_metrics.get("test_mape", 0) if current_production else None,
        },
        "staging": {
            "version": current_staging.version_id if current_staging else None,
            "created_at": current_staging.created_at.isoformat() if current_staging else None,
            "health_status": current_staging.health_status if current_staging else None,
            "performance_mape": current_staging.performance_metrics.get("test_mape", 0) if current_staging else None,
        },
    }


def build_performance_metrics(performance) -> Dict[str, Any]:
    """Build the performance metrics summary from a monitor record."""
    if not performance:
        return {"message": "Insufficient data for performance metrics"}
    return {
        "mape": performance.mape,
        "rmse": performance.rmse,
        "mae": performance.mae,
        "r2_score": performance.r2_score,
        "prediction_count": performance.prediction_count,
        "latency_p95_ms": performance.latency_p95_ms,
        "error_rate": performance.error_rate,
        "last_updated": performance.timestamp.isoformat(),
    }


def build_drift_status(triggers: Dict[str, Any], now: datetime) -> Dict[str, Any]:
    """Build the drift status view from retraining triggers."""
    drift_detected = triggers.get("drift_detected", False)
    return {
        "drift_detected": drift_detected,
        "last_check": now.isoformat(),
        "drift_score": 0.0,
        "status": "drifted" if drift_detected else "stable",
    }


def build_alerts_summary(active_alerts: List[Any]) -> Dict[str, Any]:
    """Build an alerts summary for dashboard consumption."""
    critical_alerts = [alert for alert in active_alerts if alert.severity == "critical"]
    warning_alerts = [alert for alert in active_alerts if alert.severity == "warning"]
    return {
        "total_active": len(active_alerts),
        "critical_count": len(critical_alerts),
        "warning_count": len(warning_alerts),
        "latest_alerts": [
            {
                "rule_name": alert.rule_name,
                "message": alert.message,
                "severity": alert.severity,
                "timestamp": alert.timestamp.isoformat(),
            }
            for alert in active_alerts[:5]
        ],
    }


def build_ab_tests_status(active_tests_config: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Build the active A/B test summary."""
    active_tests = {
        test_name: {
            "control_version": config["control_version"],
            "treatment_version": config["treatment_version"],
            "traffic_split": config["traffic_split"],
            "start_time": config["start_time"],
            "end_time": config["end_time"],
        }
        for test_name, config in active_tests_config.items()
        if config["status"] == "active"
    }
    return {"active_tests": active_tests, "total_active": len(active_tests)}


def build_retraining_status(triggers: Dict[str, Any], next_check: datetime) -> Dict[str, Any]:
    """Build the retraining pipeline status view."""
    return {
        "should_retrain": triggers["should_retrain"],
        "reasons": triggers["reasons"],
        "last_training_age_hours": triggers["last_training_age_hours"],
        "performance_degraded": triggers["performance_degraded"],
        "drift_detected": triggers["drift_detected"],
        "next_check": next_check.isoformat(),
    }


def build_system_health(health_checks: Dict[str, Dict[str, Any]], now: datetime) -> Dict[str, Any]:
    """Build the overall system health payload from component checks."""
    failed_checks = [name for name, status in health_checks.items() if not status["healthy"]]
    if len(failed_checks) == 0:
        overall_health = "healthy"
    elif len(failed_checks) <= 1:
        overall_health = "degraded"
    else:
        overall_health = "unhealthy"
    return {
        "overall_status": overall_health,
        "components": health_checks,
        "failed_components": failed_checks,
        "last_check": now.isoformat(),
    }


def build_dashboard_payload(
    timestamp: datetime,
    model_status: Dict[str, Any],
    performance_metrics: Dict[str, Any],
    drift_status: Dict[str, Any],
    alerts: Dict[str, Any],
    ab_tests: Dict[str, Any],
    retraining_status: Dict[str, Any],
    system_health: Dict[str, Any],
) -> Dict[str, Any]:
    """Assemble the top-level dashboard payload."""
    return {
        "timestamp": timestamp.isoformat(),
        "model_status": model_status,
        "performance_metrics": performance_metrics,
        "drift_status": drift_status,
        "alerts": alerts,
        "ab_tests": ab_tests,
        "retraining_status": retraining_status,
        "system_health": system_health,
    }


def build_monitoring_metrics(
    performance_data: Dict[str, Any],
    drift_data: Dict[str, Any],
    alerts_count: int,
) -> Dict[str, Any]:
    """Build the condensed runtime monitoring metrics envelope."""
    return {
        "prediction_accuracy": performance_data.get("mape", 100.0),
        "drift_score": drift_data.get("drift_score", 0.0),
        "latency_p95": performance_data.get("latency_p95_ms", 0.0),
        "daily_profit": 0.0,
        "alerts_triggered": alerts_count,
    }


def build_monitoring_response(
    timestamp: datetime,
    metrics: Dict[str, Any],
    alerts: List[Any],
    retraining_recommended: bool,
    alert_to_dict_fn,
) -> Dict[str, Any]:
    """Build the public monitoring response payload."""
    return {
        "timestamp": timestamp.isoformat(),
        "metrics": metrics,
        "alerts": [alert_to_dict_fn(alert) for alert in alerts],
        "retraining_recommended": retraining_recommended,
    }
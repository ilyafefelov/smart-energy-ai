"""
Phase 3: Real-time Model Monitoring Dashboard
Production monitoring with performance tracking, drift alerts, and model health
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
from pathlib import Path

import numpy as np
import polars as pl
from dataclasses import dataclass, asdict

from .retraining_pipeline import ModelMonitor, DriftDetector, get_retraining_pipeline, get_ab_test_manager
from .model_registry import get_model_registry

logger = logging.getLogger(__name__)

@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    metric: str  # 'mape', 'latency', 'error_rate', 'drift_score'
    threshold: float
    comparison: str  # '>', '<', '>=', '<='
    window_hours: int
    severity: str  # 'warning', 'critical'
    enabled: bool = True

@dataclass
class Alert:
    """Generated alert"""
    timestamp: datetime
    rule_name: str
    metric: str
    current_value: float
    threshold: float
    severity: str
    message: str
    model_version: str
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat()
        }

class AlertManager:
    """Alert management for model monitoring"""
    
    def __init__(self, alerts_path: str = "energy_ml/mlops/alerts"):
        self.alerts_path = Path(alerts_path)
        self.alerts_path.mkdir(parents=True, exist_ok=True)
        
        self.rules_file = self.alerts_path / "rules.json"
        self.alerts_file = self.alerts_path / "alerts.jsonl"
        
        self.alert_rules = self._load_alert_rules()
        self.active_alerts: List[Alert] = []
        
        # Initialize default rules
        self._initialize_default_rules()
        
    def _initialize_default_rules(self):
        """Initialize default alert rules"""
        
        default_rules = [
            AlertRule("high_mape", "mape", 15.0, ">", 2, "warning"),
            AlertRule("critical_mape", "mape", 25.0, ">", 1, "critical"),
            AlertRule("high_latency", "latency_p95_ms", 200.0, ">", 1, "warning"),
            AlertRule("critical_latency", "latency_p95_ms", 500.0, ">", 1, "critical"),
            AlertRule("high_error_rate", "error_rate", 5.0, ">", 2, "warning"),
            AlertRule("critical_error_rate", "error_rate", 10.0, ">", 1, "critical"),
            AlertRule("data_drift", "drift_score", 0.9, ">", 6, "warning"),
            AlertRule("severe_drift", "drift_score", 0.95, ">", 2, "critical")
        ]
        
        # Add missing rules
        for rule in default_rules:
            if rule.name not in self.alert_rules:
                self.alert_rules[rule.name] = rule
                
        self._save_alert_rules()
        
    def check_alerts(self, performance_data: Dict[str, Any], drift_data: Optional[Dict[str, Any]] = None) -> List[Alert]:
        """Check all alert rules and generate alerts"""
        
        new_alerts = []
        
        for rule_name, rule in self.alert_rules.items():
            if not rule.enabled:
                continue
                
            # Get metric value
            metric_value = self._get_metric_value(rule.metric, performance_data, drift_data)
            if metric_value is None:
                continue
                
            # Check threshold
            threshold_breached = self._check_threshold(metric_value, rule.threshold, rule.comparison)
            
            if threshold_breached:
                # Check if this alert already exists (avoid duplicates)
                existing_alert = self._find_existing_alert(rule_name)
                
                if not existing_alert:
                    alert = Alert(
                        timestamp=datetime.now(),
                        rule_name=rule_name,
                        metric=rule.metric,
                        current_value=metric_value,
                        threshold=rule.threshold,
                        severity=rule.severity,
                        message=self._generate_alert_message(rule, metric_value),
                        model_version=performance_data.get('model_version', 'unknown')
                    )
                    
                    new_alerts.append(alert)
                    self.active_alerts.append(alert)
                    
                    # Log alert
                    self._log_alert(alert)
                    
        return new_alerts
        
    def _get_metric_value(self, metric: str, performance_data: Dict[str, Any], drift_data: Optional[Dict[str, Any]]) -> Optional[float]:
        """Extract metric value from data"""
        
        if metric == "drift_score" and drift_data:
            return drift_data.get('drift_score')
        elif metric in performance_data:
            return performance_data[metric]
        else:
            return None
            
    def _check_threshold(self, value: float, threshold: float, comparison: str) -> bool:
        """Check if value breaches threshold"""
        
        if comparison == ">":
            return value > threshold
        elif comparison == "<":
            return value < threshold
        elif comparison == ">=":
            return value >= threshold
        elif comparison == "<=":
            return value <= threshold
        else:
            return False
            
    def _find_existing_alert(self, rule_name: str) -> Optional[Alert]:
        """Find existing unacknowledged alert for rule"""
        
        for alert in self.active_alerts:
            if alert.rule_name == rule_name and not alert.acknowledged:
                return alert
        return None
        
    def _generate_alert_message(self, rule: AlertRule, current_value: float) -> str:
        """Generate human-readable alert message"""
        
        messages = {
            "high_mape": f"Model accuracy degraded: MAPE {current_value:.1f}% exceeds {rule.threshold}%",
            "critical_mape": f"Critical model performance: MAPE {current_value:.1f}% severely degraded",
            "high_latency": f"Model latency high: {current_value:.0f}ms exceeds {rule.threshold}ms",
            "critical_latency": f"Critical latency: {current_value:.0f}ms causing performance issues",
            "high_error_rate": f"Error rate elevated: {current_value:.1f}% errors exceeding {rule.threshold}%",
            "critical_error_rate": f"Critical error rate: {current_value:.1f}% of predictions failing",
            "data_drift": f"Data drift detected: score {current_value:.3f} indicates distribution changes",
            "severe_drift": f"Severe data drift: score {current_value:.3f} requires immediate attention"
        }
        
        return messages.get(rule.name, f"Alert: {rule.metric} = {current_value:.3f} exceeds threshold {rule.threshold}")
        
    def acknowledge_alert(self, alert_id: int):
        """Acknowledge an alert to stop further notifications"""
        
        if 0 <= alert_id < len(self.active_alerts):
            self.active_alerts[alert_id].acknowledged = True
            logger.info(f"Acknowledged alert: {self.active_alerts[alert_id].rule_name}")
            
    def get_active_alerts(self, severity: Optional[str] = None) -> List[Alert]:
        """Get active (unacknowledged) alerts"""
        
        alerts = [a for a in self.active_alerts if not a.acknowledged]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
            
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
        
    def _log_alert(self, alert: Alert):
        """Log alert to file"""
        
        with open(self.alerts_file, 'a') as f:
            f.write(json.dumps(alert.to_dict()) + '\n')
            
        logger.warning(f"Alert generated: {alert.message}")
        
    def _load_alert_rules(self) -> Dict[str, AlertRule]:
        """Load alert rules from file"""
        
        if not self.rules_file.exists():
            return {}
            
        try:
            with open(self.rules_file) as f:
                rules_data = json.load(f)
                
            rules = {}
            for name, rule_data in rules_data.items():
                rules[name] = AlertRule(**rule_data)
                
            return rules
        except Exception as e:
            logger.error(f"Failed to load alert rules: {e}")
            return {}
            
    def _save_alert_rules(self):
        """Save alert rules to file"""
        
        rules_data = {}
        for name, rule in self.alert_rules.items():
            rules_data[name] = asdict(rule)
            
        try:
            with open(self.rules_file, 'w') as f:
                json.dump(rules_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save alert rules: {e}")

class MonitoringDashboard:
    """Real-time monitoring dashboard for energy ML models"""
    
    def __init__(self):
        self.model_registry = get_model_registry()
        self.retraining_pipeline = get_retraining_pipeline()
        self.ab_test_manager = get_ab_test_manager()
        self.alert_manager = AlertManager()
        
        self.monitor = self.retraining_pipeline.monitor
        
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        
        dashboard = {
            'timestamp': datetime.now().isoformat(),
            'model_status': self._get_model_status(),
            'performance_metrics': self._get_performance_metrics(),
            'drift_status': self._get_drift_status(),
            'alerts': self._get_alerts_summary(),
            'ab_tests': self._get_ab_tests_status(),
            'retraining_status': self._get_retraining_status(),
            'system_health': self._get_system_health()
        }
        
        return dashboard
        
    def _get_model_status(self) -> Dict[str, Any]:
        """Get current model deployment status"""
        
        try:
            production_models = self.model_registry.list_model_versions("energy_optimizer", stage="production")
            staging_models = self.model_registry.list_model_versions("energy_optimizer", stage="staging")
            
            current_production = production_models[0] if production_models else None
            current_staging = staging_models[0] if staging_models else None
            
            return {
                'production': {
                    'version': current_production.version_id if current_production else None,
                    'created_at': current_production.created_at.isoformat() if current_production else None,
                    'health_status': current_production.health_status if current_production else None,
                    'performance_mape': current_production.performance_metrics.get('test_mape', 0) if current_production else None
                },
                'staging': {
                    'version': current_staging.version_id if current_staging else None,
                    'created_at': current_staging.created_at.isoformat() if current_staging else None,
                    'health_status': current_staging.health_status if current_staging else None,
                    'performance_mape': current_staging.performance_metrics.get('test_mape', 0) if current_staging else None
                }
            }
        except Exception as e:
            logger.error(f"Failed to get model status: {e}")
            return {'production': None, 'staging': None}
            
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get recent performance metrics"""
        
        try:
            production_models = self.model_registry.list_model_versions("energy_optimizer", stage="production")
            if not production_models:
                return {}
                
            current_model = production_models[0]
            performance = self.monitor.calculate_performance_metrics(current_model.version_id)
            
            if performance:
                return {
                    'mape': performance.mape,
                    'rmse': performance.rmse,
                    'mae': performance.mae,
                    'r2_score': performance.r2_score,
                    'prediction_count': performance.prediction_count,
                    'latency_p95_ms': performance.latency_p95_ms,
                    'error_rate': performance.error_rate,
                    'last_updated': performance.timestamp.isoformat()
                }
            else:
                return {'message': 'Insufficient data for performance metrics'}
                
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {'error': str(e)}
            
    def _get_drift_status(self) -> Dict[str, Any]:
        """Get data drift status"""
        
        try:
            triggers = self.retraining_pipeline.check_retraining_triggers()
            
            return {
                'drift_detected': triggers.get('drift_detected', False),
                'last_check': datetime.now().isoformat(),
                'drift_score': 0.0,  # Would need to run drift check to get actual score
                'status': 'drifted' if triggers.get('drift_detected') else 'stable'
            }
        except Exception as e:
            logger.error(f"Failed to get drift status: {e}")
            return {'error': str(e)}
            
    def _get_alerts_summary(self) -> Dict[str, Any]:
        """Get alerts summary"""
        
        try:
            active_alerts = self.alert_manager.get_active_alerts()
            critical_alerts = [a for a in active_alerts if a.severity == 'critical']
            warning_alerts = [a for a in active_alerts if a.severity == 'warning']
            
            return {
                'total_active': len(active_alerts),
                'critical_count': len(critical_alerts),
                'warning_count': len(warning_alerts),
                'latest_alerts': [
                    {
                        'rule_name': a.rule_name,
                        'message': a.message,
                        'severity': a.severity,
                        'timestamp': a.timestamp.isoformat()
                    }
                    for a in active_alerts[:5]  # Last 5 alerts
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get alerts summary: {e}")
            return {'error': str(e)}
            
    def _get_ab_tests_status(self) -> Dict[str, Any]:
        """Get A/B testing status"""
        
        try:
            active_tests = {}
            
            for test_name, config in self.ab_test_manager.active_tests.items():
                if config['status'] == 'active':
                    active_tests[test_name] = {
                        'control_version': config['control_version'],
                        'treatment_version': config['treatment_version'],
                        'traffic_split': config['traffic_split'],
                        'start_time': config['start_time'],
                        'end_time': config['end_time']
                    }
                    
            return {
                'active_tests': active_tests,
                'total_active': len(active_tests)
            }
        except Exception as e:
            logger.error(f"Failed to get A/B tests status: {e}")
            return {'error': str(e)}
            
    def _get_retraining_status(self) -> Dict[str, Any]:
        """Get retraining pipeline status"""
        
        try:
            triggers = self.retraining_pipeline.check_retraining_triggers()
            
            return {
                'should_retrain': triggers['should_retrain'],
                'reasons': triggers['reasons'],
                'last_training_age_hours': triggers['last_training_age_hours'],
                'performance_degraded': triggers['performance_degraded'],
                'drift_detected': triggers['drift_detected'],
                'next_check': (datetime.now() + timedelta(hours=1)).isoformat()  # Check every hour
            }
        except Exception as e:
            logger.error(f"Failed to get retraining status: {e}")
            return {'error': str(e)}
            
    def _get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        
        try:
            # Collect health indicators
            health_checks = {
                'model_registry': self._check_model_registry_health(),
                'feature_store': self._check_feature_store_health(),
                'monitoring': self._check_monitoring_health(),
                'alerts': self._check_alerts_health()
            }
            
            # Determine overall health
            failed_checks = [name for name, status in health_checks.items() if not status['healthy']]
            
            if len(failed_checks) == 0:
                overall_health = 'healthy'
            elif len(failed_checks) <= 1:
                overall_health = 'degraded'
            else:
                overall_health = 'unhealthy'
                
            return {
                'overall_status': overall_health,
                'components': health_checks,
                'failed_components': failed_checks,
                'last_check': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {'overall_status': 'error', 'error': str(e)}
            
    def _check_model_registry_health(self) -> Dict[str, Any]:
        """Check model registry health"""
        
        try:
            production_models = self.model_registry.list_model_versions("energy_optimizer", stage="production")
            has_production_model = len(production_models) > 0
            
            return {
                'healthy': has_production_model,
                'message': 'Production model deployed' if has_production_model else 'No production model',
                'details': {'production_models': len(production_models)}
            }
        except Exception as e:
            return {
                'healthy': False,
                'message': f'Model registry error: {str(e)}',
                'details': {'error': str(e)}
            }
            
    def _check_feature_store_health(self) -> Dict[str, Any]:
        """Check feature store health"""
        
        try:
            # Check if feature views are registered
            feature_store = self.retraining_pipeline.feature_store
            has_features = len(feature_store.feature_views) > 0
            
            return {
                'healthy': has_features,
                'message': 'Feature store operational' if has_features else 'No feature views registered',
                'details': {'feature_views': len(feature_store.feature_views)}
            }
        except Exception as e:
            return {
                'healthy': False,
                'message': f'Feature store error: {str(e)}',
                'details': {'error': str(e)}
            }
            
    def _check_monitoring_health(self) -> Dict[str, Any]:
        """Check monitoring system health"""
        
        try:
            # Check if we have recent predictions
            recent_predictions = len(self.monitor.recent_predictions)
            is_healthy = recent_predictions > 0
            
            return {
                'healthy': is_healthy,
                'message': 'Monitoring active' if is_healthy else 'No recent predictions',
                'details': {'recent_predictions': recent_predictions}
            }
        except Exception as e:
            return {
                'healthy': False,
                'message': f'Monitoring error: {str(e)}',
                'details': {'error': str(e)}
            }
            
    def _check_alerts_health(self) -> Dict[str, Any]:
        """Check alerting system health"""
        
        try:
            critical_alerts = len(self.alert_manager.get_active_alerts('critical'))
            is_healthy = critical_alerts == 0
            
            return {
                'healthy': is_healthy,
                'message': 'No critical alerts' if is_healthy else f'{critical_alerts} critical alerts active',
                'details': {'critical_alerts': critical_alerts}
            }
        except Exception as e:
            return {
                'healthy': False,
                'message': f'Alerting error: {str(e)}',
                'details': {'error': str(e)}
            }

# Function to monitor energy model in production
def monitor_energy_model():
    """Real-time ML monitoring function for energy optimization model"""
    
    dashboard = MonitoringDashboard()
    
    # Get performance and drift data
    performance_data = dashboard._get_performance_metrics()
    drift_data = dashboard._get_drift_status()
    
    # Check for alerts
    alerts = dashboard.alert_manager.check_alerts(performance_data, drift_data)
    
    # Log monitoring results
    metrics = {
        "prediction_accuracy": performance_data.get('mape', 100.0),
        "drift_score": drift_data.get('drift_score', 0.0),
        "latency_p95": performance_data.get('latency_p95_ms', 0.0),
        "daily_profit": 0.0,  # Would calculate from actual trading results
        "alerts_triggered": len(alerts)
    }
    
    logger.info(f"Energy model monitoring: {json.dumps(metrics, indent=2)}")
    
    # Trigger retraining if needed
    retraining_status = dashboard._get_retraining_status()
    if retraining_status.get('should_retrain', False):
        logger.warning("Model retraining recommended")
        # Could automatically trigger retraining here
        
    return {
        'timestamp': datetime.now().isoformat(),
        'metrics': metrics,
        'alerts': [alert.to_dict() for alert in alerts],
        'retraining_recommended': retraining_status.get('should_retrain', False)
    }

# Singleton dashboard instance
_dashboard_instance = None

def get_monitoring_dashboard() -> MonitoringDashboard:
    """Get global monitoring dashboard instance"""
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = MonitoringDashboard()
    return _dashboard_instance
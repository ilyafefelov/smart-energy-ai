"""
Phase 3: Real-time Model Monitoring Dashboard
Production monitoring with performance tracking, drift alerts, and model health
"""

import importlib.util
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys

from dataclasses import dataclass, asdict

from .retraining_pipeline import ModelMonitor, DriftDetector, get_retraining_pipeline, get_ab_test_manager
from .model_registry import get_model_registry

try:
    from energy_ml.mlops.monitoring_dashboard_support import (
        alert_to_dict,
        build_ab_tests_status,
        build_alerts_summary,
        build_dashboard_payload,
        build_drift_status,
        build_model_status,
        build_monitoring_metrics,
        build_monitoring_response,
        build_performance_metrics,
        build_retraining_status,
        build_system_health,
        check_threshold,
        default_alert_rule_specs,
        generate_alert_message,
        get_metric_value,
        load_alert_rules,
        log_alert,
        save_alert_rules,
    )
except ImportError:
    _SUPPORT_MODULE_NAME = "energy_ml.mlops.monitoring_dashboard_support"
    _SUPPORT_PATH = Path(__file__).with_name("monitoring_dashboard_support.py")
    _SUPPORT_SPEC = importlib.util.spec_from_file_location(_SUPPORT_MODULE_NAME, _SUPPORT_PATH)
    if _SUPPORT_SPEC is None or _SUPPORT_SPEC.loader is None:
        raise ImportError(f"Unable to load monitoring dashboard support module from {_SUPPORT_PATH}")
    _SUPPORT_MODULE = sys.modules.get(_SUPPORT_MODULE_NAME)
    if _SUPPORT_MODULE is None:
        _SUPPORT_MODULE = importlib.util.module_from_spec(_SUPPORT_SPEC)
        sys.modules[_SUPPORT_MODULE_NAME] = _SUPPORT_MODULE
        _SUPPORT_SPEC.loader.exec_module(_SUPPORT_MODULE)
    alert_to_dict = _SUPPORT_MODULE.alert_to_dict
    build_ab_tests_status = _SUPPORT_MODULE.build_ab_tests_status
    build_alerts_summary = _SUPPORT_MODULE.build_alerts_summary
    build_dashboard_payload = _SUPPORT_MODULE.build_dashboard_payload
    build_drift_status = _SUPPORT_MODULE.build_drift_status
    build_model_status = _SUPPORT_MODULE.build_model_status
    build_monitoring_metrics = _SUPPORT_MODULE.build_monitoring_metrics
    build_monitoring_response = _SUPPORT_MODULE.build_monitoring_response
    build_performance_metrics = _SUPPORT_MODULE.build_performance_metrics
    build_retraining_status = _SUPPORT_MODULE.build_retraining_status
    build_system_health = _SUPPORT_MODULE.build_system_health
    check_threshold = _SUPPORT_MODULE.check_threshold
    default_alert_rule_specs = _SUPPORT_MODULE.default_alert_rule_specs
    generate_alert_message = _SUPPORT_MODULE.generate_alert_message
    get_metric_value = _SUPPORT_MODULE.get_metric_value
    load_alert_rules = _SUPPORT_MODULE.load_alert_rules
    log_alert = _SUPPORT_MODULE.log_alert
    save_alert_rules = _SUPPORT_MODULE.save_alert_rules

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
        return alert_to_dict(self, asdict)

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
        for rule_data in default_alert_rule_specs():
            rule = AlertRule(**rule_data)
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
        return get_metric_value(metric, performance_data, drift_data)
            
    def _check_threshold(self, value: float, threshold: float, comparison: str) -> bool:
        """Check if value breaches threshold"""
        return check_threshold(value, threshold, comparison)
            
    def _find_existing_alert(self, rule_name: str) -> Optional[Alert]:
        """Find existing unacknowledged alert for rule"""
        
        for alert in self.active_alerts:
            if alert.rule_name == rule_name and not alert.acknowledged:
                return alert
        return None
        
    def _generate_alert_message(self, rule: AlertRule, current_value: float) -> str:
        """Generate human-readable alert message"""
        return generate_alert_message(rule.name, rule.metric, rule.threshold, current_value)
        
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
        log_alert(self.alerts_file, alert, logger, lambda current_alert: current_alert.to_dict())
        
    def _load_alert_rules(self) -> Dict[str, AlertRule]:
        """Load alert rules from file"""
        return load_alert_rules(self.rules_file, AlertRule, logger)
            
    def _save_alert_rules(self):
        """Save alert rules to file"""
        save_alert_rules(self.rules_file, self.alert_rules, asdict, logger)

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
        now = datetime.now()
        return build_dashboard_payload(
            timestamp=now,
            model_status=self._get_model_status(),
            performance_metrics=self._get_performance_metrics(),
            drift_status=self._get_drift_status(),
            alerts=self._get_alerts_summary(),
            ab_tests=self._get_ab_tests_status(),
            retraining_status=self._get_retraining_status(),
            system_health=self._get_system_health(),
        )
        
    def _get_model_status(self) -> Dict[str, Any]:
        """Get current model deployment status"""
        
        try:
            production_models = self.model_registry.list_model_versions("energy_optimizer", stage="production")
            staging_models = self.model_registry.list_model_versions("energy_optimizer", stage="staging")
            return build_model_status(production_models, staging_models)
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
            return build_performance_metrics(performance)
                
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {'error': str(e)}
            
    def _get_drift_status(self) -> Dict[str, Any]:
        """Get data drift status"""
        
        try:
            triggers = self.retraining_pipeline.check_retraining_triggers()
            return build_drift_status(triggers, datetime.now())
        except Exception as e:
            logger.error(f"Failed to get drift status: {e}")
            return {'error': str(e)}
            
    def _get_alerts_summary(self) -> Dict[str, Any]:
        """Get alerts summary"""
        
        try:
            return build_alerts_summary(self.alert_manager.get_active_alerts())
        except Exception as e:
            logger.error(f"Failed to get alerts summary: {e}")
            return {'error': str(e)}
            
    def _get_ab_tests_status(self) -> Dict[str, Any]:
        """Get A/B testing status"""
        
        try:
            return build_ab_tests_status(self.ab_test_manager.active_tests)
        except Exception as e:
            logger.error(f"Failed to get A/B tests status: {e}")
            return {'error': str(e)}
            
    def _get_retraining_status(self) -> Dict[str, Any]:
        """Get retraining pipeline status"""
        
        try:
            triggers = self.retraining_pipeline.check_retraining_triggers()
            return build_retraining_status(triggers, datetime.now() + timedelta(hours=1))
        except Exception as e:
            logger.error(f"Failed to get retraining status: {e}")
            return {'error': str(e)}
            
    def _get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        
        try:
            health_checks = {
                'model_registry': self._check_model_registry_health(),
                'feature_store': self._check_feature_store_health(),
                'monitoring': self._check_monitoring_health(),
                'alerts': self._check_alerts_health()
            }
            return build_system_health(health_checks, datetime.now())
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
    metrics = build_monitoring_metrics(performance_data, drift_data, len(alerts))
    
    logger.info(f"Energy model monitoring: {json.dumps(metrics, indent=2)}")
    
    # Trigger retraining if needed
    retraining_status = dashboard._get_retraining_status()
    if retraining_status.get('should_retrain', False):
        logger.warning("Model retraining recommended")
        # Could automatically trigger retraining here
        
    return build_monitoring_response(
        timestamp=datetime.now(),
        metrics=metrics,
        alerts=alerts,
        retraining_recommended=retraining_status.get('should_retrain', False),
        alert_to_dict_fn=lambda alert: alert.to_dict(),
    )

# Singleton dashboard instance
_dashboard_instance = None

def get_monitoring_dashboard() -> MonitoringDashboard:
    """Get global monitoring dashboard instance"""
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = MonitoringDashboard()
    return _dashboard_instance
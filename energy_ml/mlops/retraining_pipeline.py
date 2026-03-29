"""
Phase 3: Automated Retraining Pipeline
Production ML pipeline with drift monitoring, automated retraining, and A/B testing
"""

import importlib.util
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
from xgboost import XGBRegressor

from .model_registry import ModelRegistry, get_model_registry
from .feature_store import FeatureStore, get_feature_store

try:
    from energy_ml.mlops.retraining_pipeline_support import (
        analyze_ab_test_config,
        build_drift_report_payload,
        build_insufficient_drift_report,
        build_model_performance_payload,
        build_prediction_log,
        build_training_metrics,
        build_training_result,
        calculate_ks_drift,
        compute_feature_statistics,
        create_ab_test_config,
        dataclass_to_timestamped_dict,
        drift_feature_columns,
        evaluate_retraining_triggers,
        load_json_file,
        prepare_training_arrays,
        recent_drift_window,
        reference_drift_window,
        route_ab_prediction,
        save_json_file,
        training_feature_columns,
        trim_recent_predictions,
        update_ab_metrics,
    )
except ImportError:
    _SUPPORT_MODULE_NAME = "energy_ml.mlops.retraining_pipeline_support"
    _SUPPORT_PATH = Path(__file__).with_name("retraining_pipeline_support.py")
    _SUPPORT_SPEC = importlib.util.spec_from_file_location(_SUPPORT_MODULE_NAME, _SUPPORT_PATH)
    if _SUPPORT_SPEC is None or _SUPPORT_SPEC.loader is None:
        raise ImportError(f"Unable to load retraining support module from {_SUPPORT_PATH}")
    _SUPPORT_MODULE = sys.modules.get(_SUPPORT_MODULE_NAME)
    if _SUPPORT_MODULE is None:
        _SUPPORT_MODULE = importlib.util.module_from_spec(_SUPPORT_SPEC)
        sys.modules[_SUPPORT_MODULE_NAME] = _SUPPORT_MODULE
        _SUPPORT_SPEC.loader.exec_module(_SUPPORT_MODULE)
    analyze_ab_test_config = _SUPPORT_MODULE.analyze_ab_test_config
    build_drift_report_payload = _SUPPORT_MODULE.build_drift_report_payload
    build_insufficient_drift_report = _SUPPORT_MODULE.build_insufficient_drift_report
    build_model_performance_payload = _SUPPORT_MODULE.build_model_performance_payload
    build_prediction_log = _SUPPORT_MODULE.build_prediction_log
    build_training_metrics = _SUPPORT_MODULE.build_training_metrics
    build_training_result = _SUPPORT_MODULE.build_training_result
    calculate_ks_drift = _SUPPORT_MODULE.calculate_ks_drift
    compute_feature_statistics = _SUPPORT_MODULE.compute_feature_statistics
    create_ab_test_config = _SUPPORT_MODULE.create_ab_test_config
    dataclass_to_timestamped_dict = _SUPPORT_MODULE.dataclass_to_timestamped_dict
    drift_feature_columns = _SUPPORT_MODULE.drift_feature_columns
    evaluate_retraining_triggers = _SUPPORT_MODULE.evaluate_retraining_triggers
    load_json_file = _SUPPORT_MODULE.load_json_file
    prepare_training_arrays = _SUPPORT_MODULE.prepare_training_arrays
    recent_drift_window = _SUPPORT_MODULE.recent_drift_window
    reference_drift_window = _SUPPORT_MODULE.reference_drift_window
    route_ab_prediction = _SUPPORT_MODULE.route_ab_prediction
    save_json_file = _SUPPORT_MODULE.save_json_file
    training_feature_columns = _SUPPORT_MODULE.training_feature_columns
    trim_recent_predictions = _SUPPORT_MODULE.trim_recent_predictions
    update_ab_metrics = _SUPPORT_MODULE.update_ab_metrics

logger = logging.getLogger(__name__)

@dataclass
class DriftReport:
    """Data drift detection report"""
    timestamp: datetime
    drift_score: float
    drift_threshold: float
    is_drift_detected: bool
    feature_drifts: Dict[str, float]  # Per-feature drift scores
    sample_size: int
    reference_period: str
    detection_method: str
    
    def to_dict(self) -> Dict[str, Any]:
        return dataclass_to_timestamped_dict(self, asdict)

@dataclass
class ModelPerformance:
    """Model performance metrics"""
    timestamp: datetime
    model_version: str
    mape: float
    rmse: float
    mae: float
    r2_score: float
    prediction_count: int
    latency_p95_ms: float
    error_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        return dataclass_to_timestamped_dict(self, asdict)

class DriftDetector:
    """Statistical drift detection for energy features"""
    
    def __init__(self, sensitivity: float = 0.05):
        self.sensitivity = sensitivity  # P-value threshold for drift detection
        self.reference_data: Optional[pl.DataFrame] = None
        self.feature_statistics: Dict[str, Dict[str, float]] = {}
        
    def set_reference_data(self, reference_df: pl.DataFrame, feature_columns: List[str]):
        """Set reference data for drift detection"""
        self.reference_data = reference_df
        self.feature_statistics = compute_feature_statistics(reference_df, feature_columns)
                
        logger.info(f"Set reference data with {len(reference_df)} samples for {len(feature_columns)} features")
        
    def detect_drift(self, current_df: pl.DataFrame, feature_columns: List[str]) -> DriftReport:
        """Detect drift in current data compared to reference"""
        
        if self.reference_data is None:
            raise ValueError("Reference data not set. Call set_reference_data() first.")
            
        feature_drifts = {}
        overall_drift_score = 0.0
        
        for feature in feature_columns:
            if feature not in current_df.columns or feature not in self.feature_statistics:
                continue
                
            # Get current feature values
            current_values = current_df[feature].to_numpy()
            current_values = current_values[~np.isnan(current_values)]
            
            if len(current_values) == 0:
                continue
                
            # Calculate drift score using Kolmogorov-Smirnov test approximation
            drift_score = self._calculate_ks_drift(feature, current_values)
            feature_drifts[feature] = drift_score
            overall_drift_score = max(overall_drift_score, drift_score)
            
        return DriftReport(
            **build_drift_report_payload(
                timestamp=datetime.now(),
                overall_drift_score=overall_drift_score,
                sensitivity=self.sensitivity,
                feature_drifts=feature_drifts,
                sample_size=len(current_df),
                reference_sample_size=len(self.reference_data),
            )
        )
        
    def _calculate_ks_drift(self, feature: str, current_values: np.ndarray) -> float:
        """Calculate drift score using KS-test approximation"""
        return calculate_ks_drift(self.feature_statistics[feature], current_values)

class ModelMonitor:
    """Real-time model performance monitoring"""
    
    def __init__(self, monitor_path: str = "energy_ml/mlops/monitoring"):
        self.monitor_path = Path(monitor_path)
        self.monitor_path.mkdir(parents=True, exist_ok=True)
        
        self.performance_log_path = self.monitor_path / "performance.jsonl"
        self.drift_log_path = self.monitor_path / "drift.jsonl"
        
        # Performance tracking
        self.recent_predictions: List[Dict[str, Any]] = []
        self.performance_window_size = 1000  # Keep last 1000 predictions
        
    def log_prediction(self, 
                      model_version: str,
                      features: Dict[str, Any],
                      prediction: float,
                      actual: Optional[float] = None,
                      latency_ms: Optional[float] = None):
        """Log model prediction for performance tracking"""
        
        prediction_log = {
            **build_prediction_log(datetime.now(), model_version, features, prediction, actual, latency_ms)
        }
        
        self.recent_predictions.append(prediction_log)
        self.recent_predictions = trim_recent_predictions(self.recent_predictions, self.performance_window_size)
            
    def calculate_performance_metrics(self, model_version: str) -> Optional[ModelPerformance]:
        """Calculate performance metrics for model version"""
        
        # Filter predictions for this model version with actual values
        model_predictions = [
            p for p in self.recent_predictions 
            if p['model_version'] == model_version and p['actual'] is not None
        ]
        
        if len(model_predictions) < 10:  # Need minimum samples
            return None
            
        payload = build_model_performance_payload(model_version, model_predictions, datetime.now())
        if payload is None:
            return None
        performance = ModelPerformance(**payload)
        
        # Log performance
        self._log_performance(performance)
        
        return performance
        
    def _log_performance(self, performance: ModelPerformance):
        """Log performance metrics to file"""
        with open(self.performance_log_path, 'a') as f:
            f.write(json.dumps(performance.to_dict()) + '\n')

class RetrainingPipeline:
    """Automated model retraining pipeline"""
    
    def __init__(self, 
                 model_registry: Optional[ModelRegistry] = None,
                 feature_store: Optional[FeatureStore] = None,
                 monitor: Optional[ModelMonitor] = None):
        self.model_registry = model_registry or get_model_registry()
        self.feature_store = feature_store or get_feature_store()
        self.monitor = monitor or ModelMonitor()
        
        self.drift_detector = DriftDetector()
        
        # Retraining thresholds
        self.performance_threshold_mape = 12.0  # Retrain if MAPE > 12%
        self.drift_threshold = 0.95  # Retrain if drift score > 0.95
        self.min_retraining_interval_hours = 24  # Don't retrain more than once per day
        
        # Load reference data for drift detection
        self._initialize_drift_detection()
        
    def check_retraining_triggers(self) -> Dict[str, Any]:
        """Check if model retraining should be triggered"""
        production_versions = self.model_registry.list_model_versions("energy_optimizer", stage="production")
        current_version = production_versions[0] if production_versions else None
        performance = self.monitor.calculate_performance_metrics(current_version.version_id) if current_version else None
        drift_report = self._check_data_drift() if current_version else None
        return evaluate_retraining_triggers(
            production_versions,
            performance,
            drift_report,
            self.performance_threshold_mape,
            self.min_retraining_interval_hours,
            datetime.now(),
        )
        
    def trigger_retraining(self, reason: str = "Manual trigger") -> Dict[str, Any]:
        """Trigger automated model retraining"""
        
        logger.info(f"Starting model retraining: {reason}")
        
        training_result = build_training_result(reason, datetime.now())
        
        try:
            # Get training data
            end_time = datetime.now()
            start_time = end_time - timedelta(days=30)  # Last 30 days
            
            training_data = self.feature_store.load_batch_features(
                "energy_features",
                start_time,
                end_time
            )
            
            if len(training_data) < 100:
                raise ValueError(f"Insufficient training data: {len(training_data)} samples")
                
            feature_columns = training_feature_columns()
            X_train, X_test, y_train, y_test = prepare_training_arrays(training_data, feature_columns)
            
            # Train new model
            model = XGBRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1
            )
            
            logger.info(f"Training new model on {len(X_train)} samples")
            model.fit(X_train, y_train)
            
            # Evaluate model
            y_pred_train = model.predict(X_train)
            y_pred_test = model.predict(X_test)
            
            train_mape = mean_absolute_percentage_error(y_train, y_pred_train) * 100
            test_mape = mean_absolute_percentage_error(y_test, y_pred_test) * 100
            
            metrics = build_training_metrics(y_train, y_pred_train, y_test, y_pred_test, len(X_train), len(X_test))
            
            training_result['metrics'] = metrics
            
            # Register new model version
            new_version = self.model_registry.register_model(
                model=model,
                model_name="energy_optimizer",
                algorithm="xgboost",
                performance_metrics=metrics,
                feature_schema=feature_columns,
                validation_data={'X': X_test, 'y': y_test}
            )
            
            training_result['new_model_version'] = new_version.version_id
            
            # Auto-promote to staging if performance is good
            if test_mape < 10.0:  # Good performance threshold
                self.model_registry.promote_to_staging(new_version.version_id)
                logger.info(f"Auto-promoted model {new_version.version_id} to staging")
                
                # Auto-deploy to production if significantly better than current
                production_versions = self.model_registry.list_model_versions("energy_optimizer", stage="production")
                if not production_versions or test_mape < production_versions[0].performance_metrics.get('test_mape', 100.0) - 2.0:
                    self.model_registry.deploy_to_production(new_version.version_id, canary_percentage=20.0)
                    logger.info(f"Auto-deployed model {new_version.version_id} to production (canary 20%)")
                    
            training_result['success'] = True
            logger.info(f"Model retraining completed: {new_version.version_id} (Test MAPE: {test_mape:.2f}%)")
            
        except Exception as e:
            error_msg = f"Model retraining failed: {str(e)}"
            logger.error(error_msg)
            training_result['error'] = error_msg
            
        finally:
            training_result['completed_at'] = datetime.now().isoformat()
            
        return training_result
        
    def _check_data_drift(self) -> DriftReport:
        """Check for data drift in recent data"""
        
        start_time, end_time = recent_drift_window(datetime.now())
        
        recent_data = self.feature_store.load_batch_features(
            "energy_features",
            start_time,
            end_time
        )
        
        if len(recent_data) < 50:
            return DriftReport(**build_insufficient_drift_report(datetime.now(), self.drift_threshold, len(recent_data)))
        return self.drift_detector.detect_drift(recent_data, drift_feature_columns())
        
    def _initialize_drift_detection(self):
        """Initialize drift detection with reference data"""
        
        try:
            start_time, end_time = reference_drift_window(datetime.now())
            reference_data = self.feature_store.load_batch_features(
                "energy_features",
                start_time,
                end_time
            )
            
            if len(reference_data) > 100:
                self.drift_detector.set_reference_data(reference_data, drift_feature_columns())
                logger.info("Initialized drift detection with reference data")
            else:
                logger.warning("Insufficient reference data for drift detection")
                
        except Exception as e:
            logger.warning(f"Failed to initialize drift detection: {e}")

class ABTestManager:
    """A/B testing manager for model deployment"""
    
    def __init__(self, ab_config_path: str = "energy_ml/mlops/ab_tests.json"):
        self.ab_config_path = Path(ab_config_path)
        self.ab_config_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.active_tests = self._load_ab_config()
        
    def create_ab_test(self, 
                      test_name: str,
                      control_version: str,
                      treatment_version: str,
                      traffic_split: float = 0.5,
                      duration_hours: int = 168) -> Dict[str, Any]:  # Default 1 week
        """Create new A/B test between model versions"""
        test_config = create_ab_test_config(
            test_name,
            control_version,
            treatment_version,
            traffic_split,
            duration_hours,
            datetime.now(),
        )
        
        self.active_tests[test_name] = test_config
        self._save_ab_config()
        
        logger.info(f"Created A/B test: {test_name} ({traffic_split*100:.1f}% traffic to treatment)")
        return test_config
        
    def route_prediction(self, user_id: str = "default") -> str:
        """Route prediction request to appropriate model version"""
        return route_ab_prediction(self.active_tests, user_id, datetime.now())
        
    def log_ab_result(self, 
                     test_name: str,
                     version: str,
                     prediction: float,
                     actual: Optional[float] = None,
                     error: bool = False):
        """Log A/B test result"""
        
        if test_name not in self.active_tests:
            return
            
        config = self.active_tests[test_name]
        if not update_ab_metrics(config, version, prediction, actual, error):
            return
            
        self._save_ab_config()
        
    def analyze_ab_test(self, test_name: str) -> Dict[str, Any]:
        """Analyze A/B test results"""
        
        if test_name not in self.active_tests:
            raise ValueError(f"A/B test not found: {test_name}")
        return analyze_ab_test_config(test_name, self.active_tests[test_name])
        
    def _load_ab_config(self) -> Dict[str, Dict[str, Any]]:
        """Load A/B test configuration from disk"""
        return load_json_file(self.ab_config_path, logger, "A/B config")
            
    def _save_ab_config(self):
        """Save A/B test configuration to disk"""
        save_json_file(self.ab_config_path, self.active_tests, logger, "A/B config")

# Singleton instances for global access
_retraining_pipeline_instance = None
_ab_test_manager_instance = None

def get_retraining_pipeline() -> RetrainingPipeline:
    """Get global retraining pipeline instance"""
    global _retraining_pipeline_instance
    if _retraining_pipeline_instance is None:
        _retraining_pipeline_instance = RetrainingPipeline()
    return _retraining_pipeline_instance

def get_ab_test_manager() -> ABTestManager:
    """Get global A/B test manager instance"""
    global _ab_test_manager_instance
    if _ab_test_manager_instance is None:
        _ab_test_manager_instance = ABTestManager()
    return _ab_test_manager_instance
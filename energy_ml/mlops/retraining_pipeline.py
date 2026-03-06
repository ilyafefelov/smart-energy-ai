"""
Phase 3: Automated Retraining Pipeline
Production ML pipeline with drift monitoring, automated retraining, and A/B testing
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import pickle

import numpy as np
import polars as pl
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor
import joblib

from .model_registry import ModelRegistry, get_model_registry
from .feature_store import FeatureStore, get_feature_store

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
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat()
        }

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
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat()
        }

class DriftDetector:
    """Statistical drift detection for energy features"""
    
    def __init__(self, sensitivity: float = 0.05):
        self.sensitivity = sensitivity  # P-value threshold for drift detection
        self.reference_data: Optional[pl.DataFrame] = None
        self.feature_statistics: Dict[str, Dict[str, float]] = {}
        
    def set_reference_data(self, reference_df: pl.DataFrame, feature_columns: List[str]):
        """Set reference data for drift detection"""
        self.reference_data = reference_df
        
        # Calculate reference statistics for each feature
        for feature in feature_columns:
            if feature in reference_df.columns:
                values = reference_df[feature].to_numpy()
                values = values[~np.isnan(values)]  # Remove NaNs
                
                self.feature_statistics[feature] = {
                    'mean': float(np.mean(values)),
                    'std': float(np.std(values)),
                    'min': float(np.min(values)),
                    'max': float(np.max(values)),
                    'median': float(np.median(values))
                }
                
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
            
        # Determine if drift is detected
        is_drift_detected = overall_drift_score > (1.0 - self.sensitivity)
        
        return DriftReport(
            timestamp=datetime.now(),
            drift_score=overall_drift_score,
            drift_threshold=1.0 - self.sensitivity,
            is_drift_detected=is_drift_detected,
            feature_drifts=feature_drifts,
            sample_size=len(current_df),
            reference_period=f"{len(self.reference_data)} samples",
            detection_method="KS-approximation"
        )
        
    def _calculate_ks_drift(self, feature: str, current_values: np.ndarray) -> float:
        """Calculate drift score using KS-test approximation"""
        
        ref_stats = self.feature_statistics[feature]
        
        # Simple statistical comparison (approximates KS test)
        current_mean = np.mean(current_values)
        current_std = np.std(current_values)
        
        # Normalized difference in means
        mean_diff = abs(current_mean - ref_stats['mean']) / max(ref_stats['std'], 0.001)
        
        # Difference in standard deviations
        std_ratio = current_std / max(ref_stats['std'], 0.001)
        std_diff = abs(1.0 - std_ratio)
        
        # Combined drift score (0 = no drift, 1 = maximum drift)
        drift_score = min(1.0, (mean_diff * 0.7 + std_diff * 0.3) / 3.0)
        
        return drift_score

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
            'timestamp': datetime.now().isoformat(),
            'model_version': model_version,
            'prediction': prediction,
            'actual': actual,
            'latency_ms': latency_ms,
            'features': features
        }
        
        self.recent_predictions.append(prediction_log)
        
        # Keep only recent predictions
        if len(self.recent_predictions) > self.performance_window_size:
            self.recent_predictions = self.recent_predictions[-self.performance_window_size:]
            
    def calculate_performance_metrics(self, model_version: str) -> Optional[ModelPerformance]:
        """Calculate performance metrics for model version"""
        
        # Filter predictions for this model version with actual values
        model_predictions = [
            p for p in self.recent_predictions 
            if p['model_version'] == model_version and p['actual'] is not None
        ]
        
        if len(model_predictions) < 10:  # Need minimum samples
            return None
            
        # Extract predictions and actuals
        predictions = [p['prediction'] for p in model_predictions]
        actuals = [p['actual'] for p in model_predictions]
        
        # Calculate metrics
        mape = mean_absolute_percentage_error(actuals, predictions) * 100
        rmse = np.sqrt(mean_squared_error(actuals, predictions))
        mae = np.mean(np.abs(np.array(predictions) - np.array(actuals)))
        
        # R² score
        ss_res = np.sum((np.array(actuals) - np.array(predictions)) ** 2)
        ss_tot = np.sum((np.array(actuals) - np.mean(actuals)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        
        # Latency metrics
        latencies = [p['latency_ms'] for p in model_predictions if p['latency_ms'] is not None]
        latency_p95 = np.percentile(latencies, 95) if latencies else 0.0
        
        # Error rate (predictions with errors > 20% MAPE)
        errors = [abs(p - a) / max(abs(a), 0.001) > 0.2 for p, a in zip(predictions, actuals)]
        error_rate = np.mean(errors) * 100
        
        performance = ModelPerformance(
            timestamp=datetime.now(),
            model_version=model_version,
            mape=mape,
            rmse=rmse,
            mae=mae,
            r2_score=r2,
            prediction_count=len(model_predictions),
            latency_p95_ms=latency_p95,
            error_rate=error_rate
        )
        
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
        
        triggers = {
            'should_retrain': False,
            'reasons': [],
            'performance_degraded': False,
            'drift_detected': False,
            'last_training_age_hours': 0
        }
        
        # Get current production model
        production_versions = self.model_registry.list_model_versions("energy_optimizer", stage="production")
        if not production_versions:
            triggers['should_retrain'] = True
            triggers['reasons'].append("No production model found")
            return triggers
            
        current_version = production_versions[0]
        
        # Check model age
        age = datetime.now() - current_version.created_at
        triggers['last_training_age_hours'] = age.total_seconds() / 3600
        
        if age < timedelta(hours=self.min_retraining_interval_hours):
            logger.info(f"Model too recent for retraining: {age}")
            return triggers
            
        # Check performance degradation
        performance = self.monitor.calculate_performance_metrics(current_version.version_id)
        if performance and performance.mape > self.performance_threshold_mape:
            triggers['should_retrain'] = True
            triggers['performance_degraded'] = True
            triggers['reasons'].append(f"Performance degraded: MAPE {performance.mape:.1f}% > {self.performance_threshold_mape}%")
            
        # Check data drift
        drift_report = self._check_data_drift()
        if drift_report.is_drift_detected:
            triggers['should_retrain'] = True
            triggers['drift_detected'] = True
            triggers['reasons'].append(f"Data drift detected: score {drift_report.drift_score:.3f}")
            
        return triggers
        
    def trigger_retraining(self, reason: str = "Manual trigger") -> Dict[str, Any]:
        """Trigger automated model retraining"""
        
        logger.info(f"Starting model retraining: {reason}")
        
        training_result = {
            'started_at': datetime.now().isoformat(),
            'reason': reason,
            'success': False,
            'new_model_version': None,
            'metrics': {},
            'error': None
        }
        
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
                
            # Prepare training data
            feature_columns = [
                'battery_soc', 'grid_price_uah_kwh', 'solar_generation_kw', 
                'load_demand_kw', 'temperature_celsius', 'is_peak_hour',
                'day_of_week', 'hour_of_day', 'price_ma_24h', 'load_ma_7d'
            ]
            
            # Create target variable (next hour price for prediction)
            training_data = training_data.sort('timestamp')
            training_data = training_data.with_columns(
                pl.col('grid_price_uah_kwh').shift(-1).alias('target_price')
            ).drop_nulls()
            
            # Extract features and targets
            X = training_data.select(feature_columns).to_numpy()
            y = training_data['target_price'].to_numpy()
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, shuffle=False  # Time series: no shuffling
            )
            
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
            
            metrics = {
                'train_mape': train_mape,
                'test_mape': test_mape,
                'train_rmse': np.sqrt(mean_squared_error(y_train, y_pred_train)),
                'test_rmse': np.sqrt(mean_squared_error(y_test, y_pred_test)),
                'training_samples': len(X_train),
                'test_samples': len(X_test)
            }
            
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
        
        # Get recent data (last 7 days)
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        
        recent_data = self.feature_store.load_batch_features(
            "energy_features",
            start_time,
            end_time
        )
        
        if len(recent_data) < 50:
            # Not enough data for drift detection
            return DriftReport(
                timestamp=datetime.now(),
                drift_score=0.0,
                drift_threshold=self.drift_threshold,
                is_drift_detected=False,
                feature_drifts={},
                sample_size=len(recent_data),
                reference_period="insufficient data",
                detection_method="skipped"
            )
            
        feature_columns = [
            'battery_soc', 'grid_price_uah_kwh', 'solar_generation_kw', 
            'load_demand_kw', 'temperature_celsius'
        ]
        
        return self.drift_detector.detect_drift(recent_data, feature_columns)
        
    def _initialize_drift_detection(self):
        """Initialize drift detection with reference data"""
        
        try:
            # Get reference data (30-60 days ago to avoid recent changes)
            end_time = datetime.now() - timedelta(days=30)
            start_time = end_time - timedelta(days=30)
            
            reference_data = self.feature_store.load_batch_features(
                "energy_features",
                start_time,
                end_time
            )
            
            if len(reference_data) > 100:
                feature_columns = [
                    'battery_soc', 'grid_price_uah_kwh', 'solar_generation_kw', 
                    'load_demand_kw', 'temperature_celsius'
                ]
                
                self.drift_detector.set_reference_data(reference_data, feature_columns)
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
        
        test_config = {
            'test_name': test_name,
            'control_version': control_version,
            'treatment_version': treatment_version,
            'traffic_split': traffic_split,
            'start_time': datetime.now().isoformat(),
            'end_time': (datetime.now() + timedelta(hours=duration_hours)).isoformat(),
            'status': 'active',
            'metrics': {
                'control': {'predictions': 0, 'errors': 0, 'total_mape': 0.0},
                'treatment': {'predictions': 0, 'errors': 0, 'total_mape': 0.0}
            }
        }
        
        self.active_tests[test_name] = test_config
        self._save_ab_config()
        
        logger.info(f"Created A/B test: {test_name} ({traffic_split*100:.1f}% traffic to treatment)")
        return test_config
        
    def route_prediction(self, user_id: str = "default") -> str:
        """Route prediction request to appropriate model version"""
        
        for test_name, config in self.active_tests.items():
            if config['status'] != 'active':
                continue
                
            # Check if test is still active
            end_time = datetime.fromisoformat(config['end_time'])
            if datetime.now() > end_time:
                config['status'] = 'completed'
                continue
                
            # Simple hash-based routing for consistent assignment
            user_hash = int(hashlib.md5(f"{user_id}_{test_name}".encode()).hexdigest(), 16)
            
            if (user_hash % 100) < (config['traffic_split'] * 100):
                return config['treatment_version']
            else:
                return config['control_version']
                
        # Default to production model if no active tests
        return "production"
        
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
        
        # Determine which group (control or treatment)
        if version == config['control_version']:
            group = 'control'
        elif version == config['treatment_version']:
            group = 'treatment'
        else:
            return
            
        # Update metrics
        metrics = config['metrics'][group]
        metrics['predictions'] += 1
        
        if error:
            metrics['errors'] += 1
            
        if actual is not None:
            mape = abs(prediction - actual) / max(abs(actual), 0.001)
            metrics['total_mape'] += mape
            
        self._save_ab_config()
        
    def analyze_ab_test(self, test_name: str) -> Dict[str, Any]:
        """Analyze A/B test results"""
        
        if test_name not in self.active_tests:
            raise ValueError(f"A/B test not found: {test_name}")
            
        config = self.active_tests[test_name]
        control_metrics = config['metrics']['control']
        treatment_metrics = config['metrics']['treatment']
        
        # Calculate performance metrics
        control_error_rate = control_metrics['errors'] / max(control_metrics['predictions'], 1)
        treatment_error_rate = treatment_metrics['errors'] / max(treatment_metrics['predictions'], 1)
        
        control_avg_mape = control_metrics['total_mape'] / max(control_metrics['predictions'], 1) * 100
        treatment_avg_mape = treatment_metrics['total_mape'] / max(treatment_metrics['predictions'], 1) * 100
        
        # Statistical significance (simplified)
        sample_size_adequate = min(control_metrics['predictions'], treatment_metrics['predictions']) >= 100
        
        # Winner determination
        winner = None
        if sample_size_adequate:
            if treatment_avg_mape < control_avg_mape * 0.95:  # 5% improvement threshold
                winner = 'treatment'
            elif control_avg_mape < treatment_avg_mape * 0.95:
                winner = 'control'
                
        analysis = {
            'test_name': test_name,
            'status': config['status'],
            'sample_size_adequate': sample_size_adequate,
            'winner': winner,
            'control': {
                'version': config['control_version'],
                'predictions': control_metrics['predictions'],
                'error_rate': control_error_rate * 100,
                'avg_mape': control_avg_mape
            },
            'treatment': {
                'version': config['treatment_version'],
                'predictions': treatment_metrics['predictions'],
                'error_rate': treatment_error_rate * 100,
                'avg_mape': treatment_avg_mape
            },
            'improvement': {
                'mape_improvement_percent': ((control_avg_mape - treatment_avg_mape) / control_avg_mape) * 100 if control_avg_mape > 0 else 0,
                'error_rate_improvement_percent': ((control_error_rate - treatment_error_rate) / control_error_rate) * 100 if control_error_rate > 0 else 0
            }
        }
        
        return analysis
        
    def _load_ab_config(self) -> Dict[str, Dict[str, Any]]:
        """Load A/B test configuration from disk"""
        if not self.ab_config_path.exists():
            return {}
            
        try:
            with open(self.ab_config_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load A/B config: {e}")
            return {}
            
    def _save_ab_config(self):
        """Save A/B test configuration to disk"""
        try:
            with open(self.ab_config_path, 'w') as f:
                json.dump(self.active_tests, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save A/B config: {e}")

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
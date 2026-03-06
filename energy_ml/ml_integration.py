"""Phase 4F: ML Integration - MLflow Model Loading and Prediction Service.

Integrates MLflow model for energy trading recommendations.
"""
import importlib.util
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import polars as pl

try:
    from energy_ml.ml_integration_support import (
        build_error_response,
        build_mock_prediction,
        build_model_info,
        build_prediction_response,
        generate_reasoning_text,
        get_feature_importance_map,
        parse_prediction_result,
        validate_feature_frame,
    )
except ImportError:
    _SUPPORT_MODULE_NAME = "energy_ml.ml_integration_support"
    _SUPPORT_PATH = Path(__file__).with_name("ml_integration_support.py")
    _SUPPORT_SPEC = importlib.util.spec_from_file_location(_SUPPORT_MODULE_NAME, _SUPPORT_PATH)
    if _SUPPORT_SPEC is None or _SUPPORT_SPEC.loader is None:
        raise ImportError(f"Unable to load ml integration support module from {_SUPPORT_PATH}")
    _SUPPORT_MODULE = sys.modules.get(_SUPPORT_MODULE_NAME)
    if _SUPPORT_MODULE is None:
        _SUPPORT_MODULE = importlib.util.module_from_spec(_SUPPORT_SPEC)
        sys.modules[_SUPPORT_MODULE_NAME] = _SUPPORT_MODULE
        _SUPPORT_SPEC.loader.exec_module(_SUPPORT_MODULE)
    build_error_response = _SUPPORT_MODULE.build_error_response
    build_mock_prediction = _SUPPORT_MODULE.build_mock_prediction
    build_model_info = _SUPPORT_MODULE.build_model_info
    build_prediction_response = _SUPPORT_MODULE.build_prediction_response
    generate_reasoning_text = _SUPPORT_MODULE.generate_reasoning_text
    get_feature_importance_map = _SUPPORT_MODULE.get_feature_importance_map
    parse_prediction_result = _SUPPORT_MODULE.parse_prediction_result
    validate_feature_frame = _SUPPORT_MODULE.validate_feature_frame

try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    logging.warning("MLflow not available. PredictionService will operate in mock mode.")


logger = logging.getLogger(__name__)


class PredictionService:
    """Load MLflow model and generate predictions.
    
    Handles:
    - MLflow model loading and caching
    - Feature validation
    - Prediction generation
    - Confidence scoring
    - Reasoning generation
    """
    
    # Expected features matching FeatureEngineer output
    EXPECTED_FEATURES = [
        'hour_of_day', 'day_of_week', 'is_peak_hour', 'season',
        'current_tariff_uah_mwh', 'price_trend', 'price_volatility',
        'soc_percent', 'battery_health', 'degradation_cost_uah_kwh',
        'battery_cycles_remaining',
        'current_load_kw', 'load_forecast_1h', 'load_trend'
    ]
    
    # Valid action classes
    VALID_ACTIONS = ['BUY', 'SELL', 'HOLD']
    
    def __init__(self, model_uri: Optional[str] = None):
        """Initialize prediction service with MLflow model.
        
        Args:
            model_uri: MLflow model URI (e.g., 'models:/battery-optimizer/production')
                      If None, uses latest registered model.
        """
        self.model_uri = model_uri
        self.model = None
        self.model_info = None
        self.model_version = "mock-v1"
        self._mock_mode = not MLFLOW_AVAILABLE
        
        if MLFLOW_AVAILABLE:
            self._load_model()
    
    def _load_model(self):
        """Load MLflow model.
        
        Handles missing models gracefully by falling back to mock mode.
        """
        try:
            if self.model_uri is None:
                # Load latest registered model
                # For now, just use mock since real model may not exist
                logger.info("No model URI provided. Using mock prediction service.")
                self._mock_mode = True
                return
            
            self.model = mlflow.pyfunc.load_model(self.model_uri)
            self._mock_mode = False
            logger.info(f"Loaded MLflow model: {self.model_uri}")
            
            # Try to get model metadata
            try:
                self.model_info = mlflow.models.get_model(self.model_uri)
                self.model_version = self.model_info.version if hasattr(self.model_info, 'version') else "unknown"
            except Exception as e:
                logger.warning(f"Could not retrieve model metadata: {e}")
                self.model_version = "unknown"
        
        except Exception as e:
            logger.warning(f"Failed to load MLflow model: {e}. Using mock prediction service.")
            self._mock_mode = True
    
    def predict(self, features: pl.DataFrame) -> Dict[str, any]:
        """Generate ML prediction from features.
        
        Args:
            features: polars DataFrame with 14 features (from FeatureEngineer)
        
        Returns:
            dict with keys:
            - action: str ('BUY', 'SELL', 'HOLD')
            - confidence: float (0.0-1.0)
            - reasoning: str (explanation)
            - model_version: str (model identifier)
            - timestamp: str (ISO 8601)
            - feature_importance: dict (top features and importance)
        """
        # Validate features
        is_valid, errors = self.validate_features(features)
        if not is_valid:
            return self._error_response(f"Feature validation failed: {errors}")
        
        if self._mock_mode:
            return self._mock_predict(features)
        
        try:
            feature_array = features[self.EXPECTED_FEATURES].to_numpy()
            prediction = self.model.predict(feature_array)
            action, confidence = self._parse_prediction(prediction)
            reasoning = self._generate_reasoning(action, features, confidence)
            return build_prediction_response(
                action,
                confidence,
                reasoning,
                self.model_version,
                self._get_feature_importance(features),
            )
        
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return self._error_response(str(e))
    
    def _mock_predict(self, features: pl.DataFrame) -> Dict[str, any]:
        """Generate mock prediction (when model unavailable).
        
        Uses simple heuristic rules based on features.
        """
        return build_mock_prediction(features, self.model_version)
    
    def _parse_prediction(self, prediction) -> Tuple[str, float]:
        """Parse model output into action and confidence.
        
        Args:
            prediction: Model output (array-like)
        
        Returns:
            Tuple of (action, confidence)
        """
        return parse_prediction_result(prediction, self.VALID_ACTIONS)
    
    def _generate_reasoning(self, 
                           action: str,
                           features: pl.DataFrame,
                           confidence: float) -> str:
        """Generate natural language reasoning for prediction.
        
        Args:
            action: Predicted action
            features: Input features
            confidence: Confidence score
        
        Returns:
            Reasoning string
        """
        return generate_reasoning_text(action, features, confidence)
    
    def _get_feature_importance(self, features: pl.DataFrame) -> Dict[str, float]:
        """Get feature importance scores.
        
        Args:
            features: Input features
        
        Returns:
            Dict of feature importance scores
        """
        return get_feature_importance_map(features)
    
    def validate_features(self, features: pl.DataFrame) -> Tuple[bool, List[str]]:
        """Validate feature DataFrame matches model schema.
        
        Args:
            features: Input features DataFrame
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        return validate_feature_frame(features, self.EXPECTED_FEATURES)
    
    def _error_response(self, error_msg: str) -> Dict[str, any]:
        """Generate error response.
        
        Args:
            error_msg: Error message
        
        Returns:
            Error response dict (defaults to HOLD)
        """
        logger.error(f"Prediction error: {error_msg}")
        return build_error_response(error_msg, self.model_version)
    
    def get_model_info(self) -> Dict[str, any]:
        """Return loaded model metadata.
        
        Returns:
            Dict with model information
        """
        return build_model_info(
            self.model_uri,
            self.model_version,
            self._mock_mode,
            MLFLOW_AVAILABLE,
            self.EXPECTED_FEATURES,
            self.VALID_ACTIONS,
        )
    
    def generate_prediction(self, features: pl.DataFrame, user_strategy: str = "balanced") -> Dict[str, Any]:
        """Generate ML prediction with user optimization strategy.
        
        Args:
            features: Input features DataFrame
            user_strategy: User optimization strategy
            
        Returns:
            Optimized prediction dict
        """
        # Get base prediction
        base_prediction = self.predict(features)
        
        # Apply user optimization preferences if available
        try:
            from energy_ml.mlops.optimization_engine import OptimizationEngine
            optimization_engine = OptimizationEngine()
            
            # Mock user config for optimization
            from energy_ml.user_config import ConfigurationManager
            config_manager = ConfigurationManager()
            config = config_manager.load_config_or_raise()
            
            # Set strategy in config
            setattr(config, 'optimization_strategy', user_strategy)
            
            # Get user preferences
            user_preferences = optimization_engine.get_user_strategy(config)
            
            # Apply optimization
            optimized_prediction = optimization_engine.optimize_decision(
                base_prediction, 
                user_strategy,
                weights=user_preferences.get('weights', {})
            )
            
            return optimized_prediction
            
        except Exception as e:
            logger.warning(f"Optimization failed, returning base prediction: {e}")
            return base_prediction

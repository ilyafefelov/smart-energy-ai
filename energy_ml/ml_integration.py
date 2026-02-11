"""Phase 4F: ML Integration - MLflow Model Loading and Prediction Service.

Integrates MLflow model for energy trading recommendations.
"""
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple, List
import json

import polars as pl

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
            # Prepare feature array for model
            feature_array = features[self.EXPECTED_FEATURES].to_numpy()
            
            # Get model prediction
            prediction = self.model.predict(feature_array)
            
            # Parse prediction
            action, confidence = self._parse_prediction(prediction)
            reasoning = self._generate_reasoning(action, features, confidence)
            
            return {
                'action': action,
                'confidence': confidence,
                'reasoning': reasoning,
                'model_version': self.model_version,
                'timestamp': datetime.now().isoformat(),
                'feature_importance': self._get_feature_importance(features),
            }
        
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return self._error_response(str(e))
    
    def _mock_predict(self, features: pl.DataFrame) -> Dict[str, any]:
        """Generate mock prediction (when model unavailable).
        
        Uses simple heuristic rules based on features.
        """
        feature_dict = features.to_dicts()[0]
        
        soc = feature_dict.get('soc_percent', 0.5)
        tariff = feature_dict.get('current_tariff_uah_mwh', 0.5)
        is_peak = feature_dict.get('is_peak_hour', 0.0)
        health = feature_dict.get('battery_health', 0.8)
        
        # Simple decision logic
        if health < 0.2:
            action = 'HOLD'
            confidence = 0.95
        elif is_peak > 0.5 and soc > 0.3:
            action = 'SELL'
            confidence = 0.75 + (soc - 0.3) * 0.2
        elif is_peak < 0.5 and soc < 0.8 and tariff < 0.5:
            action = 'BUY'
            confidence = 0.70 + (0.8 - soc) * 0.15
        else:
            action = 'HOLD'
            confidence = 0.65
        
        reasoning = f"Mock prediction: {action} (battery SOC: {soc:.0%}, tariff: {tariff:.0%})"
        
        return {
            'action': action,
            'confidence': min(1.0, max(0.0, confidence)),
            'reasoning': reasoning,
            'model_version': self.model_version,
            'timestamp': datetime.now().isoformat(),
            'feature_importance': self._get_feature_importance(features),
        }
    
    def _parse_prediction(self, prediction) -> Tuple[str, float]:
        """Parse model output into action and confidence.
        
        Args:
            prediction: Model output (array-like)
        
        Returns:
            Tuple of (action, confidence)
        """
        # Handle different prediction formats
        if isinstance(prediction, (list, tuple)):
            if len(prediction) > 0:
                # Assume first element is action (0=BUY, 1=SELL, 2=HOLD)
                action_idx = int(prediction[0])
                confidence = prediction[1] if len(prediction) > 1 else 0.5
            else:
                return 'HOLD', 0.5
        else:
            # Single value - assume probabilities
            action_idx = 1  # Default HOLD
            confidence = 0.5
        
        action = self.VALID_ACTIONS[action_idx % len(self.VALID_ACTIONS)]
        confidence = max(0.0, min(1.0, float(confidence)))
        
        return action, confidence
    
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
        feature_dict = features.to_dicts()[0]
        
        soc = feature_dict.get('soc_percent', 0.5)
        tariff = feature_dict.get('current_tariff_uah_mwh', 0.5)
        is_peak = feature_dict.get('is_peak_hour', 0.0)
        load = feature_dict.get('current_load_kw', 0.5)
        
        confidence_pct = int(confidence * 100)
        
        if action == 'BUY':
            reason = f"Charge battery at current tariff level ({tariff:.0%}). "
            if is_peak < 0.5:
                reason += "Off-peak pricing provides favorable charging conditions."
            else:
                reason += "Low tariff relative to peak hours justifies charging."
            reason += f" Confidence: {confidence_pct}%."
        
        elif action == 'SELL':
            reason = f"Discharge battery to supply current load ({load:.0%}). "
            if is_peak > 0.5:
                reason += "Peak hour pricing makes discharge most profitable."
            else:
                reason += "Discharge reduces grid consumption."
            reason += f" Confidence: {confidence_pct}%."
        
        else:  # HOLD
            reason = "Current market conditions do not justify charging or discharging. "
            if soc < 0.3:
                reason += "Battery SOC is low, preferring charge availability."
            elif soc > 0.8:
                reason += "Battery is well-charged. Avoid additional degradation."
            else:
                reason += "Balance between economic opportunity and battery longevity."
            reason += f" Confidence: {confidence_pct}%."
        
        return reason
    
    def _get_feature_importance(self, features: pl.DataFrame) -> Dict[str, float]:
        """Get feature importance scores.
        
        Args:
            features: Input features
        
        Returns:
            Dict of feature importance scores
        """
        # Heuristic importance based on variance in current instance
        feature_dict = features.to_dicts()[0]
        
        importance = {}
        
        # Peak hour is always important
        importance['is_peak_hour'] = 0.20
        
        # SOC importance depends on value
        soc = feature_dict.get('soc_percent', 0.5)
        importance['soc_percent'] = 0.15 if 0.2 < soc < 0.8 else 0.20
        
        # Tariff importance
        importance['current_tariff_uah_mwh'] = 0.15
        
        # Load importance
        load = feature_dict.get('current_load_kw', 0.5)
        importance['current_load_kw'] = 0.12 if load > 0.2 else 0.08
        
        # Battery health
        health = feature_dict.get('battery_health', 0.8)
        importance['battery_health'] = 0.12 if health < 0.5 else 0.08
        
        # Remaining features
        importance['price_trend'] = 0.08
        importance['load_forecast_1h'] = 0.06
        importance['day_of_week'] = 0.04
        
        return importance
    
    def validate_features(self, features: pl.DataFrame) -> Tuple[bool, List[str]]:
        """Validate feature DataFrame matches model schema.
        
        Args:
            features: Input features DataFrame
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check shape
        if features.shape[0] != 1:
            errors.append(f"Expected 1 row, got {features.shape[0]}")
        
        # Check columns
        feature_cols = set(features.columns)
        expected_cols = set(self.EXPECTED_FEATURES)
        
        missing = expected_cols - feature_cols
        if missing:
            errors.append(f"Missing features: {missing}")
        
        # Check values in 0-1 range
        for col in self.EXPECTED_FEATURES:
            if col in feature_cols:
                val = features[col][0]
                if not (0.0 <= val <= 1.0):
                    errors.append(f"Feature {col} out of bounds: {val}")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def _error_response(self, error_msg: str) -> Dict[str, any]:
        """Generate error response.
        
        Args:
            error_msg: Error message
        
        Returns:
            Error response dict (defaults to HOLD)
        """
        logger.error(f"Prediction error: {error_msg}")
        return {
            'action': 'HOLD',
            'confidence': 0.0,
            'reasoning': f"Prediction failed: {error_msg}",
            'model_version': self.model_version,
            'timestamp': datetime.now().isoformat(),
            'feature_importance': {},
            'error': error_msg,
        }
    
    def get_model_info(self) -> Dict[str, any]:
        """Return loaded model metadata.
        
        Returns:
            Dict with model information
        """
        return {
            'model_uri': self.model_uri,
            'model_version': self.model_version,
            'mock_mode': self._mock_mode,
            'mlflow_available': MLFLOW_AVAILABLE,
            'expected_features': self.EXPECTED_FEATURES,
            'valid_actions': self.VALID_ACTIONS,
        }

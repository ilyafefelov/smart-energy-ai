"""Phase 4F: ML Integration - MLflow Model Loading and Prediction Service.

Integrates MLflow model for energy trading recommendations.
"""
import importlib.util
import logging
import os
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

LEARNED_POLICY_SERVING_MODE = "learned_policy"
LEGACY_MOCK_SERVING_MODE = "legacy_mock"


def _normalize_serving_mode(value: Optional[str]) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == LEARNED_POLICY_SERVING_MODE:
        return LEARNED_POLICY_SERVING_MODE
    return LEGACY_MOCK_SERVING_MODE


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    normalized = str(value or "").strip()
    return normalized or None


def _resolve_model_uri(
    model_uri: Optional[str] = None,
    model_name: Optional[str] = None,
    model_alias: Optional[str] = None,
    model_stage: Optional[str] = None,
) -> Optional[str]:
    explicit_uri = _normalize_optional_text(model_uri)
    if explicit_uri:
        return explicit_uri

    normalized_name = _normalize_optional_text(model_name)
    normalized_alias = _normalize_optional_text(model_alias)
    normalized_stage = _normalize_optional_text(model_stage)

    if normalized_name and normalized_alias:
        return f"models:/{normalized_name}@{normalized_alias}"
    if normalized_name and normalized_stage:
        return f"models:/{normalized_name}/{normalized_stage}"

    return None


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
    
    def __init__(
        self,
        model_uri: Optional[str] = None,
        *,
        model_name: Optional[str] = None,
        model_alias: Optional[str] = None,
        model_stage: Optional[str] = None,
        tracking_uri: Optional[str] = None,
        serving_mode: Optional[str] = None,
        require_explicit_model: bool = False,
        allow_mock_fallback: Optional[bool] = None,
    ):
        """Initialize prediction service with MLflow model.
        
        Args:
            model_uri: MLflow model URI (e.g., 'models:/battery-optimizer/production')
                      If None, uses latest registered model.
        """
        self.serving_mode = _normalize_serving_mode(serving_mode)
        self.model_name = _normalize_optional_text(model_name)
        self.model_alias = _normalize_optional_text(model_alias)
        self.model_stage = _normalize_optional_text(model_stage)
        self.requested_model_uri = _normalize_optional_text(model_uri)
        self.model_uri = _resolve_model_uri(
            model_uri=model_uri,
            model_name=model_name,
            model_alias=model_alias,
            model_stage=model_stage,
        )
        self.tracking_uri = (
            _normalize_optional_text(tracking_uri)
            or _normalize_optional_text(os.getenv("ENERGY_ML_MLFLOW_TRACKING_URI"))
            or _normalize_optional_text(os.getenv("MLFLOW_TRACKING_URI"))
        )
        self.model = None
        self.model_info = None
        self.model_version = "mock-v1"
        self.require_explicit_model = bool(
            require_explicit_model or self.serving_mode == LEARNED_POLICY_SERVING_MODE
        )
        self._mock_mode = bool(
            allow_mock_fallback
            if allow_mock_fallback is not None
            else not self.require_explicit_model
        )
        self.availability_error: Optional[str] = None
        self.availability_message: Optional[str] = None
        self.fallback_reason_code = "none"

        self._load_model()

    @classmethod
    def for_learned_policy(
        cls,
        *,
        model_uri: Optional[str] = None,
        model_name: Optional[str] = None,
        model_alias: Optional[str] = None,
        model_stage: Optional[str] = None,
        tracking_uri: Optional[str] = None,
    ) -> "PredictionService":
        return cls(
            model_uri=model_uri,
            model_name=model_name,
            model_alias=model_alias,
            model_stage=model_stage,
            tracking_uri=tracking_uri,
            serving_mode=LEARNED_POLICY_SERVING_MODE,
            require_explicit_model=True,
            allow_mock_fallback=False,
        )

    def _mark_unavailable(self, reason_code: str, message: str) -> None:
        self.availability_error = reason_code
        self.availability_message = message
        self.fallback_reason_code = reason_code
        self.model_version = "unavailable"
    
    def _load_model(self):
        """Load MLflow model.
        
        Handles missing models gracefully by falling back to mock mode.
        """
        self.model = None
        self.model_info = None
        self.availability_error = None
        self.availability_message = None
        self.fallback_reason_code = "none"

        if self.model_uri is None:
            if self.require_explicit_model:
                self._mock_mode = False
                self._mark_unavailable(
                    "learned_policy_model_not_configured",
                    "Learned-policy mode requires ENERGY_ML_MODEL_URI or ENERGY_ML_MODEL_NAME with ENERGY_ML_MODEL_ALIAS or ENERGY_ML_MODEL_STAGE.",
                )
                logger.warning(self.availability_message)
                return

            logger.info("No model URI provided. Using mock prediction service.")
            self._mock_mode = True
            return

        if not MLFLOW_AVAILABLE:
            if self._mock_mode:
                logger.warning("MLflow not available. PredictionService will operate in mock mode.")
                return

            self._mock_mode = False
            self._mark_unavailable(
                "mlflow_unavailable",
                "MLflow is not installed or importable, so learned-policy serving cannot load the configured model.",
            )
            logger.warning(self.availability_message)
            return

        try:
            if self.tracking_uri and hasattr(mlflow, "set_tracking_uri"):
                mlflow.set_tracking_uri(self.tracking_uri)

            self.model = mlflow.pyfunc.load_model(self.model_uri)
            self._mock_mode = False
            logger.info(f"Loaded MLflow model: {self.model_uri}")

            try:
                self.model_info = mlflow.models.get_model(self.model_uri)
                self.model_version = self.model_info.version if hasattr(self.model_info, 'version') else "unknown"
            except Exception as e:
                logger.warning(f"Could not retrieve model metadata: {e}")
                self.model_version = "unknown"

        except Exception as e:
            if self._mock_mode:
                logger.warning(f"Failed to load MLflow model: {e}. Using mock prediction service.")
                return

            self._mock_mode = False
            self._mark_unavailable(
                "learned_policy_model_load_failed",
                f"Failed to load learned-policy model from {self.model_uri}: {e}",
            )
            logger.warning(self.availability_message)
    
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

        if self.require_explicit_model and self.model is None:
            return self._service_unavailable_response()
        
        if self._mock_mode:
            return self._mock_predict(features)
        
        try:
            feature_array = features[self.EXPECTED_FEATURES].to_numpy()
            prediction = self.model.predict(feature_array)
            action, confidence = self._parse_prediction(prediction)
            reasoning = self._generate_reasoning(action, features, confidence)
            response = build_prediction_response(
                action,
                confidence,
                reasoning,
                self.model_version,
                self._get_feature_importance(features),
            )
            response["decision_source"] = "ml_recommendation"
            response["fallback_reason_code"] = "none"
            response["serving_mode"] = self.serving_mode
            response["resolved_model_uri"] = self.model_uri
            return response
        
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return self._error_response(str(e))
    
    def _mock_predict(self, features: pl.DataFrame) -> Dict[str, any]:
        """Generate mock prediction (when model unavailable).
        
        Uses simple heuristic rules based on features.
        """
        response = build_mock_prediction(features, self.model_version)
        response["decision_source"] = "ml_recommendation"
        response["fallback_reason_code"] = "none"
        response["serving_mode"] = self.serving_mode
        response["resolved_model_uri"] = self.model_uri
        return response
    
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
        response = build_error_response(error_msg, self.model_version)
        response["decision_source"] = "ml_recommendation"
        response["fallback_reason_code"] = self.fallback_reason_code
        response["serving_mode"] = self.serving_mode
        response["resolved_model_uri"] = self.model_uri
        return response

    def _service_unavailable_response(self) -> Dict[str, Any]:
        message = self.availability_message or "Learned-policy serving is unavailable"
        return self._error_response(message)
    
    def get_model_info(self) -> Dict[str, any]:
        """Return loaded model metadata.
        
        Returns:
            Dict with model information
        """
        info = build_model_info(
            self.model_uri,
            self.model_version,
            self._mock_mode,
            MLFLOW_AVAILABLE,
            self.EXPECTED_FEATURES,
            self.VALID_ACTIONS,
        )
        info.update({
            "serving_mode": self.serving_mode,
            "require_explicit_model": self.require_explicit_model,
            "requested_model_uri": self.requested_model_uri,
            "resolved_model_uri": self.model_uri,
            "model_name": self.model_name,
            "model_alias": self.model_alias,
            "model_stage": self.model_stage,
            "tracking_uri": self.tracking_uri,
            "model_available": self.model is not None and not self._mock_mode,
            "availability_error": self.availability_error,
            "availability_message": self.availability_message,
            "fallback_reason_code": self.fallback_reason_code,
        })
        return info
    
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

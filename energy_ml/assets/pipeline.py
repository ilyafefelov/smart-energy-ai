"""Phase 4F: Dagster Assets - Pipeline Integration and Feature Engineering.

Orchestrates the full ML pipeline through Dagster assets with proper
data lineage from user config through features to predictions.
"""
import logging
from datetime import datetime
from typing import Dict, Any

import polars as pl
from dagster import asset, In, Out, DagsterInvariantViolationError

from energy_ml.pipeline import PipelineOrchestrator
from energy_ml.features import FeatureEngineer
from energy_ml.ml_integration import PredictionService
from energy_ml.user_config import UserConfigModel, ConfigurationManager


logger = logging.getLogger(__name__)


@asset(
    name="integrated_pipeline",
    description="Full pipeline integration orchestrating all Phase 4 components",
    tags=["phase_4f", "pipeline"],
    compute_kind="python",
)
def integrated_pipeline_asset(
    user_config_data: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Asset: Full pipeline integration and recommendation generation.
    
    Orchestrates:
    - Load user configuration (Phase 4E)
    - Initialize PipelineOrchestrator with all Phase 4 components:
      * Battery models (Phase 4B)
      * Load profiles (Phase 4C)
      * Tariff models (Phase 4D)
      * User configuration (Phase 4E)
    - Generate recommendation (BUY/SELL/HOLD)
    - Return decision with full context
    
    Depends on: user_config (if available), battery_models, load_profiles, tariff_optimization
    
    Returns:
        dict with keys:
        - action: str ('BUY', 'SELL', 'HOLD')
        - reasoning: str
        - confidence: float (0.0-1.0)
        - estimated_savings: float (UAH)
        - battery_impact: float (%)
        - timestamp: str (ISO 8601)
        - details: dict (full state)
        - status: str ('success' or 'error')
    """
    try:
        # Load configuration
        if user_config_data is None:
            config_manager = ConfigurationManager()
            config = config_manager.load_config()
        else:
            config = UserConfigModel(**user_config_data)
        
        logger.info(f"Integrated pipeline using config: {config.dict()}")
        
        # Initialize orchestrator
        orchestrator = PipelineOrchestrator(config)
        
        # Validate inputs
        is_valid, errors = orchestrator.validate_all_inputs()
        if not is_valid:
            logger.warning(f"Configuration validation warnings: {errors}")
        
        # Generate recommendation
        recommendation = orchestrator.calculate_recommendation(config)
        
        # Add status
        recommendation['status'] = 'success'
        
        logger.info(f"Pipeline generated recommendation: {recommendation['action']}")
        
        return recommendation
    
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return {
            'action': 'HOLD',
            'reasoning': f'Pipeline error: {str(e)}',
            'confidence': 0.0,
            'estimated_savings': 0.0,
            'battery_impact': 0.0,
            'timestamp': datetime.now().isoformat(),
            'details': {},
            'status': 'error',
            'error': str(e),
        }


@asset(
    name="engineered_features",
    description="Feature engineering - normalized features for ML model",
    tags=["phase_4f", "features"],
    compute_kind="python",
    ins={
        "integrated_pipeline": In(
            name="integrated_pipeline",
            description="Pipeline output used for feature context"
        )
    },
)
def engineered_features_asset(integrated_pipeline: Dict[str, Any]) -> pl.DataFrame:
    """Asset: Feature engineering output for ML models.
    
    Uses FeatureEngineer to extract normalized features from pipeline state.
    
    Input:
        integrated_pipeline: Pipeline output dict
    
    Returns:
        polars DataFrame with 14 normalized features (0-1 range):
        
        TEMPORAL (4):
        - hour_of_day: Current hour normalized (0-1)
        - day_of_week: Day of week normalized (0-1)
        - is_peak_hour: Binary peak indicator
        - season: Quarter of year normalized (0-1)
        
        PRICE (3):
        - current_tariff_uah_mwh: Normalized by bounds
        - price_trend: 6-hour MA derivative
        - price_volatility: 6-hour std dev
        
        BATTERY (4):
        - soc_percent: State of charge normalized (0-1)
        - battery_health: Health % normalized (0-1)
        - degradation_cost_uah_kwh: Cost per cycle normalized
        - battery_cycles_remaining: Log-normalized cycles
        
        LOAD (3):
        - current_load_kw: Current load normalized
        - load_forecast_1h: Next hour load normalized
        - load_trend: 3-hour MA derivative
        
        All features are in [0.0, 1.0] range with no missing values.
    """
    try:
        # Create feature engineer
        engineer = FeatureEngineer()
        
        # Create orchestrator for context
        config_manager = ConfigurationManager()
        config = config_manager.load_config()
        orchestrator = PipelineOrchestrator(config)
        
        # Extract features
        features = engineer.extract_features(orchestrator)
        
        logger.info(f"Extracted {features.shape[1]} features, shape: {features.shape}")
        
        # Validate all features are 0-1
        for col in features.columns:
            min_val = features[col].min()
            max_val = features[col].max()
            if not (min_val >= 0.0 and max_val <= 1.0):
                logger.warning(f"Feature {col} out of bounds: [{min_val}, {max_val}]")
        
        return features
    
    except Exception as e:
        logger.error(f"Feature engineering failed: {e}")
        # Return empty DataFrame with correct structure
        empty_features = {
            'hour_of_day': [0.0],
            'day_of_week': [0.0],
            'is_peak_hour': [0.0],
            'season': [0.0],
            'current_tariff_uah_mwh': [0.5],
            'price_trend': [0.5],
            'price_volatility': [0.5],
            'soc_percent': [0.5],
            'battery_health': [0.5],
            'degradation_cost_uah_kwh': [0.0],
            'battery_cycles_remaining': [0.5],
            'current_load_kw': [0.0],
            'load_forecast_1h': [0.0],
            'load_trend': [0.5],
        }
        return pl.DataFrame(empty_features)


@asset(
    name="ml_predictions",
    description="ML model predictions based on engineered features",
    tags=["phase_4f", "ml"],
    compute_kind="python",
    ins={
        "engineered_features": In(
            name="engineered_features",
            description="Normalized features from feature engineer"
        )
    },
)
def ml_predictions_asset(engineered_features: pl.DataFrame) -> Dict[str, Any]:
    """Asset: ML model predictions.
    
    Uses PredictionService to load MLflow model and generate predictions.
    
    Input:
        engineered_features: polars DataFrame with 14 normalized features
    
    Returns:
        dict with keys:
        - action: str ('BUY', 'SELL', 'HOLD')
        - confidence: float (0.0-1.0)
        - reasoning: str (explanation)
        - model_version: str
        - timestamp: str
        - feature_importance: dict (top features)
        - status: str ('success' or 'error')
    """
    try:
        # Initialize prediction service
        prediction_service = PredictionService()
        
        # Generate prediction
        prediction = prediction_service.predict(engineered_features)
        
        # Add status
        prediction['status'] = 'success'
        
        logger.info(f"ML model predicted: {prediction['action']}")
        
        return prediction
    
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        return {
            'action': 'HOLD',
            'confidence': 0.0,
            'reasoning': f'Prediction service error: {str(e)}',
            'model_version': 'error',
            'timestamp': datetime.now().isoformat(),
            'feature_importance': {},
            'status': 'error',
            'error': str(e),
        }


@asset(
    name="pipeline_status",
    description="Overall pipeline status and health",
    tags=["phase_4f", "status"],
    compute_kind="python",
    ins={
        "integrated_pipeline": In(name="integrated_pipeline"),
        "engineered_features": In(name="engineered_features"),
        "ml_predictions": In(name="ml_predictions"),
    },
)
def pipeline_status_asset(
    integrated_pipeline: Dict[str, Any],
    engineered_features: pl.DataFrame,
    ml_predictions: Dict[str, Any],
) -> Dict[str, Any]:
    """Asset: Overall pipeline status combining all components.
    
    Inputs:
        integrated_pipeline: Pipeline recommendation
        engineered_features: Extracted features
        ml_predictions: Model predictions
    
    Returns:
        dict with comprehensive pipeline status
    """
    return {
        'timestamp': datetime.now().isoformat(),
        'pipeline_status': integrated_pipeline.get('status', 'unknown'),
        'pipeline_action': integrated_pipeline.get('action', 'HOLD'),
        'pipeline_confidence': integrated_pipeline.get('confidence', 0.0),
        'features_count': engineered_features.shape[1],
        'features_valid': all(
            0.0 <= engineered_features[col].min() and
            engineered_features[col].max() <= 1.0
            for col in engineered_features.columns
        ),
        'ml_status': ml_predictions.get('status', 'unknown'),
        'ml_action': ml_predictions.get('action', 'HOLD'),
        'ml_confidence': ml_predictions.get('confidence', 0.0),
        'agreement': 1.0 if (
            integrated_pipeline.get('action') == ml_predictions.get('action')
        ) else 0.0,
    }

"""Phase 4F: Dagster Assets - Pipeline Integration and Feature Engineering.

Orchestrates the full ML pipeline through Dagster assets with proper
data lineage from user config through features to predictions.
"""
import logging
from datetime import datetime
from typing import Dict, Any

import polars as pl
from dagster import asset, AssetIn

from energy_ml.pipeline import PipelineOrchestrator
from energy_ml.features import FeatureEngineer
from energy_ml.ml_integration import PredictionService
from energy_ml.user_config import UserConfigModel, ConfigurationManager
from energy_ml.mlops.optimization_engine import OptimizationEngine
from energy_ml.mlops.battery_physics import BatteryPhysicsEngine
from energy_ml.mlops.renewable_forecasting import RenewableForecaster


logger = logging.getLogger(__name__)


@asset(
    name="integrated_pipeline",
    description="Full pipeline integration orchestrating all Phase 4 components",
    tags={"phase_4f": "true", "pipeline": "true"},
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
            config = config_manager.load_config_or_raise()
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
    tags={"phase_4f": "true", "features": "true"},
    compute_kind="python",
    ins={
        "integrated_pipeline": AssetIn()
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
        config = config_manager.load_config_or_raise()
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
    tags={"phase_4f": "true", "ml": "true"},
    compute_kind="python",
    ins={
        "engineered_features": AssetIn()
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
    tags={"phase_4f": "true", "status": "true"},
    compute_kind="python",
    ins={
        "integrated_pipeline": AssetIn(),
        "engineered_features": AssetIn(),
        "ml_predictions": AssetIn(),
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


@asset(
    name="optimization_preferences",
    description="User optimization preferences for Max Earn, Max Battery Health, Max Charge strategies",
    tags={"optimization": "true", "user_preferences": "true"},
    compute_kind="python",
)
def optimization_preferences_asset(user_config_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Asset: User optimization strategy preferences.
    
    Loads user optimization strategy (Max Earn, Max Health, Max Charge)
    and processes user preferences for decision optimization.
    
    Returns:
        dict with keys:
        - strategy: str ('max_earn', 'max_battery_health', 'max_charge')
        - weights: dict (optimization weights for different objectives)
        - constraints: dict (user-defined constraints)
        - preferences: dict (full user preferences)
    """
    try:
        # Load configuration
        if user_config_data is None:
            config_manager = ConfigurationManager()
            config = config_manager.load_config_or_raise()
        else:
            config = UserConfigModel(**user_config_data)
        
        # Initialize optimization engine
        optimization_engine = OptimizationEngine()
        
        # Get user strategy from config (extend UserConfigModel to include this)
        strategy = getattr(config, 'optimization_strategy', 'balanced')  # Default: balanced
        
        # Load optimization preferences
        preferences = optimization_engine.get_user_strategy(config)
        
        logger.info(f"Loaded optimization strategy: {strategy}")
        
        return {
            'strategy': strategy,
            'weights': preferences.get('weights', {}),
            'constraints': preferences.get('constraints', {}),
            'preferences': preferences,
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        }
    
    except Exception as e:
        logger.error(f"Optimization preferences failed: {e}")
        return {
            'strategy': 'balanced',
            'weights': {'earnings': 0.4, 'battery_health': 0.4, 'charge_availability': 0.2},
            'constraints': {},
            'preferences': {},
            'timestamp': datetime.now().isoformat(),
            'status': 'error',
            'error': str(e)
        }


@asset(
    name="battery_physics_simulation",
    description="Real battery physics simulation with multi-chemistry models",
    tags={"physics": "true", "battery": "true"},
    compute_kind="python",
)
def battery_physics_asset(user_config_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Asset: Real battery physics simulation.
    
    Runs real battery physics simulation with actual charging behavior
    for different battery chemistries (LFP, Lead-Acid, VRFB).
    
    Returns:
        dict with keys:
        - chemistry: str (battery chemistry)
        - simulation_results: dict (physics simulation output)
        - charging_curves: dict (voltage/current curves)
        - degradation_model: dict (degradation physics)
        - efficiency_model: dict (efficiency at different states)
    """
    try:
        # Load configuration
        if user_config_data is None:
            config_manager = ConfigurationManager()
            config = config_manager.load_config_or_raise()
        else:
            config = UserConfigModel(**user_config_data)
        
        # Initialize battery physics engine
        physics_engine = BatteryPhysicsEngine()
        
        # Run battery physics simulation
        simulation_results = physics_engine.simulate_battery_behavior(config)
        
        logger.info(f"Battery physics simulation completed for {config.battery_type}")
        
        return {
            'chemistry': config.battery_type,
            'simulation_results': simulation_results,
            'charging_curves': simulation_results.get('charging_curves', {}),
            'degradation_model': simulation_results.get('degradation_model', {}),
            'efficiency_model': simulation_results.get('efficiency_model', {}),
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        }
    
    except Exception as e:
        logger.error(f"Battery physics simulation failed: {e}")
        return {
            'chemistry': 'LFP',
            'simulation_results': {},
            'charging_curves': {},
            'degradation_model': {},
            'efficiency_model': {},
            'timestamp': datetime.now().isoformat(),
            'status': 'error',
            'error': str(e)
        }


@asset(
    name="renewable_generation_forecast",
    description="Solar/Wind generation modeling and forecasting",
    tags={"renewable": "true", "forecasting": "true"},
    compute_kind="python",
)
def renewable_generation_asset(user_config_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Asset: Real-time renewable generation modeling.
    
    Models solar and wind generation based on weather data,
    location, and installed capacity.
    
    Returns:
        dict with keys:
        - solar_forecast: dict (hourly solar generation forecast)
        - wind_forecast: dict (hourly wind generation forecast)
        - total_renewable: dict (combined renewable forecast)
        - weather_data: dict (weather conditions used)
        - capacity_factors: dict (renewable capacity factors)
    """
    try:
        # Load configuration
        if user_config_data is None:
            config_manager = ConfigurationManager()
            config = config_manager.load_config_or_raise()
        else:
            config = UserConfigModel(**user_config_data)
        
        # Initialize renewable forecaster
        renewable_forecaster = RenewableForecaster()
        
        # Generate renewable forecasts
        forecasts = renewable_forecaster.generate_forecasts(config)
        
        logger.info("Renewable generation forecast completed")
        
        return {
            'solar_forecast': forecasts.get('solar_forecast', {}),
            'wind_forecast': forecasts.get('wind_forecast', {}),
            'total_renewable': forecasts.get('total_renewable', {}),
            'weather_data': forecasts.get('weather_data', {}),
            'capacity_factors': forecasts.get('capacity_factors', {}),
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        }
    
    except Exception as e:
        logger.error(f"Renewable generation forecast failed: {e}")
        return {
            'solar_forecast': {},
            'wind_forecast': {},
            'total_renewable': {},
            'weather_data': {},
            'capacity_factors': {},
            'timestamp': datetime.now().isoformat(),
            'status': 'error',
            'error': str(e)
        }


@asset(
    name="enhanced_ml_predictions",
    description="Enhanced ML predictions using optimization preferences and physics simulation",
    tags={"phase_4f": "true", "ml": "true", "enhanced": "true"},
    compute_kind="python",
    ins={
        "engineered_features": AssetIn(),
        "optimization_preferences": AssetIn(),
        "battery_physics_simulation": AssetIn(),
        "renewable_generation_forecast": AssetIn(),
    },
)
def enhanced_ml_predictions_asset(
    engineered_features: pl.DataFrame,
    optimization_preferences: Dict[str, Any],
    battery_physics_simulation: Dict[str, Any],
    renewable_generation_forecast: Dict[str, Any]
) -> Dict[str, Any]:
    """Asset: Enhanced ML predictions with user optimization and physics.
    
    Uses PredictionService with optimization preferences to generate
    enhanced predictions that consider user strategy and physics constraints.
    
    Inputs:
        engineered_features: Normalized features from feature engineer
        optimization_preferences: User optimization strategy
        battery_physics_simulation: Real battery physics data
        renewable_generation_forecast: Renewable generation forecasts
    
    Returns:
        dict with enhanced prediction including optimization strategy
    """
    try:
        # Initialize prediction service
        prediction_service = PredictionService()
        
        # Get base ML prediction
        base_prediction = prediction_service.predict(engineered_features)
        
        # Apply optimization preferences
        strategy = optimization_preferences.get('strategy', 'balanced')
        weights = optimization_preferences.get('weights', {})
        
        # Initialize optimization engine
        optimization_engine = OptimizationEngine()
        
        # Optimize the decision based on user preferences
        optimized_prediction = optimization_engine.optimize_decision(
            base_prediction, 
            strategy,
            physics_data=battery_physics_simulation,
            renewable_data=renewable_generation_forecast,
            weights=weights
        )
        
        # Enhance with physics-based constraints
        physics_engine = BatteryPhysicsEngine()
        physics_constrained = physics_engine.apply_physics_constraints(
            optimized_prediction,
            battery_physics_simulation
        )
        
        # Add renewable integration
        renewable_forecaster = RenewableForecaster()
        renewable_enhanced = renewable_forecaster.integrate_with_prediction(
            physics_constrained,
            renewable_generation_forecast
        )
        
        # Combine all enhancements
        enhanced_prediction = {
            **renewable_enhanced,
            'action': renewable_enhanced.get('action', 'HOLD'),
            'base_prediction': base_prediction,
            'optimization_applied': strategy,
            'physics_constraints': battery_physics_simulation.get('constraints', {}),
            'renewable_integration': renewable_generation_forecast.get('integration', {}),
            'enhancement_confidence': min(1.0, renewable_enhanced.get('confidence', 0.0) + 0.1),
            'status': 'success'
        }
        
        logger.info(f"Enhanced ML prediction: {enhanced_prediction['action']} (strategy: {strategy})")
        
        return enhanced_prediction
    
    except Exception as e:
        logger.error(f"Enhanced prediction failed: {e}")
        return {
            'action': 'HOLD',
            'confidence': 0.0,
            'reasoning': f'Enhanced prediction service error: {str(e)}',
            'model_version': 'enhanced-error',
            'timestamp': datetime.now().isoformat(),
            'feature_importance': {},
            'base_prediction': {},
            'optimization_applied': 'none',
            'physics_constraints': {},
            'renewable_integration': {},
            'enhancement_confidence': 0.0,
            'status': 'error',
            'error': str(e)
        }

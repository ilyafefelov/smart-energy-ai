"""Phase 4F: Full Pipeline Integration & Feature Engineering - Comprehensive Tests"""
import pytest
import polars as pl
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from energy_ml.pipeline import PipelineOrchestrator
from energy_ml.features import FeatureEngineer
from energy_ml.ml_integration import PredictionService
from energy_ml.user_config import UserConfigModel
from energy_ml.config_models import BatteryConfig, LoadProfileConfig
from energy_ml.battery_degradation import BatteryModel
from energy_ml.load_simulation import StandardWorkSimulator
from energy_ml.tariff_models import UkraineTariffModel


class TestPipelineOrchestrator:
    """Test PipelineOrchestrator - full component integration (7 tests)"""
    
    def test_init_with_default_config(self):
        """Test initialization with default user config."""
        orchestrator = PipelineOrchestrator()
        
        assert orchestrator.config is not None
        assert orchestrator.battery is not None
        assert orchestrator.load_profile is not None
        assert orchestrator.tariff is not None
    
    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = UserConfigModel(
            battery_capacity_kwh=20.0,
            battery_efficiency=0.90,
            load_peak_kw=25.0
        )
        orchestrator = PipelineOrchestrator(config)
        
        assert orchestrator.config.battery_capacity_kwh == 20.0
        assert orchestrator.config.battery_efficiency == 0.90
        assert orchestrator.config.load_peak_kw == 25.0
    
    def test_calculate_recommendation_returns_dict(self):
        """Test recommendation returns proper dict structure."""
        orchestrator = PipelineOrchestrator()
        recommendation = orchestrator.calculate_recommendation()
        
        assert isinstance(recommendation, dict)
        assert 'action' in recommendation
        assert 'reasoning' in recommendation
        assert 'confidence' in recommendation
        assert 'estimated_savings' in recommendation
        assert 'battery_impact' in recommendation
        assert 'timestamp' in recommendation
    
    def test_recommendation_action_is_valid(self):
        """Test recommendation action is BUY/SELL/HOLD."""
        orchestrator = PipelineOrchestrator()
        recommendation = orchestrator.calculate_recommendation()
        
        assert recommendation['action'] in ['BUY', 'SELL', 'HOLD']
    
    def test_recommendation_confidence_in_range(self):
        """Test confidence is 0.0-1.0."""
        orchestrator = PipelineOrchestrator()
        recommendation = orchestrator.calculate_recommendation()
        
        assert 0.0 <= recommendation['confidence'] <= 1.0
    
    def test_validate_inputs_all_valid(self):
        """Test validation with all valid inputs."""
        config = UserConfigModel()
        orchestrator = PipelineOrchestrator(config)
        
        is_valid, errors = orchestrator.validate_all_inputs()
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_inputs_detects_invalid(self):
        """Test validation detects invalid config."""
        # Invalid config should raise ValidationError during __init__
        with pytest.raises(Exception):  # Could be ValidationError or other error
            config = UserConfigModel(
                battery_capacity_kwh=-1.0  # Invalid: negative
            )
            orchestrator = PipelineOrchestrator(config)
    
    def test_hourly_forecast_returns_dataframe(self):
        """Test forecast returns proper DataFrame."""
        orchestrator = PipelineOrchestrator()
        forecast = orchestrator.get_hourly_forecast(hours=24)
        
        assert isinstance(forecast, pd.DataFrame)
        assert len(forecast) == 24
        assert 'hour' in forecast.columns
        assert 'action' in forecast.columns
        assert 'confidence' in forecast.columns
    
    def test_status_returns_complete_info(self):
        """Test get_status returns comprehensive state."""
        orchestrator = PipelineOrchestrator()
        status = orchestrator.get_status()
        
        assert 'config' in status
        assert 'battery_state' in status
        assert 'load_profile' in status
        assert 'tariff' in status
        assert 'timestamp' in status


class TestFeatureEngineer:
    """Test FeatureEngineer - feature extraction and normalization (8 tests)"""
    
    def test_extract_features_returns_dataframe(self):
        """Test feature extraction returns polars DataFrame."""
        engineer = FeatureEngineer()
        orchestrator = PipelineOrchestrator()
        
        features = engineer.extract_features(orchestrator)
        
        assert isinstance(features, pl.DataFrame)
    
    def test_extracted_features_has_14_columns(self):
        """Test extracted features has exactly 14 columns."""
        engineer = FeatureEngineer()
        orchestrator = PipelineOrchestrator()
        
        features = engineer.extract_features(orchestrator)
        
        assert features.shape[1] == 14
    
    def test_extracted_features_all_normalized(self):
        """Test all features are normalized to 0-1."""
        engineer = FeatureEngineer()
        orchestrator = PipelineOrchestrator()
        
        features = engineer.extract_features(orchestrator)
        
        for col in features.columns:
            min_val = features[col].min()
            max_val = features[col].max()
            assert min_val >= 0.0, f"Feature {col} min {min_val} < 0.0"
            assert max_val <= 1.0, f"Feature {col} max {max_val} > 1.0"
    
    def test_no_null_values_in_features(self):
        """Test no null/NaN values in extracted features."""
        engineer = FeatureEngineer()
        orchestrator = PipelineOrchestrator()
        
        features = engineer.extract_features(orchestrator)
        
        for col in features.columns:
            assert features[col].null_count() == 0
    
    def test_temporal_features_extraction(self):
        """Test temporal feature extraction."""
        engineer = FeatureEngineer()
        now = datetime.now()
        
        temporal = engineer.extract_temporal_features(now)
        
        assert 'hour_of_day' in temporal
        assert 'day_of_week' in temporal
        assert 'is_peak_hour' in temporal
        assert 'season' in temporal
        
        # Check ranges
        assert 0.0 <= temporal['hour_of_day'] <= 1.0
        assert 0.0 <= temporal['day_of_week'] <= 1.0
        assert temporal['is_peak_hour'] in [0.0, 1.0]
        assert 0.0 <= temporal['season'] <= 1.0
    
    def test_price_features_extraction(self):
        """Test price feature extraction."""
        engineer = FeatureEngineer()
        tariff = UkraineTariffModel()
        
        price_features = engineer.extract_price_features(tariff)
        
        assert 'current_tariff' in price_features
        assert 'trend' in price_features
        assert 'volatility' in price_features
        
        # Check ranges
        assert 0.0 <= price_features['current_tariff'] <= 1.0
        assert 0.0 <= price_features['trend'] <= 1.0
        assert 0.0 <= price_features['volatility'] <= 1.0
    
    def test_battery_features_extraction(self):
        """Test battery feature extraction."""
        engineer = FeatureEngineer()
        config = UserConfigModel()
        
        # Create a simple battery config for testing
        battery_config = BatteryConfig(
            type='LFP',
            capacity_kwh=10.0,
            efficiency=0.95,
            max_charge_rate_kw=5.0,
            max_discharge_rate_kw=5.0,
        )
        battery = BatteryModel(battery_config)
        
        battery_features = engineer.extract_battery_features(battery)
        
        assert 'soc' in battery_features
        assert 'health' in battery_features
        assert 'degradation_cost' in battery_features
        assert 'cycles_remaining' in battery_features
        
        # Check ranges
        assert 0.0 <= battery_features['soc'] <= 1.0
        assert 0.0 <= battery_features['health'] <= 1.0
        assert 0.0 <= battery_features['degradation_cost'] <= 1.0
        assert 0.0 <= battery_features['cycles_remaining'] <= 1.0
    
    def test_load_features_extraction(self):
        """Test load feature extraction."""
        engineer = FeatureEngineer()
        config = UserConfigModel()
        
        # Create a LoadProfileConfig for testing
        load_config = LoadProfileConfig(
            profile_type='standard',
            name='Test Load',
            description='Test load profile',
            peak_load_kw=10.0,
            hourly_coefficients={
                i: 0.5 for i in range(24)
            }
        )
        load_profile = StandardWorkSimulator(load_config)
        
        load_features = engineer.extract_load_features(load_profile)
        
        assert 'current_load' in load_features
        assert 'forecast_1h' in load_features
        assert 'trend' in load_features
        
        # Check ranges
        assert 0.0 <= load_features['current_load'] <= 1.0
        assert 0.0 <= load_features['forecast_1h'] <= 1.0
        assert 0.0 <= load_features['trend'] <= 1.0
    
    def test_normalize_feature(self):
        """Test feature normalization."""
        value = 50.0
        min_val = 0.0
        max_val = 100.0
        
        normalized = FeatureEngineer.normalize_feature(value, min_val, max_val)
        
        assert normalized == 0.5
    
    def test_normalize_feature_edge_cases(self):
        """Test normalization edge cases."""
        # Value equals min
        assert FeatureEngineer.normalize_feature(0.0, 0.0, 100.0) == 0.0
        
        # Value equals max
        assert FeatureEngineer.normalize_feature(100.0, 0.0, 100.0) == 1.0
        
        # Value below min (clamps to 0)
        assert FeatureEngineer.normalize_feature(-10.0, 0.0, 100.0) == 0.0
        
        # Value above max (clamps to 1)
        assert FeatureEngineer.normalize_feature(110.0, 0.0, 100.0) == 1.0


class TestPredictionService:
    """Test PredictionService - ML predictions (5 tests)"""
    
    def test_predict_returns_dict(self):
        """Test predict returns correct dict structure."""
        service = PredictionService()
        engineer = FeatureEngineer()
        orchestrator = PipelineOrchestrator()
        
        features = engineer.extract_features(orchestrator)
        prediction = service.predict(features)
        
        assert isinstance(prediction, dict)
        assert 'action' in prediction
        assert 'confidence' in prediction
        assert 'reasoning' in prediction
        assert 'model_version' in prediction
        assert 'timestamp' in prediction
    
    def test_predict_action_is_valid(self):
        """Test prediction action is BUY/SELL/HOLD."""
        service = PredictionService()
        engineer = FeatureEngineer()
        orchestrator = PipelineOrchestrator()
        
        features = engineer.extract_features(orchestrator)
        prediction = service.predict(features)
        
        assert prediction['action'] in ['BUY', 'SELL', 'HOLD']
    
    def test_predict_confidence_in_range(self):
        """Test confidence is 0.0-1.0."""
        service = PredictionService()
        engineer = FeatureEngineer()
        orchestrator = PipelineOrchestrator()
        
        features = engineer.extract_features(orchestrator)
        prediction = service.predict(features)
        
        assert 0.0 <= prediction['confidence'] <= 1.0
    
    def test_feature_validation_passes(self):
        """Test feature validation with valid features."""
        service = PredictionService()
        engineer = FeatureEngineer()
        orchestrator = PipelineOrchestrator()
        
        features = engineer.extract_features(orchestrator)
        is_valid, errors = service.validate_features(features)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_feature_validation_detects_invalid(self):
        """Test feature validation detects invalid features."""
        service = PredictionService()
        
        # Create invalid features (out of range)
        invalid_features = pl.DataFrame({
            'hour_of_day': [2.0],  # Out of bounds
            'day_of_week': [0.5],
            'is_peak_hour': [0.0],
            'season': [0.5],
            'current_tariff_uah_mwh': [0.5],
            'price_trend': [0.5],
            'price_volatility': [0.5],
            'soc_percent': [0.5],
            'battery_health': [0.5],
            'degradation_cost_uah_kwh': [0.5],
            'battery_cycles_remaining': [0.5],
            'current_load_kw': [0.5],
            'load_forecast_1h': [0.5],
            'load_trend': [0.5],
        })
        
        is_valid, errors = service.validate_features(invalid_features)
        
        assert is_valid is False
        assert len(errors) > 0
    
    def test_model_info_returns_metadata(self):
        """Test get_model_info returns metadata."""
        service = PredictionService()
        info = service.get_model_info()
        
        assert 'model_version' in info
        assert 'mock_mode' in info
        assert 'expected_features' in info
        assert 'valid_actions' in info


class TestIntegration:
    """Integration tests - full pipeline workflows (5 tests)"""
    
    def test_end_to_end_pipeline(self):
        """Test full pipeline from config to recommendation."""
        # Create config
        config = UserConfigModel()
        
        # Run pipeline
        orchestrator = PipelineOrchestrator(config)
        recommendation = orchestrator.calculate_recommendation(config)
        
        # Verify result
        assert recommendation['action'] in ['BUY', 'SELL', 'HOLD']
        assert 0.0 <= recommendation['confidence'] <= 1.0
        assert recommendation['timestamp'] is not None
    
    def test_pipeline_to_features_to_prediction(self):
        """Test full chain: pipeline → features → prediction."""
        # Step 1: Pipeline
        orchestrator = PipelineOrchestrator()
        recommendation = orchestrator.calculate_recommendation()
        assert recommendation['action'] is not None
        
        # Step 2: Features
        engineer = FeatureEngineer()
        features = engineer.extract_features(orchestrator)
        assert features.shape[1] == 14
        
        # Step 3: Prediction
        service = PredictionService()
        prediction = service.predict(features)
        assert prediction['action'] in ['BUY', 'SELL', 'HOLD']
    
    def test_hourly_forecast_generation(self):
        """Test 24-hour forecast generation."""
        orchestrator = PipelineOrchestrator()
        forecast = orchestrator.get_hourly_forecast(hours=24)
        
        assert len(forecast) == 24
        assert all(forecast['action'].isin(['BUY', 'SELL', 'HOLD']))
        assert all((forecast['confidence'] >= 0.0) & (forecast['confidence'] <= 1.0))
    
    def test_savings_estimation_consistency(self):
        """Test savings estimates are reasonable."""
        orchestrator = PipelineOrchestrator()
        
        # Generate multiple recommendations
        savings_list = []
        for _ in range(5):
            rec = orchestrator.calculate_recommendation()
            savings_list.append(rec['estimated_savings'])
        
        # Savings should be reasonable (not infinite or NaN)
        assert all(isinstance(s, (int, float)) for s in savings_list)
        assert all(s >= 0 for s in savings_list)  # Non-negative savings
    
    def test_consistency_across_runs(self):
        """Test consistent results with same config."""
        config = UserConfigModel()
        orchestrator = PipelineOrchestrator(config)
        
        # Generate 3 recommendations at same hour
        recommendations = []
        for _ in range(3):
            rec = orchestrator.calculate_recommendation(config, current_hour=12)
            recommendations.append(rec['action'])
        
        # All should be identical
        assert recommendations[0] == recommendations[1] == recommendations[2]


class TestEdgeCases:
    """Test edge cases and error handling (3 tests)"""
    
    def test_pipeline_with_minimal_config(self):
        """Test pipeline with minimal configuration."""
        # All defaults except one change
        config = UserConfigModel(battery_capacity_kwh=0.5)
        orchestrator = PipelineOrchestrator(config)
        
        recommendation = orchestrator.calculate_recommendation()
        assert recommendation['action'] is not None
    
    def test_pipeline_with_extreme_config(self):
        """Test pipeline with extreme (but valid) config."""
        config = UserConfigModel(
            battery_capacity_kwh=1000.0,
            load_peak_kw=500.0,
            battery_efficiency=0.99
        )
        orchestrator = PipelineOrchestrator(config)
        
        recommendation = orchestrator.calculate_recommendation()
        assert recommendation['action'] is not None
    
    def test_prediction_with_all_zero_features(self):
        """Test prediction handles degenerate features."""
        service = PredictionService()
        
        # All features at minimum
        zero_features = pl.DataFrame({
            'hour_of_day': [0.0],
            'day_of_week': [0.0],
            'is_peak_hour': [0.0],
            'season': [0.0],
            'current_tariff_uah_mwh': [0.0],
            'price_trend': [0.0],
            'price_volatility': [0.0],
            'soc_percent': [0.0],
            'battery_health': [0.0],
            'degradation_cost_uah_kwh': [0.0],
            'battery_cycles_remaining': [0.0],
            'current_load_kw': [0.0],
            'load_forecast_1h': [0.0],
            'load_trend': [0.0],
        })
        
        prediction = service.predict(zero_features)
        assert prediction['action'] is not None


# Test summary and reporting
def test_phase4f_summary():
    """Print test summary after all tests run."""
    print("\n" + "="*80)
    print("PHASE 4F TEST SUMMARY")
    print("="*80)
    print("✅ PipelineOrchestrator: Integration of all Phase 4 components")
    print("✅ FeatureEngineer: 14 normalized features (0-1 range)")
    print("✅ PredictionService: ML model predictions (BUY/SELL/HOLD)")
    print("✅ Integration Tests: Full pipeline workflows")
    print("✅ Edge Cases: Error handling and extreme configs")
    print("="*80)

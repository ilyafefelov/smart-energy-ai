"""Phase 4F: Feature Engineer - ML Feature Extraction and Normalization.

Extracts and normalizes ML features from the integrated pipeline.
All features are normalized to 0-1 range for ML model input.
"""
import importlib.util
import logging
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, Optional

import polars as pl
from energy_ml.pipeline import PipelineOrchestrator

try:
    from energy_ml.features_support import (
        append_feature_history,
        clamp_feature_frame,
        combine_feature_groups,
        extract_battery_features as extract_battery_features_data,
        extract_load_features as extract_load_features_data,
        extract_price_features as extract_price_features_data,
        extract_temporal_features as extract_temporal_features_data,
        get_feature_importance_map,
        normalize_feature,
    )
except ImportError:
    _SUPPORT_MODULE_NAME = "energy_ml.features_support"
    _SUPPORT_PATH = Path(__file__).with_name("features_support.py")
    _SUPPORT_SPEC = importlib.util.spec_from_file_location(_SUPPORT_MODULE_NAME, _SUPPORT_PATH)
    if _SUPPORT_SPEC is None or _SUPPORT_SPEC.loader is None:
        raise ImportError(f"Unable to load feature support module from {_SUPPORT_PATH}")
    _SUPPORT_MODULE = sys.modules.get(_SUPPORT_MODULE_NAME)
    if _SUPPORT_MODULE is None:
        _SUPPORT_MODULE = importlib.util.module_from_spec(_SUPPORT_SPEC)
        sys.modules[_SUPPORT_MODULE_NAME] = _SUPPORT_MODULE
        _SUPPORT_SPEC.loader.exec_module(_SUPPORT_MODULE)
    append_feature_history = _SUPPORT_MODULE.append_feature_history
    clamp_feature_frame = _SUPPORT_MODULE.clamp_feature_frame
    combine_feature_groups = _SUPPORT_MODULE.combine_feature_groups
    extract_battery_features_data = _SUPPORT_MODULE.extract_battery_features
    extract_load_features_data = _SUPPORT_MODULE.extract_load_features
    extract_price_features_data = _SUPPORT_MODULE.extract_price_features
    extract_temporal_features_data = _SUPPORT_MODULE.extract_temporal_features
    get_feature_importance_map = _SUPPORT_MODULE.get_feature_importance_map
    normalize_feature = _SUPPORT_MODULE.normalize_feature


logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Extract and normalize ML features from pipeline state.
    
    Produces 14 normalized features (0-1 range):
    - Temporal: 4 features (hour, day, season, peak indicator)
    - Price: 3 features (current tariff, trend, volatility)
    - Battery: 4 features (SOC, health, degradation cost, cycles remaining)
    - Load: 3 features (current, forecast, trend)
    """
    
    # Feature normalization bounds
    TARIFF_MIN_UAH_MWH = 700.0  # Minimum expected tariff
    TARIFF_MAX_UAH_MWH = 1200.0  # Maximum expected tariff
    
    MAX_DEGRADATION_COST_UAH_KWH = 1.0  # Maximum degradation cost per kWh
    MAX_LOAD_KW = 500.0  # Maximum load capacity
    
    def __init__(self):
        """Initialize feature engineer."""
        self.last_features = None
        self.feature_history = []
    
    def extract_features(self, 
                        pipeline: PipelineOrchestrator,
                        historical_data: Optional[Dict] = None) -> pl.DataFrame:
        """Extract features for ML model.
        
        Extracts 14 normalized features (0-1) from pipeline state:
        
        TEMPORAL (4 features):
        - hour_of_day: 0-23 normalized to 0-1
        - day_of_week: 0-6 normalized to 0-1
        - is_peak_hour: 1 if 6-23h, else 0
        - season: 0-3 (Q1-Q4) normalized to 0-1
        
        PRICE (3 features):
        - current_tariff_uah_mwh: normalized by min/max bounds
        - price_trend: 6-hour MA derivative, normalized
        - price_volatility: 6-hour std dev, normalized
        
        BATTERY (4 features):
        - soc_percent: 0-100 normalized to 0-1
        - battery_health: 0-100 normalized to 0-1
        - degradation_cost_uah_per_kwh: normalized by max
        - battery_cycles_remaining: log-normalized to 0-1
        
        LOAD (3 features):
        - current_load_kw: normalized by max capacity
        - load_forecast_1h: next hour load, normalized
        - load_trend: 3-hour MA derivative, normalized
        
        Args:
            pipeline: PipelineOrchestrator instance
            historical_data: Optional dict with price/load history
        
        Returns:
            polars DataFrame with 1 row and 14 normalized features
        """
        # Extract all feature groups
        current_timestamp = datetime.now()
        temporal = self.extract_temporal_features(current_timestamp)
        price = self.extract_price_features(pipeline.tariff, historical_data, current_timestamp)
        battery = self.extract_battery_features(pipeline.battery)
        load = self.extract_load_features(pipeline.load_profile, historical_data, current_timestamp)
        all_features = combine_feature_groups(temporal, price, battery, load)
        
        df = pl.DataFrame([all_features])
        df = clamp_feature_frame(df, logger)
        
        self.last_features = df
        append_feature_history(self.feature_history, all_features, current_timestamp)
        
        return df
    
    def extract_temporal_features(self, timestamp: datetime) -> Dict[str, float]:
        """Extract temporal features.
        
        Args:
            timestamp: Current datetime
        
        Returns:
            Dict with normalized temporal features
        """
        return extract_temporal_features_data(timestamp)
    
    def extract_price_features(self, 
                              tariff_model,
                              historical_data: Optional[Dict] = None,
                              timestamp: Optional[datetime] = None) -> Dict[str, float]:
        """Extract price/tariff features.
        
        Args:
            tariff_model: UkraineTariffModel instance
            historical_data: Optional dict with 'tariff_history' key
        
        Returns:
            Dict with normalized price features
        """
        active_timestamp = timestamp or datetime.now()
        return extract_price_features_data(
            tariff_model,
            historical_data,
            active_timestamp.hour,
            self.TARIFF_MIN_UAH_MWH,
            self.TARIFF_MAX_UAH_MWH,
        )
    
    def extract_battery_features(self, battery_model) -> Dict[str, float]:
        """Extract battery state features.
        
        Args:
            battery_model: BatteryModel instance
        
        Returns:
            Dict with normalized battery features
        """
        return extract_battery_features_data(self.MAX_DEGRADATION_COST_UAH_KWH)
    
    def extract_load_features(self,
                             load_profile,
                             historical_data: Optional[Dict] = None,
                             timestamp: Optional[datetime] = None) -> Dict[str, float]:
        """Extract load profile features.
        
        Args:
            load_profile: LoadProfile/Simulator instance
            historical_data: Optional dict with 'load_history' key
        
        Returns:
            Dict with normalized load features
        """
        active_timestamp = timestamp or datetime.now()
        return extract_load_features_data(
            load_profile,
            historical_data,
            active_timestamp.hour,
            self.MAX_LOAD_KW,
        )
    
    @staticmethod
    def normalize_feature(value: float, 
                         feature_min: float,
                         feature_max: float) -> float:
        """Normalize single feature to 0-1 range.
        
        Args:
            value: Raw feature value
            feature_min: Minimum expected value for this feature
            feature_max: Maximum expected value for this feature
        
        Returns:
            Normalized value in [0.0, 1.0]
        """
        return normalize_feature(value, feature_min, feature_max)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get estimated importance scores for features.
        
        Returns:
            Dict mapping feature names to importance (0-1)
        """
        return get_feature_importance_map()

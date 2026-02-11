"""Phase 4F: Feature Engineer - ML Feature Extraction and Normalization.

Extracts and normalizes ML features from the integrated pipeline.
All features are normalized to 0-1 range for ML model input.
"""
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
import math

import polars as pl
from energy_ml.pipeline import PipelineOrchestrator


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
        temporal = self.extract_temporal_features(datetime.now())
        price = self.extract_price_features(pipeline.tariff, historical_data)
        battery = self.extract_battery_features(pipeline.battery)
        load = self.extract_load_features(pipeline.load_profile, historical_data)
        
        # Combine all features
        all_features = {
            # Temporal
            'hour_of_day': temporal['hour_of_day'],
            'day_of_week': temporal['day_of_week'],
            'is_peak_hour': temporal['is_peak_hour'],
            'season': temporal['season'],
            
            # Price
            'current_tariff_uah_mwh': price['current_tariff'],
            'price_trend': price['trend'],
            'price_volatility': price['volatility'],
            
            # Battery
            'soc_percent': battery['soc'],
            'battery_health': battery['health'],
            'degradation_cost_uah_kwh': battery['degradation_cost'],
            'battery_cycles_remaining': battery['cycles_remaining'],
            
            # Load
            'current_load_kw': load['current_load'],
            'load_forecast_1h': load['forecast_1h'],
            'load_trend': load['trend'],
        }
        
        # Create polars DataFrame
        df = pl.DataFrame([all_features])
        
        # Validate all values are in 0-1 range
        for col in df.columns:
            min_val = df[col].min()
            max_val = df[col].max()
            
            if min_val < 0.0 or max_val > 1.0:
                logger.warning(f"Feature {col} out of bounds: [{min_val}, {max_val}]")
                # Clamp to valid range
                df = df.with_columns(pl.col(col).clip(0.0, 1.0))
        
        # Store for analysis
        self.last_features = df
        self.feature_history.append({
            'timestamp': datetime.now().isoformat(),
            'features': all_features.copy()
        })
        
        return df
    
    def extract_temporal_features(self, timestamp: datetime) -> Dict[str, float]:
        """Extract temporal features.
        
        Args:
            timestamp: Current datetime
        
        Returns:
            Dict with normalized temporal features
        """
        hour = timestamp.hour
        day_of_week = timestamp.weekday()  # 0=Monday, 6=Sunday
        month = timestamp.month
        quarter = (month - 1) // 3  # 0-3 for Q1-Q4
        
        # Normalize to 0-1
        hour_normalized = hour / 23.0
        day_normalized = day_of_week / 6.0
        season_normalized = quarter / 3.0
        
        # Peak hour: 6am-11pm (6-22h inclusive, 23h exclusive)
        is_peak = 1.0 if 6 <= hour < 23 else 0.0
        
        return {
            'hour_of_day': self.normalize_feature(hour_normalized, 0.0, 1.0),
            'day_of_week': self.normalize_feature(day_normalized, 0.0, 1.0),
            'is_peak_hour': is_peak,
            'season': self.normalize_feature(season_normalized, 0.0, 1.0),
        }
    
    def extract_price_features(self, 
                              tariff_model,
                              historical_data: Optional[Dict] = None) -> Dict[str, float]:
        """Extract price/tariff features.
        
        Args:
            tariff_model: UkraineTariffModel instance
            historical_data: Optional dict with 'tariff_history' key
        
        Returns:
            Dict with normalized price features
        """
        current_hour = datetime.now().hour
        current_rate = tariff_model.get_hourly_rate(current_hour)
        
        # Normalize current tariff
        tariff_norm = self.normalize_feature(
            current_rate,
            self.TARIFF_MIN_UAH_MWH,
            self.TARIFF_MAX_UAH_MWH
        )
        
        # Calculate price trend (6-hour moving average)
        trend = 0.5  # Default neutral trend
        if historical_data and 'tariff_history' in historical_data:
            history = historical_data['tariff_history']
            if len(history) >= 6:
                recent_avg = sum(history[-6:]) / 6
                older_avg = sum(history[-12:-6]) / 6
                trend_value = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
                trend = self.normalize_feature(trend_value, -0.1, 0.1)
        
        # Calculate price volatility (6-hour std dev)
        volatility = 0.3  # Default moderate volatility
        if historical_data and 'tariff_history' in historical_data:
            history = historical_data['tariff_history']
            if len(history) >= 6:
                recent_prices = history[-6:]
                mean_price = sum(recent_prices) / len(recent_prices)
                variance = sum((p - mean_price) ** 2 for p in recent_prices) / len(recent_prices)
                std_dev = math.sqrt(variance)
                volatility_pct = (std_dev / mean_price) if mean_price > 0 else 0
                volatility = self.normalize_feature(volatility_pct, 0.0, 0.2)
        
        return {
            'current_tariff': tariff_norm,
            'trend': trend,
            'volatility': volatility,
        }
    
    def extract_battery_features(self, battery_model) -> Dict[str, float]:
        """Extract battery state features.
        
        Args:
            battery_model: BatteryModel instance
        
        Returns:
            Dict with normalized battery features
        """
        soc = 60.0  # Mock SOC (60%)
        health = 95.0  # Mock health (95%)
        cycles_remaining = 5000  # Mock cycles remaining
        
        # Get degradation cost estimate
        # Assume: battery cost 50,000 UAH, capacity 10kWh, cycles 5000
        battery_cost_uah = 50000
        est_degradation_cost = battery_cost_uah / (max(cycles_remaining, 100) * 10)
        
        # Normalize features
        soc_norm = soc / 100.0
        health_norm = health / 100.0
        degradation_norm = self.normalize_feature(
            est_degradation_cost,
            0.0,
            self.MAX_DEGRADATION_COST_UAH_KWH
        )
        
        # Log-normalize cycles remaining (log scale 1-10k cycles → 0-1)
        cycles_log = math.log10(max(cycles_remaining, 1))
        cycles_norm = cycles_log / math.log10(10000)  # Normalize by log(10k)
        cycles_norm = max(0.0, min(1.0, cycles_norm))
        
        return {
            'soc': soc_norm,
            'health': health_norm,
            'degradation_cost': degradation_norm,
            'cycles_remaining': cycles_norm,
        }
    
    def extract_load_features(self,
                             load_profile,
                             historical_data: Optional[Dict] = None) -> Dict[str, float]:
        """Extract load profile features.
        
        Args:
            load_profile: LoadProfile/Simulator instance
            historical_data: Optional dict with 'load_history' key
        
        Returns:
            Dict with normalized load features
        """
        current_hour = datetime.now().hour
        next_hour = (current_hour + 1) % 24
        
        current_load = load_profile.get_hourly_coefficient(current_hour, 0) * 10.0  # Mock peak 10kW
        forecast_load = load_profile.get_hourly_coefficient(next_hour, 0) * 10.0
        
        # Normalize by max capacity
        current_load_norm = self.normalize_feature(
            current_load,
            0.0,
            self.MAX_LOAD_KW
        )
        forecast_load_norm = self.normalize_feature(
            forecast_load,
            0.0,
            self.MAX_LOAD_KW
        )
        
        # Calculate load trend (3-hour MA derivative)
        trend = 0.5  # Default neutral
        if historical_data and 'load_history' in historical_data:
            history = historical_data['load_history']
            if len(history) >= 6:
                recent_avg = sum(history[-3:]) / 3
                older_avg = sum(history[-6:-3]) / 3
                trend_value = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
                trend = self.normalize_feature(trend_value, -0.5, 0.5)
        
        return {
            'current_load': current_load_norm,
            'forecast_1h': forecast_load_norm,
            'trend': trend,
        }
    
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
        if feature_max <= feature_min:
            return 0.5
        
        normalized = (value - feature_min) / (feature_max - feature_min)
        # Clamp to [0, 1]
        return max(0.0, min(1.0, normalized))
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get estimated importance scores for features.
        
        Returns:
            Dict mapping feature names to importance (0-1)
        """
        # These are reasonable heuristic importance estimates
        # In real scenario, would use SHAP or permutation importance from model
        return {
            'hour_of_day': 0.15,
            'is_peak_hour': 0.18,
            'current_tariff_uah_mwh': 0.16,
            'price_trend': 0.10,
            'soc_percent': 0.12,
            'battery_health': 0.08,
            'current_load_kw': 0.07,
            'day_of_week': 0.05,
            'load_forecast_1h': 0.05,
            'degradation_cost_uah_kwh': 0.02,
            'price_volatility': 0.02,
            'season': 0.01,
            'load_trend': 0.01,
            'battery_cycles_remaining': 0.01,
        }

"""
Phase 1: Feature Store Implementation
Real-time feature serving and batch feature computation for energy optimization
"""

import importlib.util
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import sys

import polars as pl
import numpy as np
from pydantic import BaseModel, Field

try:
    from energy_ml.mlops.feature_store_support import (
        build_batch_feature_row,
        build_empty_energy_frame,
        build_load_demand,
        build_real_time_feature_row,
        build_realistic_price,
        build_solar_power,
        generate_hourly_timestamps,
        read_feature_view_metadata,
        write_feature_view_metadata,
    )
except ImportError:
    _SUPPORT_MODULE_NAME = "energy_ml.mlops.feature_store_support"
    _SUPPORT_PATH = Path(__file__).with_name("feature_store_support.py")
    _SUPPORT_SPEC = importlib.util.spec_from_file_location(_SUPPORT_MODULE_NAME, _SUPPORT_PATH)
    if _SUPPORT_SPEC is None or _SUPPORT_SPEC.loader is None:
        raise ImportError(f"Unable to load feature store support module from {_SUPPORT_PATH}")
    _SUPPORT_MODULE = sys.modules.get(_SUPPORT_MODULE_NAME)
    if _SUPPORT_MODULE is None:
        _SUPPORT_MODULE = importlib.util.module_from_spec(_SUPPORT_SPEC)
        sys.modules[_SUPPORT_MODULE_NAME] = _SUPPORT_MODULE
        _SUPPORT_SPEC.loader.exec_module(_SUPPORT_MODULE)
    build_batch_feature_row = _SUPPORT_MODULE.build_batch_feature_row
    build_empty_energy_frame = _SUPPORT_MODULE.build_empty_energy_frame
    build_load_demand = _SUPPORT_MODULE.build_load_demand
    build_real_time_feature_row = _SUPPORT_MODULE.build_real_time_feature_row
    build_realistic_price = _SUPPORT_MODULE.build_realistic_price
    build_solar_power = _SUPPORT_MODULE.build_solar_power
    generate_hourly_timestamps = _SUPPORT_MODULE.generate_hourly_timestamps
    read_feature_view_metadata = _SUPPORT_MODULE.read_feature_view_metadata
    write_feature_view_metadata = _SUPPORT_MODULE.write_feature_view_metadata

logger = logging.getLogger(__name__)

class ValueType:
    """Feature value types for type safety"""
    FLOAT = "float64"
    INTEGER = "int64"
    STRING = "string"
    BOOLEAN = "boolean"
    TIMESTAMP = "datetime"

@dataclass
class Feature:
    """Feature definition with metadata"""
    name: str
    value_type: str
    description: str = ""
    source: str = ""
    
    def to_dict(self) -> Dict[str, str]:
        return asdict(self)

@dataclass 
class FeatureView:
    """Feature view definition for batch and online serving"""
    name: str
    entities: List[str]  # Primary keys [user_id, timestamp]
    features: List[Feature]
    online: bool = True  # Enable online serving
    batch_source: Optional[str] = None  # Path to batch data source
    ttl_hours: int = 24  # Time-to-live for online features
    
    def get_feature_names(self) -> List[str]:
        """Get list of feature names"""
        return [f.name for f in self.features]
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'entities': self.entities,
            'features': [f.to_dict() for f in self.features],
            'online': self.online,
            'batch_source': self.batch_source,
            'ttl_hours': self.ttl_hours
        }

class ParquetSource:
    """Parquet file data source for feature store"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        
    def read(self) -> pl.DataFrame:
        """Read data from parquet file"""
        if not self.file_path.exists():
            return build_empty_energy_frame()
            
        return pl.read_parquet(self.file_path)
        
    def write(self, df: pl.DataFrame):
        """Write data to parquet file"""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(self.file_path)

class FeatureStore:
    """Production feature store for energy optimization features"""
    
    def __init__(self, store_path: str = "energy_ml/mlops/feature_store"):
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)
        
        self.online_path = self.store_path / "online"
        self.batch_path = self.store_path / "batch" 
        self.metadata_path = self.store_path / "metadata"
        
        for path in [self.online_path, self.batch_path, self.metadata_path]:
            path.mkdir(exist_ok=True)
            
        self.feature_views: Dict[str, FeatureView] = {}
        self._load_feature_views()
        
        # Initialize core energy feature view
        self._initialize_energy_features()
        
    def register_feature_view(self, feature_view: FeatureView):
        """Register a new feature view
        
        Args:
            feature_view: FeatureView to register
        """
        self.feature_views[feature_view.name] = feature_view
        
        # Save metadata
        metadata_file = self.metadata_path / f"{feature_view.name}.json"
        write_feature_view_metadata(metadata_file, feature_view)
            
        logger.info(f"Registered feature view: {feature_view.name}")
        
    def load_online_features(self, 
                           feature_view_name: str,
                           entity_keys: Dict[str, Any]) -> Dict[str, Any]:
        """Load online features for real-time prediction.
        
        Args:
            feature_view_name: Name of feature view
            entity_keys: Dictionary with entity values (user_id, timestamp, etc.)
            
        Returns:
            Dictionary with feature values
        """
        if feature_view_name not in self.feature_views:
            raise ValueError(f"Feature view not found: {feature_view_name}")
            
        feature_view = self.feature_views[feature_view_name]
        
        if not feature_view.online:
            raise ValueError(f"Feature view {feature_view_name} not configured for online serving")
            
        # Load online feature cache
        cache_file = self.online_path / f"{feature_view_name}.parquet"
        
        if not cache_file.exists():
            # Generate fresh features if cache doesn't exist
            return self._generate_real_time_features(feature_view, entity_keys)
            
        try:
            df = pl.read_parquet(cache_file)
            
            # Filter by entity keys
            query_conditions = []
            for entity, value in entity_keys.items():
                if entity in df.columns:
                    query_conditions.append(pl.col(entity) == value)
                    
            if query_conditions:
                filtered_df = df.filter(pl.all(query_conditions))
                
                if len(filtered_df) > 0:
                    # Return most recent record
                    latest_record = filtered_df.sort('timestamp', descending=True).row(0, named=True)
                    
                    # Check TTL
                    if 'timestamp' in latest_record:
                        feature_age = datetime.now() - latest_record['timestamp']
                        if feature_age < timedelta(hours=feature_view.ttl_hours):
                            return latest_record
                            
        except Exception as e:
            logger.warning(f"Failed to load cached features: {e}")
            
        # Generate fresh features if cache miss or expired
        return self._generate_real_time_features(feature_view, entity_keys)
        
    def load_batch_features(self, 
                          feature_view_name: str,
                          start_time: datetime,
                          end_time: datetime,
                          entity_filter: Optional[Dict[str, Any]] = None) -> pl.DataFrame:
        """Load batch features for training.
        
        Args:
            feature_view_name: Name of feature view
            start_time: Start of time range
            end_time: End of time range 
            entity_filter: Optional entity filter (e.g., specific user_id)
            
        Returns:
            Polars DataFrame with batch features
        """
        if feature_view_name not in self.feature_views:
            raise ValueError(f"Feature view not found: {feature_view_name}")
            
        feature_view = self.feature_views[feature_view_name]
        
        # Load from batch source
        if feature_view.batch_source:
            source = ParquetSource(feature_view.batch_source)
            df = source.read()
        else:
            # Load from online cache as fallback
            cache_file = self.online_path / f"{feature_view_name}.parquet"
            if cache_file.exists():
                df = pl.read_parquet(cache_file)
            else:
                return pl.DataFrame()
                
        # Apply time filter
        if 'timestamp' in df.columns:
            df = df.filter(
                (pl.col('timestamp') >= start_time) & 
                (pl.col('timestamp') <= end_time)
            )
            
        # Apply entity filter
        if entity_filter:
            for entity, value in entity_filter.items():
                if entity in df.columns:
                    df = df.filter(pl.col(entity) == value)
                    
        return df
        
    def materialize_features(self, 
                           feature_view_name: str,
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None):
        """Materialize features from batch to online store
        
        Args:
            feature_view_name: Name of feature view to materialize
            start_time: Optional start time (defaults to 7 days ago)
            end_time: Optional end time (defaults to now)
        """
        if feature_view_name not in self.feature_views:
            raise ValueError(f"Feature view not found: {feature_view_name}")
            
        feature_view = self.feature_views[feature_view_name]
        
        if not start_time:
            start_time = datetime.now() - timedelta(days=7)
        if not end_time:
            end_time = datetime.now()
            
        logger.info(f"Materializing features for {feature_view_name} from {start_time} to {end_time}")
        
        # Generate feature data for time range
        features_df = self._generate_batch_features(feature_view, start_time, end_time)
        
        if len(features_df) == 0:
            logger.warning(f"No features generated for {feature_view_name}")
            return
            
        # Save to online cache
        cache_file = self.online_path / f"{feature_view_name}.parquet"
        features_df.write_parquet(cache_file)
        
        # Also save to batch store if configured
        if feature_view.batch_source:
            source = ParquetSource(feature_view.batch_source)
            
            # Merge with existing data
            try:
                existing_df = source.read()
                if len(existing_df) > 0:
                    # Remove overlapping time range and append new data
                    existing_df = existing_df.filter(
                        (pl.col('timestamp') < start_time) | 
                        (pl.col('timestamp') > end_time)
                    )
                    features_df = pl.concat([existing_df, features_df])
            except Exception:
                pass  # If no existing data, just use new features
                
            source.write(features_df)
            
        logger.info(f"Materialized {len(features_df)} feature records for {feature_view_name}")
        
    def _initialize_energy_features(self):
        """Initialize core energy optimization feature view"""
        
        # Define energy features
        energy_features = FeatureView(
            name="energy_features",
            entities=["user_id", "timestamp"],
            features=[
                Feature("battery_soc", ValueType.FLOAT, "Battery state of charge (0-1)"),
                Feature("grid_price_uah_kwh", ValueType.FLOAT, "Grid electricity price UAH/kWh"),
                Feature("solar_generation_kw", ValueType.FLOAT, "Solar generation power kW"),
                Feature("wind_generation_kw", ValueType.FLOAT, "Wind generation power kW"),
                Feature("load_demand_kw", ValueType.FLOAT, "Electrical load demand kW"),
                Feature("temperature_celsius", ValueType.FLOAT, "Ambient temperature °C"),
                Feature("is_peak_hour", ValueType.BOOLEAN, "Whether current hour is peak pricing"),
                Feature("day_of_week", ValueType.INTEGER, "Day of week (0=Monday)"),
                Feature("hour_of_day", ValueType.INTEGER, "Hour of day (0-23)"),
                Feature("price_ma_24h", ValueType.FLOAT, "24-hour moving average price"),
                Feature("load_ma_7d", ValueType.FLOAT, "7-day moving average load"),
                Feature("generation_forecast_1h", ValueType.FLOAT, "1-hour generation forecast"),
            ],
            online=True,
            batch_source="energy_ml/data/energy_features.parquet",
            ttl_hours=6  # Features valid for 6 hours
        )
        
        self.register_feature_view(energy_features)
        
        # Initialize with sample data if empty
        self.materialize_features("energy_features")
        
    def _generate_real_time_features(self, 
                                   feature_view: FeatureView,
                                   entity_keys: Dict[str, Any]) -> Dict[str, Any]:
        """Generate real-time features for immediate use"""
        return build_real_time_feature_row(datetime.now(), entity_keys)
        
    def _generate_batch_features(self, 
                               feature_view: FeatureView,
                               start_time: datetime,
                               end_time: datetime) -> pl.DataFrame:
        """Generate batch features for time range"""
        timestamps = generate_hourly_timestamps(start_time, end_time)
            
        if not timestamps:
            return pl.DataFrame()
        return pl.DataFrame([build_batch_feature_row(timestamp) for timestamp in timestamps])
        
    def _generate_realistic_price(self, timestamp: datetime) -> float:
        """Generate realistic electricity price based on time"""
        return build_realistic_price(timestamp)
        
    def _generate_solar_power(self, timestamp: datetime) -> float:
        """Generate realistic solar power based on time and season"""
        return build_solar_power(timestamp)
        
    def _generate_load_demand(self, timestamp: datetime) -> float:
        """Generate realistic load demand based on time and day"""
        return build_load_demand(timestamp)
        
    def _load_feature_views(self):
        """Load feature views from metadata"""
        for metadata_file in self.metadata_path.glob("*.json"):
            try:
                view_data = read_feature_view_metadata(metadata_file)
                    
                features = [Feature(**f) for f in view_data['features']]
                
                feature_view = FeatureView(
                    name=view_data['name'],
                    entities=view_data['entities'],
                    features=features,
                    online=view_data.get('online', True),
                    batch_source=view_data.get('batch_source'),
                    ttl_hours=view_data.get('ttl_hours', 24)
                )
                
                self.feature_views[feature_view.name] = feature_view
                
            except Exception as e:
                logger.error(f"Failed to load feature view {metadata_file}: {e}")

# Singleton feature store instance
_feature_store_instance = None

def get_feature_store() -> FeatureStore:
    """Get global feature store instance"""
    global _feature_store_instance
    if _feature_store_instance is None:
        _feature_store_instance = FeatureStore()
    return _feature_store_instance

# Pre-defined energy feature view for easy import
user_energy_features = FeatureView(
    name="energy_features",
    entities=["user_id", "timestamp"], 
    features=[
        Feature("battery_soc", ValueType.FLOAT),
        Feature("grid_price_uah_kwh", ValueType.FLOAT), 
        Feature("solar_generation_kw", ValueType.FLOAT),
        Feature("load_demand_kw", ValueType.FLOAT),
        Feature("temperature_celsius", ValueType.FLOAT),
        Feature("is_peak_hour", ValueType.BOOLEAN),
        Feature("day_of_week", ValueType.INTEGER),
        Feature("hour_of_day", ValueType.INTEGER)
    ],
    online=True,
    batch_source="data/energy_features.parquet"
)
"""
Phase 1: Feature Store Implementation
Real-time feature serving and batch feature computation for energy optimization
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import json

import polars as pl
import numpy as np
from pydantic import BaseModel, Field

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
            # Create empty DataFrame with expected schema for energy features
            return pl.DataFrame({
                'user_id': pl.Series([], dtype=pl.Utf8),
                'timestamp': pl.Series([], dtype=pl.Datetime),
                'battery_soc': pl.Series([], dtype=pl.Float64),
                'grid_price_uah_kwh': pl.Series([], dtype=pl.Float64),
                'solar_generation_kw': pl.Series([], dtype=pl.Float64),
                'wind_generation_kw': pl.Series([], dtype=pl.Float64),
                'load_demand_kw': pl.Series([], dtype=pl.Float64),
                'temperature_celsius': pl.Series([], dtype=pl.Float64),
                'is_peak_hour': pl.Series([], dtype=pl.Boolean),
                'day_of_week': pl.Series([], dtype=pl.Int32),
                'hour_of_day': pl.Series([], dtype=pl.Int32)
            })
            
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
        with open(metadata_file, 'w') as f:
            json.dump(feature_view.to_dict(), f, indent=2)
            
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
        
        current_time = datetime.now()
        
        # Base real-time features (simulated with realistic values)
        features = {
            'user_id': entity_keys.get('user_id', 'default_user'),
            'timestamp': current_time,
            'battery_soc': 0.6 + 0.3 * np.random.random(),  # 60-90%
            'grid_price_uah_kwh': 8.0 + 4.0 * np.random.random(),  # 8-12 UAH/kWh
            'solar_generation_kw': max(0, 3.0 * np.sin(np.pi * (current_time.hour - 6) / 12)),  # Solar curve
            'wind_generation_kw': 1.0 + 2.0 * np.random.random(),  # 1-3 kW wind
            'load_demand_kw': 2.0 + 3.0 * np.random.random(),  # 2-5 kW load
            'temperature_celsius': 15.0 + 10.0 * np.random.random(),  # 15-25°C
            'is_peak_hour': 6 <= current_time.hour < 23,
            'day_of_week': current_time.weekday(),
            'hour_of_day': current_time.hour,
        }
        
        # Add computed features
        features['price_ma_24h'] = features['grid_price_uah_kwh'] * (0.9 + 0.2 * np.random.random())
        features['load_ma_7d'] = features['load_demand_kw'] * (0.8 + 0.4 * np.random.random())
        features['generation_forecast_1h'] = (features['solar_generation_kw'] + features['wind_generation_kw']) * 1.1
        
        return features
        
    def _generate_batch_features(self, 
                               feature_view: FeatureView,
                               start_time: datetime,
                               end_time: datetime) -> pl.DataFrame:
        """Generate batch features for time range"""
        
        # Generate hourly features for the time range
        timestamps = []
        current_time = start_time.replace(minute=0, second=0, microsecond=0)
        
        while current_time <= end_time:
            timestamps.append(current_time)
            current_time += timedelta(hours=1)
            
        if not timestamps:
            return pl.DataFrame()
            
        # Generate realistic energy data for each timestamp
        data_rows = []
        for ts in timestamps:
            row = {
                'user_id': 'default_user',
                'timestamp': ts,
                'battery_soc': 0.3 + 0.6 * np.random.random(),  # 30-90%
                'grid_price_uah_kwh': self._generate_realistic_price(ts),
                'solar_generation_kw': self._generate_solar_power(ts),
                'wind_generation_kw': 0.5 + 2.5 * np.random.random(),
                'load_demand_kw': self._generate_load_demand(ts),
                'temperature_celsius': 10 + 20 * np.random.random(),
                'is_peak_hour': 6 <= ts.hour < 23,
                'day_of_week': ts.weekday(),
                'hour_of_day': ts.hour,
            }
            
            # Add computed features
            row['price_ma_24h'] = row['grid_price_uah_kwh'] * (0.9 + 0.2 * np.random.random())
            row['load_ma_7d'] = row['load_demand_kw'] * (0.8 + 0.4 * np.random.random())
            row['generation_forecast_1h'] = (row['solar_generation_kw'] + row['wind_generation_kw']) * 1.05
            
            data_rows.append(row)
            
        return pl.DataFrame(data_rows)
        
    def _generate_realistic_price(self, timestamp: datetime) -> float:
        """Generate realistic electricity price based on time"""
        base_price = 8.0
        
        # Peak hour premium
        if 6 <= timestamp.hour < 23:
            base_price *= 1.3
            
        # Day of week effect (higher on weekdays)
        if timestamp.weekday() < 5:  # Monday-Friday
            base_price *= 1.1
            
        # Seasonal variation (higher in winter)
        if timestamp.month in [12, 1, 2]:
            base_price *= 1.2
        elif timestamp.month in [6, 7, 8]:
            base_price *= 0.9
            
        # Add random variation
        base_price *= (0.8 + 0.4 * np.random.random())
        
        return round(base_price, 2)
        
    def _generate_solar_power(self, timestamp: datetime) -> float:
        """Generate realistic solar power based on time and season"""
        if timestamp.hour < 6 or timestamp.hour > 18:
            return 0.0
            
        # Solar curve (sine wave from sunrise to sunset)
        hour_angle = np.pi * (timestamp.hour - 6) / 12
        solar_factor = np.sin(hour_angle)
        
        # Seasonal variation
        month_factor = 0.5 + 0.5 * np.cos(2 * np.pi * (timestamp.month - 6) / 12)
        
        # Random weather effect
        weather_factor = 0.3 + 0.7 * np.random.random()
        
        max_power = 5.0  # 5kW peak solar
        return max(0, max_power * solar_factor * month_factor * weather_factor)
        
    def _generate_load_demand(self, timestamp: datetime) -> float:
        """Generate realistic load demand based on time and day"""
        base_load = 2.0
        
        # Daily pattern (higher during day, lower at night)
        if 6 <= timestamp.hour <= 22:
            time_factor = 1.5 + 0.5 * np.sin(2 * np.pi * (timestamp.hour - 6) / 16)
        else:
            time_factor = 0.5 + 0.3 * np.random.random()
            
        # Weekday vs weekend
        if timestamp.weekday() >= 5:  # Weekend
            time_factor *= 0.8
            
        # Random variation
        random_factor = 0.7 + 0.6 * np.random.random()
        
        return base_load * time_factor * random_factor
        
    def _load_feature_views(self):
        """Load feature views from metadata"""
        for metadata_file in self.metadata_path.glob("*.json"):
            try:
                with open(metadata_file) as f:
                    view_data = json.load(f)
                    
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
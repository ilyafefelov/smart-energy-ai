"""
NVTabular GPU Engine for Feature Engineering

GPU-accelerated engine using NVIDIA NVTabular for high-performance
feature engineering on large datasets.

Thesis Relevance: Demonstrates GPU-accelerated processing for
terabyte-scale energy data in high-performance environments.
"""

import logging
from typing import Dict, List, Optional, Union, Tuple, Any
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Defensive imports for GPU dependencies
try:
    import nvtabular as nvt
    import cupy as cp
    import cudf
    HAS_GPU = True
    GPU_IMPORT_ERROR = None
except ImportError as e:
    HAS_GPU = False
    GPU_IMPORT_ERROR = str(e)
    # Create placeholder classes to prevent import errors
    nvt = None
    cp = None
    cudf = None

logger = logging.getLogger(__name__)


class NVTabularEngine:
    """
    GPU-accelerated feature engineering engine using NVTabular.
    
    Designed for:
    - High-performance GPU instances (AWS p3, p4 instances)
    - Terabyte-scale data processing
    - Production environments with GPU resources
    - Research/development with CUDA support
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize NVTabular engine with GPU availability check.
        
        Args:
            config: Optional configuration dictionary
            
        Raises:
            ImportError: If NVTabular/CUDA not available
        """
        if not HAS_GPU:
            raise ImportError(
                f"NVTabular/CUDA not available: {GPU_IMPORT_ERROR}. "
                "Install with: pip install nvtabular cupy-cuda11x"
            )
            
        self.config = config or {}
        self.engine_name = "nvtabular_gpu"
        
        # Check GPU availability
        try:
            self.gpu_count = cp.cuda.runtime.getDeviceCount()
            self.gpu_memory = self._get_gpu_memory()
            
            if self.gpu_count == 0:
                raise RuntimeError("No CUDA GPUs detected")
                
        except Exception as e:
            raise RuntimeError(f"GPU initialization failed: {e}")
            
        # Configure NVTabular workflow
        self.workflow = None
        self._setup_workflow()
        
        logger.info(
            f"Initialized NVTabular engine with {self.gpu_count} GPU(s), "
            f"{self.gpu_memory:.1f} GB total memory"
        )
        
    def _get_gpu_memory(self) -> float:
        """Get total GPU memory in GB across all devices."""
        total_memory = 0
        for i in range(self.gpu_count):
            with cp.cuda.Device(i):
                memory_info = cp.cuda.runtime.memGetInfo()
                total_memory += memory_info[1]  # Total memory
        return total_memory / (1024**3)  # Convert to GB
        
    def _setup_workflow(self):
        """Setup NVTabular workflow for feature engineering."""
        if not HAS_GPU:
            return
            
        # Define feature engineering operations using NVTabular
        # This will be configured based on the specific features needed
        self.workflow_config = {
            "market_features": [
                "price_current", "price_24h_avg", "price_24h_std",
                "price_lag_1h", "price_lag_24h", "price_diff_1h"
            ],
            "weather_features": [
                "solar_ghi", "solar_24h_avg", "temp_current",
                "temp_24h_avg", "wind_current"
            ],
            "client_features": [
                "soc_current", "soc_previous", "soc_change",
                "battery_temperature", "load_current"
            ]
        }
        
    def process_features(self, 
                        market_data: Union[pd.DataFrame, 'cudf.DataFrame'],
                        weather_data: Union[pd.DataFrame, 'cudf.DataFrame'],
                        client_state: Union[pd.DataFrame, 'cudf.DataFrame']) -> 'cudf.DataFrame':
        """
        Process features using NVTabular GPU acceleration.
        
        Args:
            market_data: Market price data
            weather_data: Weather forecast data
            client_state: Client battery/system state
            
        Returns:
            Feature matrix as CuDF DataFrame
        """
        if not HAS_GPU:
            raise RuntimeError("GPU processing not available")
            
        logger.info("Starting NVTabular GPU feature processing pipeline")
        
        # Convert to CuDF DataFrames if needed
        market_cudf = self._ensure_cudf(market_data)
        weather_cudf = self._ensure_cudf(weather_data)
        client_cudf = self._ensure_cudf(client_state)
        
        # Process market features
        market_features = self._create_market_features_gpu(market_cudf)
        
        # Process weather features  
        weather_features = self._create_weather_features_gpu(weather_cudf)
        
        # Process client state features
        client_features = self._create_client_features_gpu(client_cudf)
        
        # Join all features on timestamp
        feature_matrix = self._join_features_gpu(
            market_features, weather_features, client_features
        )
        
        # Add derived features
        feature_matrix = self._add_derived_features_gpu(feature_matrix)
        
        logger.info(f"NVTabular processing complete: {feature_matrix.shape} features generated")
        return feature_matrix
        
    def _ensure_cudf(self, df: Union[pd.DataFrame, 'cudf.DataFrame']) -> 'cudf.DataFrame':
        """Convert DataFrame to CuDF if needed."""
        if not HAS_GPU:
            return df
            
        if isinstance(df, pd.DataFrame):
            return cudf.from_pandas(df)
        return df
        
    def _create_market_features_gpu(self, market_cudf: 'cudf.DataFrame') -> 'cudf.DataFrame':
        """Create market-based features using GPU acceleration."""
        if not HAS_GPU:
            raise RuntimeError("GPU processing not available")
            
        # Sort by timestamp for rolling operations
        market_cudf = market_cudf.sort_values('timestamp')
        
        # Price features using CuDF operations
        market_cudf['price_current'] = market_cudf['price_eur_mwh']
        market_cudf['price_24h_avg'] = market_cudf['price_eur_mwh'].rolling(window=24).mean()
        market_cudf['price_24h_std'] = market_cudf['price_eur_mwh'].rolling(window=24).std()
        market_cudf['price_24h_min'] = market_cudf['price_eur_mwh'].rolling(window=24).min()
        market_cudf['price_24h_max'] = market_cudf['price_eur_mwh'].rolling(window=24).max()
        
        # Price lags using CuDF shift
        market_cudf['price_lag_1h'] = market_cudf['price_eur_mwh'].shift(1)
        market_cudf['price_lag_24h'] = market_cudf['price_eur_mwh'].shift(24)
        market_cudf['price_lag_7d'] = market_cudf['price_eur_mwh'].shift(168)
        
        # Price differences
        market_cudf['price_diff_1h'] = (
            market_cudf['price_eur_mwh'] - market_cudf['price_lag_1h']
        )
        market_cudf['price_diff_24h'] = (
            market_cudf['price_eur_mwh'] - market_cudf['price_lag_24h']
        )
        
        # Time-based features
        market_cudf['hour'] = market_cudf['timestamp'].dt.hour
        market_cudf['is_peak_hour'] = market_cudf['hour'].isin([17, 18, 19, 20])
        market_cudf['is_offpeak_hour'] = market_cudf['hour'].isin([23, 0, 1, 2, 3, 4, 5, 6])
        
        # Price regime indicators
        market_cudf['above_weekly_avg'] = (
            market_cudf['price_eur_mwh'] > 
            market_cudf['price_eur_mwh'].rolling(window=168).mean()
        )
        
        return market_cudf
        
    def _create_weather_features_gpu(self, weather_cudf: 'cudf.DataFrame') -> 'cudf.DataFrame':
        """Create weather-based features using GPU acceleration."""
        if not HAS_GPU:
            raise RuntimeError("GPU processing not available")
            
        # Sort by timestamp
        weather_cudf = weather_cudf.sort_values('timestamp')
        
        # Solar irradiance features
        weather_cudf['solar_ghi'] = weather_cudf['solar_radiation']
        weather_cudf['solar_24h_avg'] = weather_cudf['solar_radiation'].rolling(window=24).mean()
        weather_cudf['solar_forecast_24h'] = weather_cudf['solar_radiation'].shift(24)
        
        # Temperature features
        weather_cudf['temp_current'] = weather_cudf['temperature']
        weather_cudf['temp_24h_avg'] = weather_cudf['temperature'].rolling(window=24).mean()
        weather_cudf['temp_anomaly'] = (
            weather_cudf['temperature'] - 
            weather_cudf['temperature'].rolling(window=168).mean()
        )
        
        # Wind features
        weather_cudf['wind_current'] = weather_cudf['wind_speed']
        weather_cudf['wind_6h_avg'] = weather_cudf['wind_speed'].rolling(window=6).mean()
        
        # Cloud cover impact
        weather_cudf['clear_sky_fraction'] = 100 - weather_cudf['cloudcover']
        weather_cudf['effective_solar'] = (
            weather_cudf['solar_radiation'] * 
            weather_cudf['clear_sky_fraction'] / 100
        )
        
        # Time-based features
        weather_cudf['hour_of_day'] = weather_cudf['timestamp'].dt.hour
        weather_cudf['day_of_year'] = weather_cudf['timestamp'].dt.dayofyear
        weather_cudf['is_daylight'] = weather_cudf['hour_of_day'].between(6, 18)
        
        return weather_cudf
        
    def _create_client_features_gpu(self, client_cudf: 'cudf.DataFrame') -> 'cudf.DataFrame':
        """Create client state features using GPU acceleration."""
        if not HAS_GPU:
            raise RuntimeError("GPU processing not available")
            
        # Sort by timestamp
        client_cudf = client_cudf.sort_values('timestamp')
        
        # Battery state features
        client_cudf['soc_current'] = client_cudf['battery_soc']
        client_cudf['soc_previous'] = client_cudf['battery_soc'].shift(1)
        client_cudf['soc_change'] = client_cudf['soc_current'] - client_cudf['soc_previous']
        client_cudf['soc_24h_avg'] = client_cudf['battery_soc'].rolling(window=24).mean()
        
        # Battery health indicators
        client_cudf['battery_temperature'] = client_cudf['battery_temp']
        client_cudf['temp_deviation_optimal'] = client_cudf['battery_temp'] - 25.0
        client_cudf['high_temp_stress'] = client_cudf['battery_temp'] > 35.0
        
        # Charge/discharge indicators
        client_cudf['is_charging'] = client_cudf['soc_change'] > 0
        client_cudf['is_discharging'] = client_cudf['soc_change'] < 0
        
        # Load patterns
        client_cudf['load_current'] = client_cudf['load_actual']
        client_cudf['load_24h_avg'] = client_cudf['load_actual'].rolling(window=24).mean()
        client_cudf['load_24h_std'] = client_cudf['load_actual'].rolling(window=24).std()
        
        # Generation patterns
        if 'solar_gen_actual' in client_cudf.columns:
            client_cudf['solar_generation'] = client_cudf['solar_gen_actual'].fillna(0.0)
        else:
            client_cudf['solar_generation'] = 0.0
            
        # Net load
        client_cudf['net_load'] = client_cudf['load_current'] - client_cudf['solar_generation']
        
        # Capacity margins
        client_cudf['charge_capacity_remaining'] = 100.0 - client_cudf['battery_soc']
        client_cudf['discharge_capacity_available'] = client_cudf['battery_soc']
        
        return client_cudf
        
    def _join_features_gpu(self, 
                          market_features: 'cudf.DataFrame',
                          weather_features: 'cudf.DataFrame', 
                          client_features: 'cudf.DataFrame') -> 'cudf.DataFrame':
        """Join all feature DataFrames on timestamp using GPU acceleration."""
        if not HAS_GPU:
            raise RuntimeError("GPU processing not available")
            
        # Inner join on timestamp
        combined = market_features.merge(
            weather_features, on='timestamp', how='inner'
        ).merge(
            client_features, on='timestamp', how='inner'
        )
        
        return combined
        
    def _add_derived_features_gpu(self, feature_cudf: 'cudf.DataFrame') -> 'cudf.DataFrame':
        """Add derived features combining multiple data sources using GPU."""
        if not HAS_GPU:
            raise RuntimeError("GPU processing not available")
            
        # Economic features
        feature_cudf['cost_without_battery'] = (
            feature_cudf['price_current'] * feature_cudf['net_load']
        )
        
        # Arbitrage opportunity indicators
        feature_cudf['low_price_opportunity'] = (
            feature_cudf['price_current'] < feature_cudf['price_24h_avg'] * 0.8
        )
        feature_cudf['high_price_opportunity'] = (
            feature_cudf['price_current'] > feature_cudf['price_24h_avg'] * 1.2
        )
        
        # Battery optimization signals
        feature_cudf['low_soc_warning'] = feature_cudf['soc_current'] < 20.0
        feature_cudf['high_soc_warning'] = feature_cudf['soc_current'] > 90.0
        
        # Time-based patterns
        feature_cudf['day_of_week'] = feature_cudf['timestamp'].dt.dayofweek
        feature_cudf['month'] = feature_cudf['timestamp'].dt.month
        
        # Seasonal indicators
        feature_cudf['is_winter'] = feature_cudf['month'].isin([12, 1, 2])
        feature_cudf['is_summer'] = feature_cudf['month'].isin([6, 7, 8])
        feature_cudf['is_weekend'] = feature_cudf['day_of_week'].isin([5, 6])
        
        # Price volatility
        feature_cudf['price_coefficient_variation'] = (
            feature_cudf['price_24h_std'] / feature_cudf['price_24h_avg']
        )
        
        # Solar availability score
        feature_cudf['solar_availability_score'] = (
            feature_cudf['solar_ghi'] / 1000.0 *
            feature_cudf['clear_sky_fraction'] / 100.0 *
            feature_cudf['is_daylight'].astype(float)
        )
        
        return feature_cudf
        
    def benchmark_performance(self, 
                            data_size_mb: float,
                            operation_type: str = "full_pipeline") -> Dict[str, float]:
        """
        Benchmark NVTabular engine performance.
        
        Args:
            data_size_mb: Size of test data in MB
            operation_type: Type of operation to benchmark
            
        Returns:
            Performance metrics
        """
        if not HAS_GPU:
            raise RuntimeError("GPU benchmarking not available")
            
        import time
        
        # Generate synthetic data for benchmarking
        n_rows = int(data_size_mb * 1024 * 1024 / 100)  # Rough estimation
        
        start_time = time.time()
        gpu_memory_before = self._get_gpu_memory_usage()
        
        # Create synthetic test data on GPU
        timestamps = pd.date_range(
            datetime.now() - timedelta(hours=n_rows),
            datetime.now(),
            freq='H'
        )[:n_rows]
        
        synthetic_market = cudf.DataFrame({
            "timestamp": timestamps,
            "price_eur_mwh": cp.random.normal(50, 15, n_rows),
        })
        
        synthetic_weather = cudf.DataFrame({
            "timestamp": timestamps,
            "solar_radiation": cp.random.uniform(0, 1000, n_rows),
            "temperature": cp.random.normal(20, 10, n_rows),
            "wind_speed": cp.random.uniform(0, 20, n_rows),
            "cloudcover": cp.random.uniform(0, 100, n_rows),
        })
        
        synthetic_client = cudf.DataFrame({
            "timestamp": timestamps,
            "battery_soc": cp.random.uniform(20, 90, n_rows),
            "battery_temp": cp.random.normal(25, 5, n_rows),
            "load_actual": cp.random.uniform(10, 100, n_rows),
            "solar_gen_actual": cp.random.uniform(0, 80, n_rows),
        })
        
        # Run the benchmark
        if operation_type == "full_pipeline":
            result = self.process_features(
                synthetic_market, synthetic_weather, synthetic_client
            )
        else:
            result = synthetic_market
            
        # Ensure GPU operations are complete
        cp.cuda.Stream.null.synchronize()
        
        end_time = time.time()
        gpu_memory_after = self._get_gpu_memory_usage()
        
        processing_time = end_time - start_time
        memory_used = gpu_memory_after - gpu_memory_before
        throughput_mb_per_sec = data_size_mb / processing_time
        
        return {
            "processing_time_seconds": processing_time,
            "gpu_memory_used_mb": memory_used,
            "throughput_mb_per_sec": throughput_mb_per_sec,
            "rows_processed": n_rows,
            "rows_per_second": n_rows / processing_time,
            "output_shape": result.shape,
            "engine": self.engine_name
        }
        
    def _get_gpu_memory_usage(self) -> float:
        """Get current GPU memory usage in MB."""
        if not HAS_GPU:
            return 0.0
            
        total_used = 0
        for i in range(self.gpu_count):
            with cp.cuda.Device(i):
                memory_info = cp.cuda.runtime.memGetInfo()
                used_memory = memory_info[1] - memory_info[0]  # Total - Free
                total_used += used_memory
                
        return total_used / (1024**2)  # Convert to MB
        
    def get_engine_info(self) -> Dict[str, Union[str, int, Dict, List]]:
        """Get engine information and capabilities."""
        if not HAS_GPU:
            return {
                "engine_name": self.engine_name,
                "status": "unavailable",
                "error": GPU_IMPORT_ERROR,
                "backend": "GPU (NVIDIA/NVTabular)",
                "available": False
            }
            
        gpu_info = []
        for i in range(self.gpu_count):
            with cp.cuda.Device(i):
                props = cp.cuda.runtime.getDeviceProperties(i)
                memory_info = cp.cuda.runtime.memGetInfo()
                gpu_info.append({
                    "device_id": i,
                    "name": props["name"].decode(),
                    "compute_capability": f"{props['major']}.{props['minor']}",
                    "memory_gb": memory_info[1] / (1024**3),
                    "multiprocessors": props["multiProcessorCount"]
                })
                
        return {
            "engine_name": self.engine_name,
            "backend": "GPU (NVIDIA/NVTabular)",
            "nvtabular_available": True,
            "cupy_available": True,
            "cudf_available": True,
            "gpu_count": self.gpu_count,
            "total_gpu_memory_gb": self.gpu_memory,
            "gpu_devices": gpu_info,
            "lazy_evaluation": False,  # Immediate execution
            "vectorized_operations": True,
            "parallel_processing": True,
            "optimal_for": [
                "Large-scale data processing",
                "Production ML pipelines", 
                "Terabyte datasets",
                "High-performance computing"
            ],
            "limitations": [
                "Requires CUDA GPU",
                "Higher memory usage",
                "Additional dependencies"
            ]
        }


# Utility functions for engine selection
def is_nvtabular_available() -> bool:
    """Check if NVTabular and GPU are available."""
    return HAS_GPU


def create_nvtabular_engine(config: Optional[Dict] = None) -> Optional[NVTabularEngine]:
    """
    Factory function to create NVTabular engine with error handling.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        NVTabularEngine instance or None if unavailable
    """
    if not is_nvtabular_available():
        logger.warning(
            f"NVTabular not available: {GPU_IMPORT_ERROR}. "
            "Falling back to CPU engine."
        )
        return None
        
    try:
        engine = NVTabularEngine(config)
        logger.info("Successfully created NVTabular GPU engine")
        return engine
    except Exception as e:
        logger.error(f"Failed to create NVTabular engine: {e}")
        return None


# Example usage and testing
if __name__ == "__main__":
    # Test engine creation
    print("NVTabular Engine Availability Check")
    print("=" * 40)
    print(f"GPU Dependencies Available: {HAS_GPU}")
    
    if not HAS_GPU:
        print(f"Import Error: {GPU_IMPORT_ERROR}")
        print("\nTo install GPU support:")
        print("pip install nvtabular cupy-cuda11x")
        exit(1)
        
    engine = create_nvtabular_engine()
    
    if engine:
        print("\nNVTabular Engine Information:")
        print("=" * 40)
        info = engine.get_engine_info()
        for key, value in info.items():
            if isinstance(value, list):
                print(f"{key}:")
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            print(f"  {k}: {v}")
                    else:
                        print(f"  - {item}")
            else:
                print(f"{key}: {value}")
                
        # Benchmark performance
        try:
            print("\nPerformance Benchmark:")
            print("-" * 30)
            benchmark = engine.benchmark_performance(data_size_mb=50.0)
            for metric, value in benchmark.items():
                if isinstance(value, float):
                    print(f"{metric}: {value:.3f}")
                else:
                    print(f"{metric}: {value}")
        except Exception as e:
            print(f"Benchmark failed: {e}")
    else:
        print("Failed to create NVTabular engine")
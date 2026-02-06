"""
Polars-based CPU Engine for Feature Engineering

CPU-optimized engine using Rust-based Polars for efficient data processing
on edge devices and AWS Free Tier instances.

Thesis Relevance: Demonstrates high-performance CPU processing for
resource-constrained environments without GPU requirements.
"""

import polars as pl
import numpy as np
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class PolarsEngine:
    """
    CPU-optimized feature engineering engine using Polars.
    
    Designed for:
    - AWS Free Tier EC2 instances (t3.micro)
    - Edge devices without GPU
    - Development environments
    - Production failover scenarios
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Polars engine with configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.engine_name = "polars_cpu"
        
        # Set Polars configuration for optimal CPU usage
        pl.Config.set_tbl_rows(50)  # Display rows
        pl.Config.set_tbl_cols(20)  # Display columns
        
        # Configure for available CPU cores
        self.n_cores = self.config.get("n_cores", None)  # Use all available
        
        logger.info(f"Initialized Polars engine with {self.n_cores or 'all'} cores")
        
    def process_features(self, 
                        market_data: pl.DataFrame,
                        weather_data: pl.DataFrame,
                        client_state: pl.DataFrame) -> pl.DataFrame:
        """
        Process features using Polars lazy evaluation.
        
        Args:
            market_data: Market price data
            weather_data: Weather forecast data
            client_state: Client battery/system state
            
        Returns:
            Feature matrix ready for ML models
        """
        logger.info("Starting Polars feature processing pipeline")
        
        # Use lazy evaluation for memory efficiency
        market_lazy = market_data.lazy()
        weather_lazy = weather_data.lazy()
        client_lazy = client_state.lazy()
        
        # Process market features
        market_features = self._create_market_features(market_lazy)
        
        # Process weather features
        weather_features = self._create_weather_features(weather_lazy)
        
        # Process client state features
        client_features = self._create_client_features(client_lazy)
        
        # Join all features on timestamp
        feature_matrix = (
            market_features
            .join(weather_features, on="timestamp", how="inner")
            .join(client_features, on="timestamp", how="inner")
        )
        
        # Add derived features
        feature_matrix = self._add_derived_features(feature_matrix)
        
        # Execute lazy operations
        result = feature_matrix.collect()
        
        logger.info(f"Polars processing complete: {result.shape} features generated")
        return result
        
    def _create_market_features(self, market_lazy: pl.LazyFrame) -> pl.LazyFrame:
        """Create market-based features using Polars expressions."""
        return (
            market_lazy
            .with_columns([
                # Price features
                pl.col("price_eur_mwh").alias("price_current"),
                pl.col("price_eur_mwh").rolling_mean(window_size=24).alias("price_24h_avg"),
                pl.col("price_eur_mwh").rolling_std(window_size=24).alias("price_24h_std"),
                pl.col("price_eur_mwh").rolling_min(window_size=24).alias("price_24h_min"),
                pl.col("price_eur_mwh").rolling_max(window_size=24).alias("price_24h_max"),
                
                # Price lags
                pl.col("price_eur_mwh").shift(1).alias("price_lag_1h"),
                pl.col("price_eur_mwh").shift(24).alias("price_lag_24h"),
                pl.col("price_eur_mwh").shift(168).alias("price_lag_7d"),
                
                # Price differences
                (pl.col("price_eur_mwh") - pl.col("price_eur_mwh").shift(1)).alias("price_diff_1h"),
                (pl.col("price_eur_mwh") - pl.col("price_eur_mwh").shift(24)).alias("price_diff_24h"),
                
                # Price percentiles (using window functions)
                pl.col("price_eur_mwh").rank(method="average").over(
                    pl.col("timestamp").dt.date()
                ).alias("price_daily_rank"),
                
                # Price regime indicators
                (pl.col("price_eur_mwh") > pl.col("price_eur_mwh").rolling_mean(window_size=168))
                .alias("above_weekly_avg"),
                
                # Peak/off-peak indicators  
                pl.col("timestamp").dt.hour().is_in([17, 18, 19, 20]).alias("is_peak_hour"),
                pl.col("timestamp").dt.hour().is_in([23, 0, 1, 2, 3, 4, 5, 6]).alias("is_offpeak_hour"),
            ])
        )
        
    def _create_weather_features(self, weather_lazy: pl.LazyFrame) -> pl.LazyFrame:
        """Create weather-based features using Polars expressions."""
        return (
            weather_lazy
            .with_columns([
                # Solar irradiance features
                pl.col("solar_radiation").alias("solar_ghi"),
                pl.col("solar_radiation").rolling_mean(window_size=24).alias("solar_24h_avg"),
                pl.col("solar_radiation").shift(24).alias("solar_forecast_24h"),
                
                # Temperature features
                pl.col("temperature").alias("temp_current"),
                pl.col("temperature").rolling_mean(window_size=24).alias("temp_24h_avg"),
                (pl.col("temperature") - pl.col("temperature").rolling_mean(window_size=168))
                .alias("temp_anomaly"),
                
                # Wind features
                pl.col("wind_speed").alias("wind_current"),
                pl.col("wind_speed").rolling_mean(window_size=6).alias("wind_6h_avg"),
                
                # Cloud cover impact
                (100 - pl.col("cloudcover")).alias("clear_sky_fraction"),
                (pl.col("solar_radiation") * (100 - pl.col("cloudcover")) / 100)
                .alias("effective_solar"),
                
                # Time-based solar features
                pl.col("timestamp").dt.hour().alias("hour_of_day"),
                (pl.col("timestamp").dt.ordinal_day() % 365).alias("day_of_year"),
                
                # Solar elevation angle approximation
                (
                    pl.lit(90) - 
                    (pl.col("timestamp").dt.hour() - 12).abs() * pl.lit(15.0 / 90.0) * 90
                ).clip(0, 90).alias("solar_elevation_approx"),
                
                # Day/night indicator
                pl.col("timestamp").dt.hour().is_between(6, 18).alias("is_daylight"),
            ])
        )
        
    def _create_client_features(self, client_lazy: pl.LazyFrame) -> pl.LazyFrame:
        """Create client state features using Polars expressions."""
        return (
            client_lazy
            .with_columns([
                # Battery state features
                pl.col("battery_soc").alias("soc_current"),
                pl.col("battery_soc").shift(1).alias("soc_previous"),
                (pl.col("battery_soc") - pl.col("battery_soc").shift(1)).alias("soc_change"),
                pl.col("battery_soc").rolling_mean(window_size=24).alias("soc_24h_avg"),
                
                # Battery health indicators
                pl.col("battery_temp").alias("battery_temperature"),
                (pl.col("battery_temp") - 25.0).alias("temp_deviation_optimal"),
                (pl.col("battery_temp") > 35.0).alias("high_temp_stress"),
                
                # Charge/discharge indicators
                (pl.col("battery_soc") > pl.col("battery_soc").shift(1)).alias("is_charging"),
                (pl.col("battery_soc") < pl.col("battery_soc").shift(1)).alias("is_discharging"),
                
                # Load patterns
                pl.col("load_actual").alias("load_current"),
                pl.col("load_actual").rolling_mean(window_size=24).alias("load_24h_avg"),
                pl.col("load_actual").rolling_std(window_size=24).alias("load_24h_std"),
                
                # Generation patterns (if available)
                pl.when(pl.col("solar_gen_actual").is_not_null())
                .then(pl.col("solar_gen_actual"))
                .otherwise(0.0)
                .alias("solar_generation"),
                
                # Net load (load minus generation)
                (pl.col("load_actual") - 
                 pl.when(pl.col("solar_gen_actual").is_not_null())
                 .then(pl.col("solar_gen_actual"))
                 .otherwise(0.0))
                .alias("net_load"),
                
                # Capacity margins
                (100.0 - pl.col("battery_soc")).alias("charge_capacity_remaining"),
                pl.col("battery_soc").alias("discharge_capacity_available"),
            ])
        )
        
    def _add_derived_features(self, feature_lazy: pl.LazyFrame) -> pl.LazyFrame:
        """Add derived features combining multiple data sources."""
        return (
            feature_lazy
            .with_columns([
                # Economic features
                (pl.col("price_current") * pl.col("net_load")).alias("cost_without_battery"),
                
                # Arbitrage opportunity indicators
                (pl.col("price_current") < pl.col("price_24h_avg") * 0.8).alias("low_price_opportunity"),
                (pl.col("price_current") > pl.col("price_24h_avg") * 1.2).alias("high_price_opportunity"),
                
                # Solar correlation features
                (pl.col("solar_ghi") * pl.col("clear_sky_fraction") / 100).alias("expected_solar_gen"),
                
                # Battery optimization signals
                (pl.col("soc_current") < 20.0).alias("low_soc_warning"),
                (pl.col("soc_current") > 90.0).alias("high_soc_warning"),
                
                # Time-based patterns
                pl.col("timestamp").dt.weekday().alias("day_of_week"),
                pl.col("timestamp").dt.hour().alias("hour"),
                pl.col("timestamp").dt.month().alias("month"),
                
                # Seasonal indicators
                pl.col("timestamp").dt.month().is_in([12, 1, 2]).alias("is_winter"),
                pl.col("timestamp").dt.month().is_in([6, 7, 8]).alias("is_summer"),
                
                # Weekend indicator
                pl.col("timestamp").dt.weekday().is_in([6, 7]).alias("is_weekend"),
                
                # Price volatility
                (pl.col("price_24h_std") / pl.col("price_24h_avg")).alias("price_coefficient_variation"),
                
                # Solar availability score
                (pl.col("solar_ghi") / pl.lit(1000.0) * 
                 pl.col("clear_sky_fraction") / 100.0 *
                 pl.col("is_daylight").cast(pl.Float64)).alias("solar_availability_score"),
            ])
        )
        
    def benchmark_performance(self, 
                            data_size_mb: float,
                            operation_type: str = "full_pipeline") -> Dict[str, float]:
        """
        Benchmark Polars engine performance.
        
        Args:
            data_size_mb: Size of test data in MB
            operation_type: Type of operation to benchmark
            
        Returns:
            Performance metrics
        """
        import time
        import psutil
        
        # Generate synthetic data for benchmarking
        n_rows = int(data_size_mb * 1024 * 1024 / 100)  # Rough estimation
        
        start_time = time.time()
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Create synthetic test data
        synthetic_market = pl.DataFrame({
            "timestamp": pl.date_range(
                datetime.now() - timedelta(hours=n_rows),
                datetime.now(),
                interval="1h"
            )[:n_rows],
            "price_eur_mwh": np.random.normal(50, 15, n_rows),
        })
        
        synthetic_weather = pl.DataFrame({
            "timestamp": synthetic_market["timestamp"],
            "solar_radiation": np.random.uniform(0, 1000, n_rows),
            "temperature": np.random.normal(20, 10, n_rows),
            "wind_speed": np.random.uniform(0, 20, n_rows),
            "cloudcover": np.random.uniform(0, 100, n_rows),
        })
        
        synthetic_client = pl.DataFrame({
            "timestamp": synthetic_market["timestamp"],
            "battery_soc": np.random.uniform(20, 90, n_rows),
            "battery_temp": np.random.normal(25, 5, n_rows),
            "load_actual": np.random.uniform(10, 100, n_rows),
            "solar_gen_actual": np.random.uniform(0, 80, n_rows),
        })
        
        # Run the benchmark
        if operation_type == "full_pipeline":
            result = self.process_features(
                synthetic_market, synthetic_weather, synthetic_client
            )
        else:
            # Individual operation benchmarks could be added here
            result = synthetic_market
            
        end_time = time.time()
        memory_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        processing_time = end_time - start_time
        memory_used = memory_after - memory_before
        throughput_mb_per_sec = data_size_mb / processing_time
        
        return {
            "processing_time_seconds": processing_time,
            "memory_used_mb": memory_used,
            "throughput_mb_per_sec": throughput_mb_per_sec,
            "rows_processed": n_rows,
            "rows_per_second": n_rows / processing_time,
            "output_shape": result.shape,
            "engine": self.engine_name
        }
        
    def get_engine_info(self) -> Dict[str, Union[str, int, Dict]]:
        """Get engine information and capabilities."""
        import polars as pl
        import psutil
        
        return {
            "engine_name": self.engine_name,
            "backend": "CPU (Rust/Polars)",
            "polars_version": pl.__version__,
            "cpu_cores": psutil.cpu_count(),
            "memory_gb": psutil.virtual_memory().total / (1024**3),
            "lazy_evaluation": True,
            "vectorized_operations": True,
            "parallel_processing": True,
            "memory_mapping": True,
            "optimal_for": [
                "Edge devices",
                "AWS Free Tier",
                "Development environments",
                "Production failover"
            ],
            "limitations": [
                "No GPU acceleration", 
                "Limited to available RAM",
                "CPU-bound for large datasets"
            ]
        }


# Utility functions for engine selection
def is_polars_available() -> bool:
    """Check if Polars is available and properly installed."""
    try:
        import polars as pl
        return True
    except ImportError:
        return False


def create_polars_engine(config: Optional[Dict] = None) -> Optional[PolarsEngine]:
    """
    Factory function to create Polars engine with error handling.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        PolarsEngine instance or None if unavailable
    """
    if not is_polars_available():
        logger.error("Polars not available - install with: pip install polars")
        return None
        
    try:
        engine = PolarsEngine(config)
        logger.info("Successfully created Polars engine")
        return engine
    except Exception as e:
        logger.error(f"Failed to create Polars engine: {e}")
        return None


# Example usage and testing
if __name__ == "__main__":
    # Test engine creation
    engine = create_polars_engine()
    
    if engine:
        print("Polars Engine Information:")
        print("=" * 40)
        info = engine.get_engine_info()
        for key, value in info.items():
            if isinstance(value, list):
                print(f"{key}:")
                for item in value:
                    print(f"  - {item}")
            else:
                print(f"{key}: {value}")
                
        # Benchmark performance
        print("\nPerformance Benchmark:")
        print("-" * 30)
        benchmark = engine.benchmark_performance(data_size_mb=10.0)
        for metric, value in benchmark.items():
            if isinstance(value, float):
                print(f"{metric}: {value:.3f}")
            else:
                print(f"{metric}: {value}")
    else:
        print("Failed to create Polars engine")
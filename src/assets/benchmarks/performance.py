"""
Benchmarking Assets - Performance and Accuracy Comparison

Dagster assets for benchmarking different processing engines and algorithms.
Implements MLflow integration for experiment tracking and model comparison.

Thesis Relevance: Demonstrates systematic performance evaluation of different
data processing approaches in production energy systems.
"""

import sys
import os
from pathlib import Path

from dagster import asset, AssetIn, MetadataValue
import polars as pl
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Any, TypedDict
import time
import tracemalloc
import numpy as np
import mlflow


def _ensure_src_in_path():
    """Ensure src/ is in sys.path for subprocess execution."""
    import sys
    from pathlib import Path

    # Check if already importable
    try:
        import physics.economics

        return  # Already in path
    except ImportError:
        pass

    # Try multiple approaches to find project root
    possible_roots = []

    # 1. From __file__
    try:
        current_file = Path(__file__).resolve()
        possible_roots.append(current_file.parent.parent.parent.parent)
    except Exception:
        pass

    # 2. From cwd
    possible_roots.append(Path.cwd())

    # 3. Try parent of cwd
    possible_roots.append(Path.cwd().parent)

    for root in possible_roots:
        src_path = root / "src"
        if src_path.exists():
            if str(src_path) not in sys.path:
                sys.path.insert(0, str(src_path))
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            break


logger = logging.getLogger(__name__)


class BenchmarkMetrics(TypedDict):
    engine_name: str
    data_size: int
    processing_time_seconds: float
    memory_peak_mb: float
    memory_current_mb: float
    throughput_records_per_second: float
    success: bool
    error_message: str | None
    output_rows: int
    benchmark_timestamp: datetime


@asset(
    group_name="benchmarks",
    description="Performance benchmark comparing Polars vs NVTabular engines",
    ins={
        "market_data": AssetIn("market_data_asset"),
        "weather_data": AssetIn("weather_asset"),
    },
    metadata={
        "benchmark_type": "engine_comparison",
        "engines": ["polars", "nvtabular"],
        "metrics": ["processing_time", "memory_usage", "throughput"],
    },
)
def engine_benchmark_asset(
    market_data: pl.DataFrame, weather_data: pl.DataFrame
) -> pl.DataFrame:
    """
    Benchmark Polars vs NVTabular engines for feature engineering tasks.

    Returns DataFrame with performance metrics for each engine.
    """
    logger.info("Starting engine benchmark comparison...")

    # Ensure src is in path for subprocess execution
    _ensure_src_in_path()

    # Import engines
    from engines.polars_engine import PolarsEngine

    # Initialize engines
    polars_engine = PolarsEngine()

    # Try to import NVTabular (optional - may not be installed)
    nvtabular_engine = None
    try:
        from engines.nvtabular_engine import NVTabularEngine

        nvtabular_engine = NVTabularEngine()
    except ImportError as e:
        logger.warning(f"NVTabular not available, skipping: {e}")

    # Combine input data for benchmarking
    combined_data = market_data.join(weather_data, on="timestamp", how="inner")

    benchmark_results = []

    # Test datasets of different sizes
    test_sizes = [1000, 5000, 10000, len(combined_data)]

    for size in test_sizes:
        if size > len(combined_data):
            continue

        test_data = combined_data.head(size)
        logger.info(f"Benchmarking with {size} records...")

        # Benchmark Polars Engine
        polars_metrics = _benchmark_engine(
            engine=polars_engine, data=test_data, engine_name="polars", data_size=size
        )
        benchmark_results.append(polars_metrics)

        # Benchmark NVTabular Engine (if available)
        if nvtabular_engine is not None:
            nvtabular_metrics = _benchmark_engine(
                engine=nvtabular_engine,
                data=test_data,
                engine_name="nvtabular",
                data_size=size,
            )
            benchmark_results.append(nvtabular_metrics)

        # Memory cleanup between tests
        import gc

        gc.collect()

    # Convert results to DataFrame
    benchmark_df = pl.DataFrame(benchmark_results)

    # Calculate performance ratios and rankings
    benchmark_df = _add_performance_analysis(benchmark_df)

    logger.info(f"Engine benchmark complete: {len(benchmark_df)} test results")
    return benchmark_df


def _benchmark_engine(
    engine, data: pl.DataFrame, engine_name: str, data_size: int
) -> BenchmarkMetrics:
    """Run performance benchmark on a specific engine."""

    # Start memory tracking
    tracemalloc.start()
    start_time = time.time()

    try:
        # Execute feature engineering pipeline
        if hasattr(engine, "process_energy_features"):
            result = engine.process_energy_features(data)
        elif hasattr(engine, "fit_transform"):
            # For NVTabular-style engines
            result = engine.fit_transform(data)
        else:
            # Fallback: basic data processing
            result = data.with_columns(
                [
                    pl.col("price_eur_mwh")
                    .rolling_mean(window_size=3)
                    .alias("price_ma3"),
                    pl.col("solar_radiation")
                    .rolling_max(window_size=6)
                    .alias("solar_max6h"),
                    (pl.col("price_eur_mwh") * pl.col("volume_mwh") / 1000).alias(
                        "market_value"
                    ),
                ]
            )

        # Measure completion time
        end_time = time.time()
        processing_time = end_time - start_time

        # Measure memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Calculate throughput
        throughput = data_size / processing_time if processing_time > 0 else 0

        # Success metrics
        success = True
        error_message = None
        output_rows = len(result) if hasattr(result, "__len__") else data_size

    except Exception as e:
        # Handle engine failures
        end_time = time.time()
        processing_time = end_time - start_time
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        success = False
        error_message = str(e)
        output_rows = 0
        throughput = 0

        logger.warning(f"Engine {engine_name} failed on {data_size} records: {e}")

    return {
        "engine_name": engine_name,
        "data_size": data_size,
        "processing_time_seconds": processing_time,
        "memory_peak_mb": peak / (1024 * 1024),
        "memory_current_mb": current / (1024 * 1024),
        "throughput_records_per_second": throughput,
        "success": success,
        "error_message": error_message,
        "output_rows": output_rows,
        "benchmark_timestamp": datetime.now(),
    }


def _add_performance_analysis(df: pl.DataFrame) -> pl.DataFrame:
    """Add performance analysis and rankings to benchmark results."""

    # Add performance rankings within each data size
    df = df.with_columns(
        [
            # Processing time ranking (lower is better)
            pl.col("processing_time_seconds")
            .rank()
            .over("data_size")
            .alias("time_rank"),
            # Throughput ranking (higher is better)
            pl.col("throughput_records_per_second")
            .rank(descending=True)
            .over("data_size")
            .alias("throughput_rank"),
            # Memory efficiency ranking (lower is better)
            pl.col("memory_peak_mb").rank().over("data_size").alias("memory_rank"),
            # Success rate
            pl.col("success").cast(pl.Int32).alias("success_int"),
        ]
    )

    # Calculate performance ratios (compared to best performer)
    df = df.with_columns(
        [
            # Time ratio vs fastest
            (
                pl.col("processing_time_seconds")
                / pl.col("processing_time_seconds").min().over("data_size")
            ).alias("time_ratio"),
            # Throughput ratio vs fastest
            (
                pl.col("throughput_records_per_second")
                / pl.col("throughput_records_per_second").max().over("data_size")
            ).alias("throughput_ratio"),
            # Memory ratio vs most efficient
            (
                pl.col("memory_peak_mb")
                / pl.col("memory_peak_mb").min().over("data_size")
            ).alias("memory_ratio"),
        ]
    )

    # Add performance categories
    df = df.with_columns(
        [
            pl.when(pl.col("time_ratio") <= 1.2)
            .then(pl.lit("excellent"))
            .when(pl.col("time_ratio") <= 2.0)
            .then(pl.lit("good"))
            .when(pl.col("time_ratio") <= 5.0)
            .then(pl.lit("acceptable"))
            .otherwise(pl.lit("poor"))
            .alias("performance_category"),
            pl.when(pl.col("memory_ratio") <= 1.5)
            .then(pl.lit("efficient"))
            .when(pl.col("memory_ratio") <= 3.0)
            .then(pl.lit("moderate"))
            .otherwise(pl.lit("memory_intensive"))
            .alias("memory_category"),
        ]
    )

    return df


@asset(
    group_name="benchmarks",
    description="Accuracy benchmark for economic calculations",
    ins={
        "market_data": AssetIn("market_data_asset"),
    },
    metadata={
        "benchmark_type": "accuracy_validation",
        "focus": "economic_models",
        "validation_methods": ["synthetic_truth", "cross_validation"],
    },
)
def accuracy_benchmark_asset(market_data: pl.DataFrame) -> pl.DataFrame:
    """
    Benchmark accuracy of economic calculations and predictions.

    Uses synthetic ground truth data to validate model accuracy.
    """
    logger.info("Starting accuracy benchmark for economic models...")

    _ensure_src_in_path()
    from physics.economics import EconomicModel, BatteryTechnology, OperationProfile

    test_scenarios = _create_economic_test_scenarios()

    accuracy_results = []

    for scenario in test_scenarios:
        scenario_name = scenario["name"]
        expected_lcos = scenario["expected_lcos"]
        expected_arbitrage = scenario["expected_arbitrage"]
        technology = scenario["technology"]
        capacity_kwh = scenario["capacity_kwh"]
        operation_profile = scenario["operation_profile"]
        price_spreads = scenario["price_spreads"]

        logger.info(f"Testing scenario: {scenario_name}")

        try:
            model = EconomicModel(technology, capacity_kwh)

            lcos_result = model.calculate_lcos(operation_profile)
            calculated_lcos = lcos_result["lcos_usd_per_kwh"]
            lcos_error = abs(calculated_lcos - expected_lcos) / expected_lcos

            arbitrage_result = model.calculate_arbitrage_value(
                price_spreads, operation_profile
            )
            calculated_arbitrage = arbitrage_result["annual_net_value"]
            arbitrage_error = (
                abs(calculated_arbitrage - expected_arbitrage) / expected_arbitrage
            )

            result = {
                "scenario_name": scenario_name,
                "metric_type": "lcos",
                "expected_value": expected_lcos,
                "calculated_value": calculated_lcos,
                "absolute_error": abs(calculated_lcos - expected_lcos),
                "relative_error_percent": lcos_error * 100,
                "success": True,
                "benchmark_timestamp": datetime.now(),
            }
            accuracy_results.append(result)

            result = {
                "scenario_name": scenario_name,
                "metric_type": "arbitrage",
                "expected_value": expected_arbitrage,
                "calculated_value": calculated_arbitrage,
                "absolute_error": abs(calculated_arbitrage - expected_arbitrage),
                "relative_error_percent": arbitrage_error * 100,
                "success": True,
                "benchmark_timestamp": datetime.now(),
            }
            accuracy_results.append(result)

        except Exception as e:
            # Record failures
            logger.error(f"Accuracy test failed for {scenario_name}: {e}")
            result = {
                "scenario_name": scenario_name,
                "metric_type": "error",
                "expected_value": None,
                "calculated_value": None,
                "absolute_error": None,
                "relative_error_percent": None,
                "success": False,
                "error_message": str(e),
                "benchmark_timestamp": datetime.now(),
            }
            accuracy_results.append(result)

    # Convert to DataFrame and add analysis
    accuracy_df = pl.DataFrame(accuracy_results)

    # Add accuracy categories
    accuracy_df = accuracy_df.with_columns(
        [
            pl.when(pl.col("relative_error_percent") <= 1.0)
            .then(pl.lit("excellent"))
            .when(pl.col("relative_error_percent") <= 5.0)
            .then(pl.lit("good"))
            .when(pl.col("relative_error_percent") <= 10.0)
            .then(pl.lit("acceptable"))
            .otherwise(pl.lit("poor"))
            .alias("accuracy_category")
        ]
    )

    logger.info(f"Accuracy benchmark complete: {len(accuracy_df)} test results")
    return accuracy_df


def _create_economic_test_scenarios() -> List[Dict]:
    """Create test scenarios with known ground truth for validation."""

    from physics.economics import BatteryTechnology, OperationProfile

    scenarios = [
        {
            "name": "standard_lfp_system",
            "expected_lcos": 0.080,
            "expected_arbitrage": 50.0,
            "technology": BatteryTechnology.LFP,
            "capacity_kwh": 100.0,
            "operation_profile": OperationProfile(
                daily_cycles=1.0,
                seasonal_variation=0.2,
                capacity_factor=0.85,
                grid_services_revenue=0.0,
                energy_arbitrage_spread=40.0,
            ),
            "price_spreads": [30.0, 40.0, 50.0, 35.0, 45.0],
        },
        {
            "name": "premium_nmc_system",
            "expected_lcos": 0.120,
            "expected_arbitrage": 75.0,
            "technology": BatteryTechnology.NMC,
            "capacity_kwh": 100.0,
            "operation_profile": OperationProfile(
                daily_cycles=1.5,
                seasonal_variation=0.25,
                capacity_factor=0.80,
                grid_services_revenue=0.0,
                energy_arbitrage_spread=60.0,
            ),
            "price_spreads": [50.0, 70.0, 90.0, 60.0, 80.0],
        },
        {
            "name": "large_scale_system",
            "expected_lcos": 0.060,
            "expected_arbitrage": 200.0,
            "technology": BatteryTechnology.LFP,
            "capacity_kwh": 500.0,
            "operation_profile": OperationProfile(
                daily_cycles=2.0,
                seasonal_variation=0.15,
                capacity_factor=0.90,
                grid_services_revenue=0.0,
                energy_arbitrage_spread=50.0,
            ),
            "price_spreads": [40.0, 55.0, 65.0, 45.0, 60.0],
        },
    ]

    return scenarios


@asset(
    group_name="benchmarks",
    description="MLflow experiment tracking for benchmark results",
    ins={
        "engine_benchmark": AssetIn("engine_benchmark_asset"),
        "accuracy_benchmark": AssetIn("accuracy_benchmark_asset"),
    },
)
def mlflow_tracking_asset(
    engine_benchmark: pl.DataFrame, accuracy_benchmark: pl.DataFrame
) -> pl.DataFrame:
    """
    Log benchmark results to MLflow for experiment tracking and comparison.
    """
    logger.info("Logging benchmark results to MLflow...")

    mlflow.set_tracking_uri("http://localhost:5000")

    mlflow_logs = []

    for row in engine_benchmark.to_dicts():
        with mlflow.start_run(run_name=f"{row['engine_name']}_size_{row['data_size']}"):
            mlflow.log_param("engine_name", row["engine_name"])
            mlflow.log_param("data_size", row["data_size"])

            mlflow.log_metric("processing_time_seconds", row["processing_time_seconds"])
            mlflow.log_metric("memory_peak_mb", row["memory_peak_mb"])
            mlflow.log_metric(
                "throughput_records_per_second", row["throughput_records_per_second"]
            )

            mlflow.set_tag("benchmark_type", "engine_performance")
            mlflow.set_tag("success", str(row["success"]))

        log_entry = {
            "experiment_name": "engine_benchmarks",
            "run_name": f"{row['engine_name']}_size_{row['data_size']}",
            "engine_name": row["engine_name"],
            "data_size": row["data_size"],
            "metric_processing_time": row["processing_time_seconds"],
            "metric_memory_peak": row["memory_peak_mb"],
            "metric_throughput": row["throughput_records_per_second"],
            "param_success": row["success"],
            "tag_benchmark_type": "engine_performance",
            "timestamp": row["benchmark_timestamp"],
        }
        mlflow_logs.append(log_entry)

    for row in accuracy_benchmark.to_dicts():
        if row["success"]:
            with mlflow.start_run(
                run_name=f"{row['scenario_name']}_{row['metric_type']}"
            ):
                mlflow.log_param("scenario_name", row["scenario_name"])
                mlflow.log_param("metric_type", row["metric_type"])
                mlflow.log_param("expected_value", row["expected_value"])

                mlflow.log_metric("absolute_error", row["absolute_error"])
                mlflow.log_metric(
                    "relative_error_percent", row["relative_error_percent"]
                )

                mlflow.set_tag("benchmark_type", "accuracy_validation")
                mlflow.set_tag("success", str(row["success"]))

            log_entry = {
                "experiment_name": "accuracy_benchmarks",
                "run_name": f"{row['scenario_name']}_{row['metric_type']}",
                "scenario_name": row["scenario_name"],
                "metric_type": row["metric_type"],
                "metric_relative_error": row["relative_error_percent"],
                "metric_absolute_error": row["absolute_error"],
                "param_expected_value": row["expected_value"],
                "param_calculated_value": row["calculated_value"],
                "tag_benchmark_type": "accuracy_validation",
                "timestamp": row["benchmark_timestamp"],
            }
            mlflow_logs.append(log_entry)

    tracking_df = pl.DataFrame(mlflow_logs)

    logger.info(f"MLflow tracking complete: {len(tracking_df)} experiment logs")
    return tracking_df


# Test and validation functions
def test_benchmark_assets():
    """Test benchmark asset functionality."""
    print("🧪 Testing Benchmark Assets...")

    # Create mock data
    mock_market = pl.DataFrame(
        {
            "timestamp": [datetime.now() + timedelta(hours=i) for i in range(24)],
            "price_eur_mwh": [50 + i for i in range(24)],
            "volume_mwh": [1000 + i * 10 for i in range(24)],
        }
    )

    mock_weather = pl.DataFrame(
        {
            "timestamp": [datetime.now() + timedelta(hours=i) for i in range(24)],
            "temperature": [20 + i * 0.1 for i in range(24)],
            "solar_radiation": [
                i * 50 if 6 <= (i % 24) <= 18 else 0 for i in range(24)
            ],
        }
    )

    # Test engine benchmark
    try:
        benchmark_result = engine_benchmark_asset(mock_market, mock_weather)
        print(f"✅ Engine Benchmark: {len(benchmark_result)} test results")
    except Exception as e:
        print(f"❌ Engine Benchmark: {e}")

    # Test accuracy benchmark
    try:
        accuracy_result = accuracy_benchmark_asset(mock_market)
        print(f"✅ Accuracy Benchmark: {len(accuracy_result)} test results")
    except Exception as e:
        print(f"❌ Accuracy Benchmark: {e}")

    print("🎯 Benchmark tests complete!")


if __name__ == "__main__":
    test_benchmark_assets()

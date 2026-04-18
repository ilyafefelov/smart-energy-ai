"""
Benchmarking Assets - Performance and Accuracy Comparison

Dagster assets for benchmarking different processing engines and algorithms.
Implements MLflow integration for experiment tracking and model comparison.

Thesis Relevance: Demonstrates systematic performance evaluation of different
data processing approaches in production energy systems.
"""

import importlib.util
import sys
from pathlib import Path

from dagster import asset, AssetIn
import polars as pl
from datetime import datetime, timedelta, timezone
import logging
import time
import tracemalloc
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

DEFAULT_FORECAST_MODEL_NAME = None
_build_forecast_with_model_spec = None
build_promoted_forecast_model_metadata = None
get_forecast_model_readiness = None
list_forecast_model_specs = None
write_promoted_forecast_model_metadata = None


def _load_price_forecast_module():
    module_name = "smart_energy_ai_price_forecast_asset"
    module_path = Path(__file__).resolve().parents[1] / "core" / "price_forecast.py"
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    if module_spec is None or module_spec.loader is None:
        raise ImportError(f"Unable to load price forecast helpers from {module_path}")

    module = sys.modules.get(module_name)
    if module is None:
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[module_name] = module
        module_spec.loader.exec_module(module)
    return module


def _resolve_forecast_benchmark_dependencies():
    build_forecast_with_model_spec = _build_forecast_with_model_spec
    default_forecast_model_name = DEFAULT_FORECAST_MODEL_NAME
    build_promotion_metadata = build_promoted_forecast_model_metadata
    get_model_readiness = get_forecast_model_readiness
    list_model_specs = list_forecast_model_specs
    write_promotion_metadata = write_promoted_forecast_model_metadata

    try:
        if build_forecast_with_model_spec is None:
            from src.assets.core.price_forecast import _build_forecast_with_model_spec as build_forecast_with_model_spec
    except ImportError:
        if build_forecast_with_model_spec is None:
            price_forecast_module = _load_price_forecast_module()
            build_forecast_with_model_spec = price_forecast_module._build_forecast_with_model_spec

    if (
        default_forecast_model_name is None
        or build_promotion_metadata is None
        or get_model_readiness is None
        or list_model_specs is None
        or write_promotion_metadata is None
    ):
        from src.data_pipeline.forecast_model_registry import (
            DEFAULT_FORECAST_MODEL_NAME as registry_default_model_name,
            build_promoted_forecast_model_metadata as registry_build_promotion_metadata,
            get_forecast_model_readiness as registry_get_model_readiness,
            list_forecast_model_specs as registry_list_model_specs,
            write_promoted_forecast_model_metadata as registry_write_promotion_metadata,
        )

        default_forecast_model_name = default_forecast_model_name or registry_default_model_name
        build_promotion_metadata = build_promotion_metadata or registry_build_promotion_metadata
        get_model_readiness = get_model_readiness or registry_get_model_readiness
        list_model_specs = list_model_specs or registry_list_model_specs
        write_promotion_metadata = write_promotion_metadata or registry_write_promotion_metadata

    return {
        "DEFAULT_FORECAST_MODEL_NAME": default_forecast_model_name,
        "build_forecast_with_model_spec": build_forecast_with_model_spec,
        "build_promoted_forecast_model_metadata": build_promotion_metadata,
        "get_forecast_model_readiness": get_model_readiness,
        "list_forecast_model_specs": list_model_specs,
        "write_promoted_forecast_model_metadata": write_promotion_metadata,
    }


try:
    from src.data_pipeline.benchmark_helpers import (
        BenchmarkMetrics,
        add_performance_analysis as _add_performance_analysis,
        build_forecast_value_scorecard as _build_forecast_value_scorecard,
        create_economic_test_scenarios as _create_economic_test_scenarios,
        log_accuracy_benchmark_run as _log_accuracy_benchmark_run,
        log_engine_benchmark_run as _log_engine_benchmark_run,
        log_forecast_benchmark_run as _log_forecast_benchmark_run,
    )
except ImportError:
    _HELPER_MODULE_NAME = "smart_energy_ai_benchmark_helpers"
    _HELPER_PATH = Path(__file__).resolve().parents[2] / "data_pipeline" / "benchmark_helpers.py"
    _HELPER_SPEC = importlib.util.spec_from_file_location(_HELPER_MODULE_NAME, _HELPER_PATH)
    if _HELPER_SPEC is None or _HELPER_SPEC.loader is None:
        raise ImportError(f"Unable to load benchmark helpers from {_HELPER_PATH}")
    _HELPER_MODULE = sys.modules.get(_HELPER_MODULE_NAME)
    if _HELPER_MODULE is None:
        _HELPER_MODULE = importlib.util.module_from_spec(_HELPER_SPEC)
        sys.modules[_HELPER_MODULE_NAME] = _HELPER_MODULE
        _HELPER_SPEC.loader.exec_module(_HELPER_MODULE)
    BenchmarkMetrics = _HELPER_MODULE.BenchmarkMetrics
    _add_performance_analysis = _HELPER_MODULE.add_performance_analysis
    _build_forecast_value_scorecard = _HELPER_MODULE.build_forecast_value_scorecard
    _create_economic_test_scenarios = _HELPER_MODULE.create_economic_test_scenarios
    _log_accuracy_benchmark_run = _HELPER_MODULE.log_accuracy_benchmark_run
    _log_engine_benchmark_run = _HELPER_MODULE.log_engine_benchmark_run
    _log_forecast_benchmark_run = _HELPER_MODULE.log_forecast_benchmark_run


def _select_promoted_forecast_row(scorecard: pl.DataFrame) -> dict | None:
    if len(scorecard) == 0:
        return None

    promoted = scorecard.filter(
        pl.col("promotion_decision") == pl.lit("promoted")
    )
    if len(promoted) == 0:
        return None

    return promoted.sort(
        by=["benchmark_candidate_rank", "model_name"],
        descending=[False, False],
    ).row(0, named=True)


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


@asset(
    group_name="benchmarks",
    description="Forecast benchmark scorecard comparing point error and value capture",
    ins={
        "market_data": AssetIn("market_data_asset"),
        "price_forecast": AssetIn("price_forecast_asset"),
    },
    metadata={
        "benchmark_type": "forecast_value",
        "focus": "dam_price_forecast",
        "metrics": [
            "benchmark_rmse",
            "benchmark_mae",
            "benchmark_value_capture_ratio",
            "benchmark_conservative_value_capture_ratio",
            "benchmark_point_vs_conservative_value_capture_delta",
        ],
    },
)
def forecast_value_benchmark_asset(
    market_data: pl.DataFrame, price_forecast: pl.DataFrame
) -> pl.DataFrame:
    """Build a forecast scorecard from price forecast outputs and realized market prices."""

    forecast_dependencies = _resolve_forecast_benchmark_dependencies()
    build_forecast_with_model_spec = forecast_dependencies["build_forecast_with_model_spec"]
    default_forecast_model_name = forecast_dependencies["DEFAULT_FORECAST_MODEL_NAME"]
    build_promotion_metadata = forecast_dependencies[
        "build_promoted_forecast_model_metadata"
    ]
    get_model_readiness = forecast_dependencies["get_forecast_model_readiness"]
    list_model_specs = forecast_dependencies["list_forecast_model_specs"]
    write_promotion_metadata = forecast_dependencies[
        "write_promoted_forecast_model_metadata"
    ]

    logger.info("Building forecast benchmark scorecard...")
    existing_models = set(price_forecast.get_column("model_name").unique().to_list()) if len(price_forecast) > 0 else set()
    candidate_forecasts = [price_forecast] if len(price_forecast) > 0 else []
    skipped_candidates: list[dict[str, object]] = []
    registry_model_specs = list_model_specs()
    registry_model_names = [model_spec.model_name for model_spec in registry_model_specs]

    for model_spec in registry_model_specs:
        if model_spec.model_name in existing_models:
            continue
        try:
            readiness = get_model_readiness(model_spec.model_name)
        except KeyError:
            readiness = {
                "ready": True,
                "readiness_reason": None,
            }
        if readiness["ready"] is not True:
            skip_reason = str(
                readiness["readiness_reason"] or "candidate_not_runtime_ready"
            )
            skipped_candidates.append(
                {
                    "model_name": model_spec.model_name,
                    "model_family": getattr(model_spec, "model_family", "unknown_family"),
                    "forecast_horizon_hours": getattr(model_spec, "forecast_horizon_hours", 0),
                    "benchmark_candidate_skip_reason": skip_reason,
                }
            )
            logger.warning(
                "Skipping forecast benchmark candidate %s because it is not runtime-ready: %s",
                model_spec.model_name,
                skip_reason,
            )
            continue
        try:
            candidate_forecasts.append(build_forecast_with_model_spec(market_data, model_spec))
        except ModuleNotFoundError as exc:
            skipped_candidates.append(
                {
                    "model_name": model_spec.model_name,
                    "model_family": getattr(model_spec, "model_family", "unknown_family"),
                    "forecast_horizon_hours": getattr(model_spec, "forecast_horizon_hours", 0),
                    "benchmark_candidate_skip_reason": str(exc),
                }
            )
            logger.warning(
                "Skipping forecast benchmark candidate %s because an optional dependency is unavailable: %s",
                model_spec.model_name,
                exc,
            )

    benchmark_forecasts = (
        pl.concat(candidate_forecasts, how="diagonal_relaxed")
        if candidate_forecasts
        else price_forecast
    )
    scorecard = _build_forecast_value_scorecard(
        market_data,
        benchmark_forecasts,
        skipped_candidates=skipped_candidates,
        registry_model_names=registry_model_names,
        incumbent_model_name=default_forecast_model_name,
    )
    promoted_row = _select_promoted_forecast_row(scorecard)
    if promoted_row is not None:
        try:
            promotion_metadata = build_promotion_metadata(
                promoted_row,
                promoted_at_utc=datetime.now(timezone.utc).isoformat(),
            )
        except (KeyError, ValueError) as exc:
            logger.warning(
                "Skipping forecast promotion write for model %s because it did not pass the registry gate: %s",
                promoted_row.get("model_name"),
                exc,
            )
        else:
            promotion_path = write_promotion_metadata(promotion_metadata)
            logger.info(
                "Promoted forecast model %s via benchmark scorecard and wrote metadata to %s",
                promoted_row["model_name"],
                promotion_path,
            )
    logger.info("Forecast benchmark complete: %s scorecard rows", len(scorecard))
    return scorecard


@asset(
    group_name="benchmarks",
    description="MLflow experiment tracking for benchmark results",
    ins={
        "engine_benchmark": AssetIn("engine_benchmark_asset"),
        "accuracy_benchmark": AssetIn("accuracy_benchmark_asset"),
        "forecast_value_benchmark": AssetIn("forecast_value_benchmark_asset"),
    },
)
def mlflow_tracking_asset(
    engine_benchmark: pl.DataFrame,
    accuracy_benchmark: pl.DataFrame,
    forecast_value_benchmark: pl.DataFrame,
) -> pl.DataFrame:
    """
    Log benchmark results to MLflow for experiment tracking and comparison.
    """
    logger.info("Logging benchmark results to MLflow...")

    mlflow.set_tracking_uri("http://localhost:5000")

    mlflow_logs = []

    for row in engine_benchmark.to_dicts():
        mlflow_logs.append(_log_engine_benchmark_run(row, tracking_module=mlflow))

    for row in accuracy_benchmark.to_dicts():
        log_entry = _log_accuracy_benchmark_run(row, tracking_module=mlflow)
        if log_entry is not None:
            mlflow_logs.append(log_entry)

    for row in forecast_value_benchmark.to_dicts():
        mlflow_logs.append(_log_forecast_benchmark_run(row, tracking_module=mlflow))

    tracking_df = pl.DataFrame(mlflow_logs)

    logger.info(f"MLflow tracking complete: {len(tracking_df)} experiment logs")
    return tracking_df


# Test and validation functions
def test_benchmark_assets():
    """Test benchmark asset functionality."""
    print("🧪 Testing Benchmark Assets...")

    # Create mock data
    mock_timestamps = [datetime.now() + timedelta(hours=i) for i in range(24)]
    mock_prices = [50 + i for i in range(24)]
    mock_market = pl.DataFrame(
        {
            "timestamp": mock_timestamps,
            "price_eur_mwh": mock_prices,
            "volume_mwh": [1000 + i * 10 for i in range(24)],
        }
    )

    mock_weather = pl.DataFrame(
        {
            "timestamp": mock_timestamps,
            "temperature": [20 + i * 0.1 for i in range(24)],
            "solar_radiation": [
                i * 50 if 6 <= (i % 24) <= 18 else 0 for i in range(24)
            ],
        }
    )
    mock_forecast = pl.DataFrame(
        [
            {
                "forecast_timestamp": timestamp,
                "predicted_price_eur_mwh": price,
                "model_name": "demo_forecast",
                "model_family": "demo_family",
                "forecast_horizon_hours": 24,
                "training_rows": 24,
                "evaluation_folds": 1,
                "eval_rmse": 0.0,
                "eval_mae": 0.0,
                "eval_value_capture_ratio": 1.0,
                "eval_realized_spread_eur_mwh": 23.0,
                "eval_optimal_spread_eur_mwh": 23.0,
            }
            for timestamp, price in zip(mock_timestamps, mock_prices)
        ]
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

    # Test forecast benchmark
    try:
        forecast_result = forecast_value_benchmark_asset(mock_market, mock_forecast)
        print(f"✅ Forecast Benchmark: {len(forecast_result)} test results")
    except Exception as e:
        print(f"❌ Forecast Benchmark: {e}")

    print("🎯 Benchmark tests complete!")


if __name__ == "__main__":
    test_benchmark_assets()

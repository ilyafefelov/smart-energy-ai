"""Feature engineering assets for Energy ML system.

These assets transform raw data into machine learning features.
They depend on data source assets and create the feature matrix.
"""
import importlib.util
import pandas as pd
from dagster import asset, Output
import logging
from pathlib import Path
import sys


def _load_support_module():
    try:
        from energy_ml.energy_ml.assets import feature_support as support_module

        return support_module
    except Exception:
        support_path = Path(__file__).with_name("feature_support.py")
        module_name = "energy_ml.energy_ml.assets.feature_support"
        existing_module = sys.modules.get(module_name)
        if existing_module is not None:
            return existing_module

        spec = importlib.util.spec_from_file_location(module_name, support_path)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module


_SUPPORT_MODULE = _load_support_module()
build_battery_features = _SUPPORT_MODULE.build_battery_features
build_definitions = _SUPPORT_MODULE.build_definitions
build_feature_matrix = _SUPPORT_MODULE.build_feature_matrix
build_generation_features = _SUPPORT_MODULE.build_generation_features
build_interaction_features = _SUPPORT_MODULE.build_interaction_features
build_price_features = _SUPPORT_MODULE.build_price_features
build_time_features = _SUPPORT_MODULE.build_time_features
build_weather_features = _SUPPORT_MODULE.build_weather_features

logger = logging.getLogger(__name__)


@asset(
    name="time_features",
    description="Time-based features extracted from timestamp",
    tags={"domain": "features", "category": "time"}
)
def time_features(weather_data: pd.DataFrame) -> Output[pd.DataFrame]:
    """Extract time-based features from timestamp."""
    
    logger.info("⏰ Generating time features...")
    
    df, metadata = build_time_features(weather_data)
    
    logger.info(f"✅ Generated {metadata['num_features']} time features")
    
    return Output(df, metadata=metadata)


@asset(
    name="weather_features",
    description="Normalized weather features with lags",
    tags={"domain": "features", "category": "weather"}
)
def weather_features(weather_data: pd.DataFrame, weather_forecast: pd.DataFrame) -> Output[pd.DataFrame]:
    """Extract and normalize weather features."""
    
    logger.info("🌤️ Generating weather features...")
    
    df, metadata = build_weather_features(weather_data, weather_forecast)
    
    logger.info(f"✅ Generated {metadata['num_features']} weather features")
    
    return Output(df, metadata=metadata)


@asset(
    name="generation_features",
    description="Solar and wind generation potential features",
    tags={"domain": "features", "category": "generation"}
)
def generation_features(solar_irradiance: pd.DataFrame, wind_potential: pd.DataFrame) -> Output[pd.DataFrame]:
    """Extract solar and wind generation features."""
    
    logger.info("⚡ Generating generation features...")
    
    df, metadata, summary = build_generation_features(solar_irradiance, wind_potential)
    
    logger.info(f"✅ Generated {metadata['num_features']} generation features")
    logger.info(f"   Solar: {summary['solar_power']:.2f} kW, Wind: {summary['wind_power']:.2f} kW, Total: {summary['total_potential']:.2f} kW")
    
    return Output(df, metadata=metadata)


@asset(
    name="battery_features",
    description="Battery state features and derived metrics",
    tags={"domain": "features", "category": "battery"}
)
def battery_features(battery_state: pd.DataFrame) -> Output[pd.DataFrame]:
    """Extract battery state features."""
    
    logger.info("🔋 Generating battery features...")
    
    df, metadata, summary = build_battery_features(battery_state)
    
    logger.info(f"✅ Generated {metadata['num_features']} battery features")
    logger.info(f"   SOC: {summary['soc']:.1f}%, Hours to empty: {summary['hours_to_empty']:.1f}h, Health: {summary['health']:.1f}%")
    
    return Output(df, metadata=metadata)


@asset(
    name="price_features",
    description="Price-based features with lags and statistics",
    tags={"domain": "features", "category": "price"}
)
def price_features(price_data_current: pd.DataFrame) -> Output[pd.DataFrame]:
    """Extract price-based features."""
    
    logger.info("💰 Generating price features...")
    
    df, metadata, summary = build_price_features(price_data_current)
    
    logger.info(f"✅ Generated {metadata['num_features']} price features")
    logger.info(f"   Price: {summary['price']:.2f} ₴/kWh ({summary['price_level']}), Volatility: {summary['volatility']:.2f}")
    
    return Output(df, metadata=metadata)


@asset(
    name="interaction_features",
    description="Complex interaction features combining multiple data sources",
    tags={"domain": "features", "category": "interactions"}
)
def interaction_features(
    time_features: pd.DataFrame,
    weather_features: pd.DataFrame,
    generation_features: pd.DataFrame,
    battery_features: pd.DataFrame,
    price_features: pd.DataFrame
) -> Output[pd.DataFrame]:
    """Create interaction and combined features."""
    
    logger.info("🔗 Generating interaction features...")
    
    df, metadata = build_interaction_features(
        time_features,
        weather_features,
        generation_features,
        battery_features,
        price_features,
    )
    
    logger.info(f"✅ Generated {metadata['num_features']} interaction features")
    
    return Output(df, metadata=metadata)


@asset(
    name="feature_matrix",
    description="Combined feature matrix (100+ features, ready for ML)",
    tags={"domain": "features", "type": "matrix"}
)
def feature_matrix(
    time_features: pd.DataFrame,
    weather_features: pd.DataFrame,
    generation_features: pd.DataFrame,
    battery_features: pd.DataFrame,
    price_features: pd.DataFrame,
    interaction_features: pd.DataFrame
) -> Output[pd.DataFrame]:
    """Combine all features into a single feature matrix."""
    
    logger.info("🧠 Building feature matrix...")
    
    combined, metadata, summary = build_feature_matrix(
        time_features,
        weather_features,
        generation_features,
        battery_features,
        price_features,
        interaction_features,
    )

    logger.info(f"✅ Feature matrix created: {summary['num_rows']} rows × {summary['num_features']} features")
    logger.info(f"   Features: Time({time_features.shape[1]}) + Weather({weather_features.shape[1]}) + " \
                f"Generation({generation_features.shape[1]}) + Battery({battery_features.shape[1]}) + " \
                f"Price({price_features.shape[1]}) + Interactions({interaction_features.shape[1]})")

    if metadata['missing_values'] > 0:
        logger.warning(f"⚠️ Found {metadata['missing_values']} missing values in feature matrix")
    if metadata['infinite_values'] > 0:
        logger.warning(f"⚠️ Found {metadata['infinite_values']} infinite values, replacing with max finite values")

    return Output(combined, metadata=metadata)


# Create Definitions object for Dagster
defs = build_definitions(
    [
        time_features,
        weather_features,
        generation_features,
        battery_features,
        price_features,
        interaction_features,
        feature_matrix,
    ]
)

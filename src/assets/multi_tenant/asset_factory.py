"""
Asset Factory - Multi-Tenant Dagster Asset Generation

Dynamically generates Dagster assets for multiple clients based on YAML configurations.
Implements the "Asset Factory" pattern for scalable multi-tenancy.

Thesis Relevance: Demonstrates how Software-Defined Assets can be programmatically 
generated for multi-tenant SaaS architecture without code duplication.
"""

from dagster import asset, AssetIn
from typing import Dict, List, Any, Optional, Set, Tuple
import yaml
from pathlib import Path
import logging
import re

logger = logging.getLogger(__name__)


def _normalize_tenant_id(raw_tenant_id: str) -> str:
    """Normalize tenant IDs into deterministic, storage-safe slugs."""
    normalized = re.sub(r'[^a-zA-Z0-9]+', '_', str(raw_tenant_id).strip().lower())
    normalized = re.sub(r'_+', '_', normalized).strip('_')
    return normalized or 'unknown_tenant'


def _build_tenant_descriptor(client_config: Dict[str, Any]) -> Dict[str, str]:
    raw_id = str(client_config.get('id', 'unknown_tenant'))
    normalized_id = _normalize_tenant_id(raw_id)
    return {
        'raw_id': raw_id,
        'normalized_id': normalized_id,
        'tenant_namespace': f"tenant/{normalized_id}",
        'storage_namespace': f"tenants/{normalized_id}",
        'asset_name': f"client_data_{normalized_id}",
    }


def _sanitize_shared_input(df):
    """Drop tenant-identifying columns from shared inputs before tenant projection."""
    import polars as pl

    drop_candidates = [
        'client_id',
        'client_name',
        'tenant_id',
        'tenant_namespace',
        'storage_namespace',
    ]
    present = [column for column in drop_candidates if column in df.columns]
    if not present:
        return df

    return df.drop(present)


def load_customer_configurations() -> List[Dict[str, Any]]:
    """Load customer configurations from YAML file."""
    config_path = Path("customers.yaml")
    
    if not config_path.exists():
        logger.warning("customers.yaml not found")
        return []
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
            return config_data.get('customers', [])
    except Exception as e:
        logger.error(f"Failed to load customer configurations: {e}")
        return []


def create_client_specific_asset(client_config: Dict[str, Any]):
    """
    Create a client-specific Dagster asset dynamically.
    
    This function returns a Dagster asset that processes data specifically
    for one client based on their configuration.
    """
    tenant = _build_tenant_descriptor(client_config)
    client_id = tenant['raw_id']
    normalized_id = tenant['normalized_id']
    client_name = client_config['name']
    
    @asset(
        name=tenant['asset_name'],
        key_prefix=["tenant", normalized_id],
        group_name=f"client_specific_{normalized_id}",
        description=f"Client-specific data processing for {client_name}",
        ins={
            "market_data": AssetIn("market_data_asset"),
            "weather_data": AssetIn("weather_asset"),
        },
        metadata={
            "client_id": client_id,
            "normalized_tenant_id": normalized_id,
            "tenant_namespace": tenant['tenant_namespace'],
            "storage_namespace": tenant['storage_namespace'],
            "client_name": client_name,
            "battery_capacity": client_config['energy_system']['battery_capacity_kwh'],
            "solar_capacity": client_config['energy_system']['solar_capacity_kw']
        }
    )
    def client_asset(market_data, weather_data):
        """Process data for a specific client."""
        import polars as pl
        from datetime import datetime
        
        # Client-specific processing logic
        logger.info(f"Processing data for client: {client_id}")
        
        # Merge market and weather data
        combined_df = _sanitize_shared_input(market_data).join(
            _sanitize_shared_input(weather_data),
            on="timestamp", 
            how="inner"
        )
        
        # Add client-specific features
        client_df = combined_df.with_columns([
            pl.lit(client_id).alias("client_id"),
            pl.lit(normalized_id).alias("tenant_id"),
            pl.lit(tenant['tenant_namespace']).alias("tenant_namespace"),
            pl.lit(tenant['storage_namespace']).alias("storage_namespace"),
            pl.lit(client_name).alias("client_name"),
            
            # Battery system specifications
            pl.lit(client_config['energy_system']['battery_capacity_kwh']).alias("battery_capacity_kwh"),
            pl.lit(client_config['energy_system']['solar_capacity_kw']).alias("solar_capacity_kw"),
            pl.lit(client_config['energy_system']['peak_load_kw']).alias("peak_load_kw"),
            
            # Economic parameters
            pl.lit(client_config['economic_params']['electricity_tariff']).alias("electricity_tariff"),
            pl.lit(client_config['economic_params']['feed_in_tariff']).alias("feed_in_tariff"),
            
            # Processing timestamp
            pl.lit(datetime.now()).alias("processed_at")
        ])

        # Tenant-isolation guard: any accidental non-matching tenant assignment is rejected.
        if "client_id" in client_df.columns:
            leakage_count = client_df.filter(pl.col("client_id") != client_id).height
            if leakage_count > 0:
                raise ValueError(
                    f"Tenant isolation breach: found {leakage_count} rows outside tenant '{client_id}'"
                )
        
        # Client-specific solar generation calculation
        solar_capacity = client_config['energy_system']['solar_capacity_kw']
        client_df = client_df.with_columns([
            # More accurate solar generation based on client's system
            (pl.col("solar_radiation") / 1000.0 * solar_capacity * 0.20 * 0.85).alias("solar_generation_kw"),
            
            # Load profile simulation based on client type
            _calculate_load_profile(client_config, pl.col("timestamp")).alias("load_kw"),
            
            # Economic value calculations
            (pl.col("price_eur_mwh") / 1000.0 * pl.col("electricity_tariff")).alias("grid_cost_eur_kwh")
        ])
        
        logger.info(f"Generated {len(client_df)} records for {client_name}")
        return client_df
    
    return client_asset


def _calculate_load_profile(client_config: Dict, timestamp_col):
    """Calculate load profile based on client configuration and time."""
    import polars as pl
    
    base_load = client_config['energy_system']['base_load_kw']
    peak_load = client_config['energy_system']['peak_load_kw']
    load_profile = client_config['energy_system']['load_profile']
    
    # Simplified load profile calculation for the asset factory
    # In production, this would use more sophisticated models
    
    if load_profile == "commercial":
        # Shopping mall: high during day, low at night
        load_factor = (pl.when(timestamp_col.dt.hour().is_between(9, 21))
                       .then(0.8)
                       .otherwise(0.3))
    elif load_profile == "office":
        # Office: weekday business hours
        load_factor = (pl.when(
            (timestamp_col.dt.weekday() < 5) & 
            timestamp_col.dt.hour().is_between(8, 18)
        ).then(0.7).otherwise(0.3))
    elif load_profile == "industrial":
        # Manufacturing: consistent high load
        load_factor = (pl.when(timestamp_col.dt.hour().is_between(6, 22))
                       .then(0.8)
                       .otherwise(0.5))
    elif load_profile == "hospital":
        # Critical: always high, varies slightly
        load_factor = pl.lit(0.75) + pl.col("timestamp").dt.hour() * 0.01
    elif load_profile == "hotel":
        # Hospitality: high evening/night
        load_factor = (pl.when(timestamp_col.dt.hour().is_between(18, 23))
                       .then(0.8)
                       .otherwise(0.5))
    else:
        # Default residential-like pattern
        load_factor = pl.lit(0.6)
    
    return base_load + (peak_load - base_load) * load_factor


def generate_client_assets() -> List:
    """
    Generate Dagster assets for all clients dynamically.
    
    This is the core "Asset Factory" function that creates individual
    assets for each client configuration.
    """
    logger.info("Starting asset factory generation...")
    
    # Load client configurations
    client_configs = load_customer_configurations()
    
    if not client_configs:
        logger.warning("No client configurations found, creating fallback asset")
        return []
    
    # Generate assets for each client
    client_assets = []
    seen_normalized_ids: Set[str] = set()
    
    for config in client_configs:
        try:
            tenant = _build_tenant_descriptor(config)
            normalized_id = tenant['normalized_id']
            if normalized_id in seen_normalized_ids:
                logger.error(
                    "Skipping duplicate tenant after normalization: raw_id=%s normalized_id=%s",
                    config.get('id'),
                    normalized_id,
                )
                continue

            seen_normalized_ids.add(normalized_id)
            client_asset = create_client_specific_asset(config)
            client_assets.append(client_asset)
            logger.info(
                "Created isolated asset for client: raw_id=%s normalized_id=%s namespace=%s",
                config.get('id'),
                normalized_id,
                tenant['tenant_namespace'],
            )
        except Exception as e:
            logger.error(f"Failed to create asset for {config['id']}: {e}")
            continue
    
    logger.info(f"Asset factory generated {len(client_assets)} client assets")
    return client_assets


@asset(
    group_name="aggregation",
    description="Aggregated analytics across all clients",
    deps=["market_data_asset", "weather_asset"]
)
def multi_client_analytics():
    """
    Cross-client analytics and benchmarking.
    
    This asset aggregates data across all clients to provide
    comparative analytics and system-wide insights.
    """
    import polars as pl
    from datetime import datetime
    
    logger.info("Computing multi-client analytics...")
    
    # Load client configurations for metadata
    client_configs = load_customer_configurations()
    
    if not client_configs:
        logger.warning("No client configs for analytics")
        return pl.DataFrame()
    
    # Create summary analytics
    analytics_data = []
    
    for config in client_configs:
        client_id = config['id']
        client_name = config['name']
        
        # Client system specifications
        battery_kwh = config['energy_system']['battery_capacity_kwh']
        solar_kw = config['energy_system']['solar_capacity_kw']
        peak_load_kw = config['energy_system']['peak_load_kw']
        
        # Calculate key metrics
        storage_ratio = battery_kwh / peak_load_kw  # Hours of backup
        solar_ratio = solar_kw / peak_load_kw       # Solar coverage ratio
        
        analytics_record = {
            'client_id': client_id,
            'client_name': client_name,
            'client_type': config['type'],
            'battery_capacity_kwh': battery_kwh,
            'solar_capacity_kw': solar_kw,
            'peak_load_kw': peak_load_kw,
            'storage_hours': storage_ratio,
            'solar_coverage_ratio': solar_ratio,
            'electricity_tariff': config['economic_params']['electricity_tariff'],
            'feed_in_tariff': config['economic_params']['feed_in_tariff'],
            'location_lat': config['location']['lat'],
            'location_lon': config['location']['lon'],
            'analysis_timestamp': datetime.now()
        }
        
        analytics_data.append(analytics_record)
    
    # Convert to DataFrame
    analytics_df = pl.DataFrame(analytics_data)
    
    # Add comparative rankings
    analytics_df = analytics_df.with_columns([
        pl.col("storage_hours").rank(descending=True).alias("storage_rank"),
        pl.col("solar_coverage_ratio").rank(descending=True).alias("solar_rank"),
        pl.col("electricity_tariff").rank(descending=False).alias("tariff_rank")  # Lower is better
    ])
    
    # Add system classifications
    analytics_df = analytics_df.with_columns([
        pl.when(pl.col("storage_hours") > 2.0)
        .then(pl.lit("high_storage"))
        .when(pl.col("storage_hours") > 1.0)
        .then(pl.lit("medium_storage"))
        .otherwise(pl.lit("low_storage"))
        .alias("storage_class"),
        
        pl.when(pl.col("solar_coverage_ratio") > 1.0)
        .then(pl.lit("over_sized_solar"))
        .when(pl.col("solar_coverage_ratio") > 0.5)
        .then(pl.lit("adequate_solar"))
        .otherwise(pl.lit("under_sized_solar"))
        .alias("solar_class")
    ])
    
    logger.info(f"Multi-client analytics complete: {len(analytics_df)} clients analyzed")
    return analytics_df


# Asset factory execution
def create_all_assets():
    """
    Main function to create all assets using the factory pattern.
    This would be called during Dagster definitions loading.
    """
    # Generate client-specific assets
    client_assets = generate_client_assets()
    
    # Add the multi-client analytics asset
    analytics_asset = multi_client_analytics
    
    # Combine all assets
    all_assets = client_assets + [analytics_asset]
    
    logger.info(f"Asset factory created {len(all_assets)} total assets")
    return all_assets


# For testing and development
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("🏭 Testing Asset Factory...")
    
    # Test configuration loading
    configs = load_customer_configurations()
    print(f"📋 Loaded {len(configs)} client configurations")
    
    # Test asset generation
    assets = generate_client_assets()
    print(f"🏗️ Generated {len(assets)} client assets")
    
    print("✅ Asset Factory test complete!")
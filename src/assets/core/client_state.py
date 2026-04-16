"""
Client State Asset - Synthetic Battery & System State

Dagster asset for generating synthetic client state data based on user configurations.
Stage 1 implementation - no real IoT, using user energy capability settings.

Thesis Relevance: Demonstrates multi-tenant system state modeling without
requiring physical IoT devices in development phase.
"""

import polars as pl
from dagster import asset
import logging
from typing import Dict, List

from src.data_pipeline.battery_state_loader import (
    CONFIG_STATE_SOURCE,
    SIMULATOR_STATE_SOURCE,
    _load_operational_battery_state,
    _normalize_tenant_id,
)
from src.data_pipeline.battery_simulation import (
    _calculate_battery_voltage,
    _simulate_battery_behavior,
    _update_battery_state,
)
from src.data_pipeline.client_config_loader import (
    _get_default_client_configs,
    _load_client_configurations,
)
from src.data_pipeline.client_state_validation import (
    _generate_fallback_client_data,
    _validate_client_data,
)
from src.data_pipeline.client_load_solar_simulation import (
    _calculate_load_consumption,
    _calculate_solar_generation,
)
from src.data_pipeline.system_monitoring import (
    _calculate_system_efficiency,
    _get_inverter_status,
)

logger = logging.getLogger(__name__)


@asset(
    group_name="client_data",
    description="Client state data seeded from simulator-backed battery telemetry when available, with config fallback for missing operational state",
    deps=["weather_asset", "market_data_asset"],
    metadata={
        "source": "Simulator-backed tenant battery state with config fallback",
        "update_frequency": "Hourly",
        "stage": "Stage 1 - Simulator-backed operational telemetry with config fallback"
    }
)
def client_state_asset(weather_asset: pl.DataFrame, market_data_asset: pl.DataFrame) -> pl.DataFrame:
    """
    Generate client state data with simulator-backed battery state when available.
    
    In Stage 1, we preserve the dashboard simulator-backed battery state when present and
    only fall back to configuration defaults for missing operational state. Load and solar
    remain derived from deterministic config, weather, and market signals.

    Inputs used in the current path:
    - Simulator-backed battery state persisted by the dashboard battery loop
    - User-defined energy capabilities (battery size, solar capacity, load profile)
    - Weather conditions (for solar generation simulation)
    - Market prices (for charging/discharging behavior simulation)
    """

    logger.info("Generating synthetic client state data")

    try:
        client_configs = _load_client_configurations()

        if not client_configs:
            logger.warning("No client configurations found, using default")
            client_configs = _get_default_client_configs()

        all_client_data = []

        for client_config in client_configs:
            client_data = _generate_client_state(
                client_config, weather_asset, market_data_asset
            )
            all_client_data.extend(client_data)

        df = pl.DataFrame(all_client_data)
        df = _validate_client_data(df)

        logger.info(
            "Client state asset materialized: %s records for %s clients",
            len(df),
            len(client_configs),
        )
        return df

    except Exception as exc:
        logger.error("Failed to generate client state data: %s", exc)
        return pl.DataFrame(_generate_fallback_client_data())

def _generate_client_state(config: Dict, weather_df: pl.DataFrame, market_df: pl.DataFrame) -> List[Dict]:
    """Generate synthetic state data for a specific client."""
    client_id = config.get('id', 'unknown_client')
    tenant_id = config.get('tenant_id', _normalize_tenant_id(client_id))
    tenant_namespace = config.get('tenant_namespace', f"tenant/{tenant_id}")
    storage_namespace = config.get('storage_namespace', f"tenants/{tenant_id}")
    logger.info(f"Generating state data for client: {client_id}")
    
    # Get weather data for client location (simplified - use first available)
    weather_data = weather_df.to_dicts()
    market_data = market_df.to_dicts()
    battery_state = _load_operational_battery_state(config)
    
    # Initialize battery state from persisted simulator telemetry when available.
    current_soc = float(battery_state['soc'])
    battery_temp = float(battery_state['temperature'])
    battery_voltage = float(battery_state['voltage'])
    battery_current = float(battery_state['current'])
    battery_health = float(battery_state['health'])
    battery_cycles = float(battery_state['cycles'])
    
    client_records = []
    
    # Generate hourly data for the forecast period
    for i, (weather_row, market_row) in enumerate(zip(weather_data, market_data)):
        timestamp = weather_row['timestamp']
        
        # Solar generation based on weather and system capacity
        solar_gen = _calculate_solar_generation(
            config, weather_row['solar_radiation'], weather_row['cloudcover']
        )
        
        # Load consumption based on time of day and load profile
        load_actual = _calculate_load_consumption(config, timestamp)
        
        # Battery behavior based on market prices and system state
        _, power_flow = _simulate_battery_behavior(
            config, current_soc, market_row['price_eur_mwh'], solar_gen, load_actual
        )
        
        # Update battery state
        current_soc, battery_temp = _update_battery_state(
            current_soc, battery_temp, power_flow, config, weather_row['temperature']
        )
        
        # Calculate grid power (positive = import, negative = export)
        grid_power = load_actual - solar_gen + power_flow
        
        # System efficiency based on current conditions
        system_efficiency = _calculate_system_efficiency(current_soc, battery_temp)
        
        # Inverter status simulation
        inverter_status = _get_inverter_status(power_flow, current_soc)
        
        record = {
            'timestamp': timestamp,
            'client_id': client_id,
            'tenant_id': tenant_id,
            'tenant_namespace': tenant_namespace,
            'storage_namespace': storage_namespace,
            'battery_soc': current_soc,
            'battery_health': battery_health,
            'battery_cycles': battery_cycles,
            'battery_temp': battery_temp,
            'battery_voltage': battery_voltage if i == 0 else _calculate_battery_voltage(current_soc, config.get('battery_type', 'LFP_280Ah')),
            'battery_current': battery_current if i == 0 else power_flow,
            'solar_gen_actual': solar_gen,
            'load_actual': load_actual,
            'grid_power': grid_power,
            'battery_power': power_flow,
            'inverter_status': inverter_status,
            'system_efficiency': system_efficiency,
            'source': battery_state['source'],
            'state_source': battery_state['state_source'],
            'state_source_detail': battery_state['state_source_detail'],
            'battery_state_updated_at': battery_state['last_update'],
            'telemetry_classification': battery_state['telemetry_classification'],
        }
        
        client_records.append(record)
        
    return client_records

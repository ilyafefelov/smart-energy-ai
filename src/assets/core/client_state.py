"""
Client State Asset - Synthetic Battery & System State

Dagster asset for generating synthetic client state data based on user configurations.
Stage 1 implementation - no real IoT, using user energy capability settings.

Thesis Relevance: Demonstrates multi-tenant system state modeling without
requiring physical IoT devices in development phase.
"""

import polars as pl
from dagster import asset, MetadataValue
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Any
import numpy as np
import yaml
from pathlib import Path
import re

logger = logging.getLogger(__name__)


def _normalize_tenant_id(raw_tenant_id: str) -> str:
    normalized = re.sub(r'[^a-zA-Z0-9]+', '_', str(raw_tenant_id).strip().lower())
    normalized = re.sub(r'_+', '_', normalized).strip('_')
    return normalized or 'unknown_tenant'


@asset(
    group_name="client_data",
    description="Synthetic client state data based on user energy configurations",
    deps=["weather_asset", "market_data_asset"],
    metadata={
        "source": "User Configuration + Synthetic Generation",
        "update_frequency": "Hourly",
        "stage": "Stage 1 - Synthetic Data"
    }
)
def client_state_asset(weather_asset: pl.DataFrame, market_data_asset: pl.DataFrame) -> pl.DataFrame:
    """
    Generate synthetic client state data based on user energy configurations.
    
    In Stage 1, we simulate battery and system states based on:
    - User-defined energy capabilities (battery size, solar capacity, load profile)
    - Weather conditions (for solar generation simulation)
    - Market prices (for charging/discharging behavior simulation)
    
    Returns:
        Polars DataFrame with columns:
        - timestamp: Hour timestamp
        - client_id: Client identifier
        - battery_soc: State of charge (%)
        - battery_temp: Battery temperature (°C)
        - battery_voltage: Battery voltage (V)
        - solar_gen_actual: Solar generation (kW)
        - load_actual: Load consumption (kW)  
        - grid_power: Grid power flow (kW, positive = import)
        - inverter_status: Inverter status code
        - system_efficiency: Overall system efficiency (%)
        - source: Data source identifier
    """
    logger.info("Generating synthetic client state data")
    
    try:
        # Load client configurations
        client_configs = _load_client_configurations()
        
        if not client_configs:
            logger.warning("No client configurations found, using default")
            client_configs = _get_default_client_configs()
            
        # Generate synthetic state for each client
        all_client_data = []
        
        for client_config in client_configs:
            client_data = _generate_client_state(
                client_config, weather_asset, market_data_asset
            )
            all_client_data.extend(client_data)
            
        # Convert to Polars DataFrame
        df = pl.DataFrame(all_client_data)
        
        # Data validation and quality checks
        df = _validate_client_data(df)
        
        logger.info(f"Client state asset materialized: {len(df)} records for {len(client_configs)} clients")
        return df
        
    except Exception as e:
        logger.error(f"Failed to generate client state data: {e}")
        # Return minimal synthetic data as failsafe
        return pl.DataFrame(_generate_fallback_client_data())


def _load_client_configurations() -> List[Dict]:
    """Load client configurations from YAML file."""
    config_path = Path("customers.yaml")
    
    if not config_path.exists():
        logger.info("customers.yaml not found, using embedded configurations")
        return []
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
            raw_customers = config_data.get('customers', []) if isinstance(config_data, dict) else []
            normalized_customers = [_normalize_client_config(customer) for customer in raw_customers]
            return [customer for customer in normalized_customers if customer]
    except Exception as e:
        logger.error(f"Failed to load customer configurations: {e}")
        return []


def _normalize_client_config(raw_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize customer config to flat keys expected by synthetic state generator."""
    if not isinstance(raw_config, dict):
        logger.warning("Skipping invalid customer config row: expected object")
        return None

    energy_system = raw_config.get("energy_system")
    if not isinstance(energy_system, dict):
        energy_system = {}

    client_id = raw_config.get("id")
    if not client_id:
        logger.warning("Skipping customer config without 'id'")
        return None

    normalized_tenant_id = _normalize_tenant_id(str(client_id))

    normalized: Dict[str, Any] = dict(raw_config)
    normalized["battery_type"] = energy_system.get("battery_type", raw_config.get("battery_type", "LFP_280Ah"))
    normalized["battery_capacity_kwh"] = float(
        energy_system.get("battery_capacity_kwh", raw_config.get("battery_capacity_kwh", 200.0))
    )
    normalized["solar_capacity_kw"] = float(
        energy_system.get("solar_capacity_kw", raw_config.get("solar_capacity_kw", 0.0))
    )
    normalized["peak_load_kw"] = float(
        energy_system.get("peak_load_kw", raw_config.get("peak_load_kw", 120.0))
    )
    normalized["base_load_kw"] = float(
        energy_system.get("base_load_kw", raw_config.get("base_load_kw", 30.0))
    )
    normalized["load_profile"] = energy_system.get(
        "load_profile",
        raw_config.get("load_profile", raw_config.get("type", "commercial")),
    )
    normalized["tenant_id"] = normalized_tenant_id
    normalized["tenant_namespace"] = f"tenant/{normalized_tenant_id}"
    normalized["storage_namespace"] = f"tenants/{normalized_tenant_id}"
    return normalized


def _get_default_client_configs() -> List[Dict]:
    """Get default client configurations for development."""
    return [
        {
            'id': 'client_001_kyiv_mall',
            'name': 'Kyiv Shopping Mall',
            'location': {'lat': 50.45, 'lon': 30.52},
            'battery_type': 'LFP_280Ah',
            'battery_capacity_kwh': 280.0,
            'solar_capacity_kw': 150.0,
            'peak_load_kw': 200.0,
            'base_load_kw': 50.0,
            'load_profile': 'commercial',
            'tenant_id': 'client_001_kyiv_mall',
            'tenant_namespace': 'tenant/client_001_kyiv_mall',
            'storage_namespace': 'tenants/client_001_kyiv_mall',
        },
        {
            'id': 'client_002_lviv_office',
            'name': 'Lviv Business Center',
            'location': {'lat': 49.84, 'lon': 24.03},
            'battery_type': 'NMC_LG_Chem',
            'battery_capacity_kwh': 150.0,
            'solar_capacity_kw': 80.0,
            'peak_load_kw': 120.0,
            'base_load_kw': 30.0,
            'load_profile': 'office',
            'tenant_id': 'client_002_lviv_office',
            'tenant_namespace': 'tenant/client_002_lviv_office',
            'storage_namespace': 'tenants/client_002_lviv_office',
        },
        {
            'id': 'client_003_dnipro_factory',
            'name': 'Dnipro Manufacturing',
            'location': {'lat': 48.46, 'lon': 35.04},
            'battery_type': 'LFP_280Ah',
            'battery_capacity_kwh': 500.0,
            'solar_capacity_kw': 300.0,
            'peak_load_kw': 400.0,
            'base_load_kw': 150.0,
            'load_profile': 'industrial',
            'tenant_id': 'client_003_dnipro_factory',
            'tenant_namespace': 'tenant/client_003_dnipro_factory',
            'storage_namespace': 'tenants/client_003_dnipro_factory',
        }
    ]


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
    
    # Initialize battery state
    current_soc = 50.0  # Start at 50% SoC
    battery_temp = 25.0  # Start at optimal temperature
    
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
        battery_action, power_flow = _simulate_battery_behavior(
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
            'battery_temp': battery_temp,
            'battery_voltage': _calculate_battery_voltage(current_soc, config.get('battery_type', 'LFP_280Ah')),
            'solar_gen_actual': solar_gen,
            'load_actual': load_actual,
            'grid_power': grid_power,
            'battery_power': power_flow,
            'inverter_status': inverter_status,
            'system_efficiency': system_efficiency,
            'source': 'SYNTHETIC'
        }
        
        client_records.append(record)
        
    return client_records


def _calculate_solar_generation(config: Dict, solar_radiation: float, cloudcover: float) -> float:
    """Calculate solar generation based on weather conditions."""
    solar_capacity = float(config.get('solar_capacity_kw', 0.0))
    
    # Convert solar radiation (W/m²) to generation factor
    # Typical solar panel efficiency: ~20%, system losses: ~15%
    panel_efficiency = 0.20
    system_efficiency = 0.85
    standard_irradiance = 1000.0  # W/m² (STC)
    
    # Generation factor based on irradiance
    generation_factor = (solar_radiation / standard_irradiance) * panel_efficiency * system_efficiency
    
    # Cloud cover impact (already partially reflected in solar_radiation)
    cloud_factor = (100 - cloudcover) / 100 * 0.1 + 0.9  # Minimal additional cloud effect
    
    # Calculate generation
    solar_gen = solar_capacity * generation_factor * cloud_factor
    
    return max(0, solar_gen)


def _calculate_load_consumption(config: Dict, timestamp: datetime) -> float:
    """Calculate load consumption based on time and load profile."""
    base_load = float(config.get('base_load_kw', 30.0))
    peak_load = float(config.get('peak_load_kw', 120.0))
    load_profile = config.get('load_profile', 'commercial')
    
    hour = timestamp.hour
    day_of_week = timestamp.weekday()
    
    # Load profile patterns
    if load_profile == 'commercial':
        # Shopping mall pattern
        if day_of_week < 5:  # Weekday
            if 9 <= hour <= 21:  # Business hours
                load_factor = 0.7 + 0.3 * np.sin((hour - 9) * np.pi / 12)
            else:
                load_factor = 0.3
        else:  # Weekend
            if 10 <= hour <= 22:
                load_factor = 0.9 + 0.1 * np.sin((hour - 10) * np.pi / 12)
            else:
                load_factor = 0.3
    
    elif load_profile == 'office':
        # Office building pattern
        if day_of_week < 5:  # Weekday
            if 8 <= hour <= 18:
                load_factor = 0.8
            elif 6 <= hour <= 8 or 18 <= hour <= 20:
                load_factor = 0.4
            else:
                load_factor = 0.2
        else:  # Weekend
            load_factor = 0.3
    
    elif load_profile == 'industrial':
        # Manufacturing pattern (more consistent)
        if day_of_week < 5:  # Weekday
            if 6 <= hour <= 22:
                load_factor = 0.85 + 0.1 * np.random.normal(0, 0.1)
            else:
                load_factor = 0.4
        else:  # Weekend
            load_factor = 0.5
    
    else:
        # Default residential pattern
        if 7 <= hour <= 9 or 17 <= hour <= 22:
            load_factor = 0.8
        elif 22 <= hour or hour <= 6:
            load_factor = 0.3
        else:
            load_factor = 0.5
    
    # Calculate actual load
    load_variation = base_load + (peak_load - base_load) * max(0, min(1, load_factor))
    
    # Add some random variation
    load_actual = load_variation * (1 + np.random.normal(0, 0.05))
    
    return max(base_load * 0.5, load_actual)  # Minimum 50% of base load


def _simulate_battery_behavior(config: Dict, current_soc: float, price: float, 
                             solar_gen: float, load: float) -> tuple[str, float]:
    """Simulate battery charging/discharging behavior."""
    battery_capacity = float(config.get('battery_capacity_kwh', 200.0))
    
    # Simple arbitrage strategy
    # Charge when prices are low or excess solar
    # Discharge when prices are high or insufficient solar
    
    net_load = load - solar_gen  # Positive = deficit, negative = surplus
    
    # Price thresholds (simplified)
    low_price_threshold = 40  # EUR/MWh
    high_price_threshold = 70  # EUR/MWh
    
    # Battery power limits (C-rate = 0.5)
    max_charge_power = battery_capacity * 0.5  # kW
    max_discharge_power = battery_capacity * 0.5  # kW
    
    if net_load < -10:  # Significant solar surplus
        # Charge battery with excess solar
        available_power = abs(net_load)
        charge_power = min(available_power, max_charge_power, 
                          (100 - current_soc) / 100 * battery_capacity)
        return "CHARGE_SOLAR", charge_power
        
    elif price < low_price_threshold and current_soc < 90:
        # Cheap electricity - charge from grid
        charge_power = min(max_charge_power, (90 - current_soc) / 100 * battery_capacity)
        return "CHARGE_GRID", charge_power
        
    elif price > high_price_threshold and current_soc > 20:
        # Expensive electricity - discharge battery
        discharge_power = min(max_discharge_power, net_load, 
                            (current_soc - 20) / 100 * battery_capacity)
        return "DISCHARGE", -discharge_power  # Negative = discharge
        
    elif net_load > 0 and current_soc > 30:
        # Load demand - use battery if available
        discharge_power = min(max_discharge_power, net_load * 0.7,
                            (current_soc - 20) / 100 * battery_capacity)
        return "DISCHARGE_LOAD", -discharge_power
        
    else:
        # Idle state
        return "IDLE", 0.0


def _update_battery_state(current_soc: float, current_temp: float, power_flow: float,
                         config: Dict, ambient_temp: float) -> tuple[float, float]:
    """Update battery SoC and temperature based on power flow."""
    battery_capacity = float(config.get('battery_capacity_kwh', 200.0))
    
    # Update SoC (assuming 1-hour time step)
    # Positive power_flow = charging, negative = discharging
    efficiency = 0.95 if power_flow > 0 else 1/0.95  # Round-trip efficiency
    
    soc_change = (power_flow * efficiency) / battery_capacity * 100  # Percentage change
    new_soc = max(0, min(100, current_soc + soc_change))
    
    # Update temperature (simplified thermal model)
    # Battery heats up during operation, cools towards ambient
    power_heating = abs(power_flow) * 0.05  # 5% losses as heat
    thermal_mass = battery_capacity * 0.5  # Simplified thermal mass
    
    temp_rise = power_heating / thermal_mass  # °C per hour
    cooling_rate = (current_temp - ambient_temp) * 0.1  # Cooling towards ambient
    
    new_temp = current_temp + temp_rise - cooling_rate
    new_temp = max(ambient_temp - 5, min(ambient_temp + 30, new_temp))  # Bounds
    
    return new_soc, new_temp


def _calculate_battery_voltage(soc: float, battery_type: str) -> float:
    """Calculate battery voltage based on SoC and type."""
    if battery_type.startswith('LFP'):
        # LFP voltage curve (simplified)
        base_voltage = 3.2  # Nominal voltage per cell
        cells_in_series = 280  # Typical for 280kWh pack
        voltage_variation = 0.4 * (soc / 100)  # Voltage rises with SoC
        return (base_voltage + voltage_variation) * cells_in_series
    
    elif battery_type.startswith('NMC'):
        # NMC voltage curve
        base_voltage = 3.7
        cells_in_series = 150
        voltage_variation = 0.5 * (soc / 100)
        return (base_voltage + voltage_variation) * cells_in_series
    
    else:
        # Default voltage calculation
        return 800 + (soc / 100) * 100  # 800-900V range


def _calculate_system_efficiency(soc: float, temp: float) -> float:
    """Calculate overall system efficiency based on conditions."""
    base_efficiency = 0.92  # 92% base efficiency
    
    # Temperature derating
    if temp > 35:
        temp_factor = 1 - (temp - 35) * 0.01  # 1% per degree above 35°C
    elif temp < 10:
        temp_factor = 1 - (10 - temp) * 0.005  # 0.5% per degree below 10°C
    else:
        temp_factor = 1.0
    
    # SoC efficiency (slightly lower at extremes)
    if soc < 20 or soc > 90:
        soc_factor = 0.98
    else:
        soc_factor = 1.0
    
    return base_efficiency * temp_factor * soc_factor


def _get_inverter_status(power_flow: float, soc: float) -> str:
    """Get inverter status code."""
    if abs(power_flow) < 1:
        return "IDLE"
    elif power_flow > 0:
        return "CHARGING"
    else:
        return "DISCHARGING"


def _validate_client_data(df: pl.DataFrame) -> pl.DataFrame:
    """Validate and clean client state data."""
    logger.info(f"Validating client state data: {len(df)} records")
    
    # Clean invalid values
    df = df.with_columns([
        # SoC bounds (0-100%)
        pl.col('battery_soc').clip(0, 100).alias('battery_soc'),
        
        # Temperature bounds (-10°C to 60°C)
        pl.col('battery_temp').clip(-10, 60).alias('battery_temp'),
        
        # Power bounds (reasonable ranges)
        pl.col('solar_gen_actual').clip(0, 1000).alias('solar_gen_actual'),
        pl.col('load_actual').clip(0, 1000).alias('load_actual'),
        pl.col('grid_power').clip(-1000, 1000).alias('grid_power'),
        
        # System efficiency bounds (50-100%)
        pl.col('system_efficiency').clip(0.5, 1.0).alias('system_efficiency'),
    ])
    
    # Sort by client and timestamp
    df = df.sort(['client_id', 'timestamp'])
    
    # Add quality indicators
    df = df.with_columns([
        (pl.col('battery_soc') < 10).alias('low_battery_warning'),
        (pl.col('battery_temp') > 40).alias('high_temp_warning'),
        (pl.col('grid_power').abs() > 500).alias('high_grid_usage'),
        pl.lit(datetime.now()).alias('generated_at')
    ])
    
    logger.info(f"Client data validation complete: {len(df)} valid records")
    return df


def _generate_fallback_client_data() -> List[Dict]:
    """Generate minimal fallback data in case of errors."""
    base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    fallback_data = []
    
    for hour in range(24):
        timestamp = base_time + timedelta(hours=hour)
        
        fallback_data.append({
            'timestamp': timestamp,
            'client_id': 'fallback_client',
            'battery_soc': 50.0,
            'battery_temp': 25.0,
            'battery_voltage': 800.0,
            'solar_gen_actual': 0.0,
            'load_actual': 100.0,
            'grid_power': 100.0,
            'battery_power': 0.0,
            'inverter_status': 'IDLE',
            'system_efficiency': 0.90,
            'source': 'FALLBACK'
        })
        
    return fallback_data


# Test and validation functions
def test_client_state_asset():
    """Test client state asset functionality."""
    # Create mock input data
    mock_weather = pl.DataFrame([
        {'timestamp': datetime.now(), 'solar_radiation': 500, 'cloudcover': 30, 'temperature': 20}
    ])
    mock_market = pl.DataFrame([
        {'timestamp': datetime.now(), 'price_eur_mwh': 50}
    ])
    
    df = client_state_asset(mock_weather, mock_market)
    
    assert len(df) > 0, "Client state data should contain records"
    assert 'client_id' in df.columns, "Client ID column required"
    assert 'battery_soc' in df.columns, "Battery SoC column required"
    assert 'solar_gen_actual' in df.columns, "Solar generation column required"
    
    # Check data quality
    assert df['battery_soc'].min() >= 0, "SoC should be non-negative"
    assert df['battery_soc'].max() <= 100, "SoC should not exceed 100%"
    
    print(f"✅ Client state test passed: {len(df)} records")
    return True


if __name__ == "__main__":
    # Test the asset
    test_client_state_asset()
    
    print("Client state asset test complete")
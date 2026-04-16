"""Helpers for loading and normalizing client configuration profiles."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.data_pipeline.battery_state_loader import _normalize_tenant_id


logger = logging.getLogger(__name__)


def _load_client_configurations() -> List[Dict[str, Any]]:
    """Load client configurations from `customers.yaml`."""

    config_path = Path("customers.yaml")
    if not config_path.exists():
        logger.info("customers.yaml not found, using embedded configurations")
        return []

    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            config_data = yaml.safe_load(handle)
            raw_customers = config_data.get("customers", []) if isinstance(config_data, dict) else []
            normalized_customers = [_normalize_client_config(customer) for customer in raw_customers]
            return [customer for customer in normalized_customers if customer]
    except Exception as exc:
        logger.error("Failed to load customer configurations: %s", exc)
        return []


def _normalize_client_config(raw_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize customer config to flat keys expected by the client state generator."""

    if not isinstance(raw_config, dict):
        logger.warning("Skipping invalid customer config row: expected object")
        return None

    merged_config: Dict[str, Any] = dict(raw_config)
    energy_system_overrides = raw_config.get("energy_system")
    if isinstance(energy_system_overrides, dict):
        merged_config.update(energy_system_overrides)

    client_id = raw_config.get("id")
    if not client_id:
        logger.warning("Skipping customer config without 'id'")
        return None

    normalized_tenant_id = _normalize_tenant_id(str(client_id))

    normalized: Dict[str, Any] = dict(raw_config)
    normalized["battery_type"] = merged_config.get("battery_type", "LFP_280Ah")
    normalized["battery_capacity_kwh"] = float(merged_config.get("battery_capacity_kwh", 200.0))
    normalized["solar_capacity_kw"] = float(merged_config.get("solar_capacity_kw", 0.0))
    normalized["peak_load_kw"] = float(merged_config.get("peak_load_kw", 120.0))
    normalized["base_load_kw"] = float(merged_config.get("base_load_kw", 30.0))
    normalized["load_profile"] = merged_config.get("load_profile", raw_config.get("type", "commercial"))
    normalized["tenant_id"] = normalized_tenant_id
    normalized["tenant_namespace"] = f"tenant/{normalized_tenant_id}"
    normalized["storage_namespace"] = f"tenants/{normalized_tenant_id}"
    return normalized


def _get_default_client_configs() -> List[Dict[str, Any]]:
    """Return embedded default client configurations for development fallback."""

    return [
        {
            "id": "client_001_kyiv_mall",
            "name": "Kyiv Shopping Mall",
            "location": {"lat": 50.45, "lon": 30.52},
            "battery_type": "LFP_280Ah",
            "battery_capacity_kwh": 280.0,
            "solar_capacity_kw": 150.0,
            "peak_load_kw": 200.0,
            "base_load_kw": 50.0,
            "load_profile": "commercial",
            "tenant_id": "client_001_kyiv_mall",
            "tenant_namespace": "tenant/client_001_kyiv_mall",
            "storage_namespace": "tenants/client_001_kyiv_mall",
        },
        {
            "id": "client_002_lviv_office",
            "name": "Lviv Business Center",
            "location": {"lat": 49.84, "lon": 24.03},
            "battery_type": "NMC_LG_Chem",
            "battery_capacity_kwh": 150.0,
            "solar_capacity_kw": 80.0,
            "peak_load_kw": 120.0,
            "base_load_kw": 30.0,
            "load_profile": "office",
            "tenant_id": "client_002_lviv_office",
            "tenant_namespace": "tenant/client_002_lviv_office",
            "storage_namespace": "tenants/client_002_lviv_office",
        },
        {
            "id": "client_003_dnipro_factory",
            "name": "Dnipro Manufacturing",
            "location": {"lat": 48.46, "lon": 35.04},
            "battery_type": "LFP_280Ah",
            "battery_capacity_kwh": 500.0,
            "solar_capacity_kw": 300.0,
            "peak_load_kw": 400.0,
            "base_load_kw": 150.0,
            "load_profile": "industrial",
            "tenant_id": "client_003_dnipro_factory",
            "tenant_namespace": "tenant/client_003_dnipro_factory",
            "storage_namespace": "tenants/client_003_dnipro_factory",
        },
    ]


__all__ = [
    "_get_default_client_configs",
    "_load_client_configurations",
    "_normalize_client_config",
]
"""Helpers for loading optimization client profiles from customers.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def _coerce_float(value: Any) -> Optional[float]:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric


def _first_positive_number(*values: Any) -> Optional[float]:
    for value in values:
        numeric = _coerce_float(value)
        if numeric is not None and numeric > 0:
            return numeric
    return None


def _load_client_profiles() -> Dict[str, Dict[str, Any]]:
    config_path = Path("customers.yaml")
    if not config_path.exists():
        return {}

    try:
        config_data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

    profiles: Dict[str, Dict[str, Any]] = {}
    for entry in config_data.get("customers", []):
        client_id = entry.get("id")
        if not client_id:
            continue

        energy_system = entry.get("energy_system") or {}
        profiles[str(client_id)] = {
            "battery_capacity_kwh": _coerce_float(
                entry.get("battery_capacity_kwh", energy_system.get("battery_capacity_kwh"))
            ),
            "battery_type": entry.get("battery_type") or energy_system.get("battery_type") or "LFP",
            "battery_efficiency": _coerce_float(
                entry.get("battery_efficiency", energy_system.get("battery_efficiency"))
            ),
            "battery_dod_max": _coerce_float(
                entry.get("battery_dod_max", energy_system.get("battery_dod_max"))
            ),
            "battery_soc_min": entry.get("battery_soc_min", energy_system.get("battery_soc_min")),
            "market_regime_override": (
                entry.get("market_regime_override")
                or energy_system.get("market_regime_override")
                or "auto"
            ),
            "site_power_kw": _first_positive_number(
                entry.get("system_power_kw"),
                energy_system.get("system_power_kw"),
                entry.get("site_power_kw"),
                energy_system.get("site_power_kw"),
                entry.get("connected_power_kw"),
                energy_system.get("connected_power_kw"),
                entry.get("contracted_power_kw"),
                energy_system.get("contracted_power_kw"),
                entry.get("solar_capacity_kw"),
                energy_system.get("solar_capacity_kw"),
                entry.get("pv_capacity_kw"),
                energy_system.get("pv_capacity_kw"),
                entry.get("renewable_capacity_kw"),
                energy_system.get("renewable_capacity_kw"),
                entry.get("load_peak_kw"),
                energy_system.get("load_peak_kw"),
                entry.get("peak_load_kw"),
                energy_system.get("peak_load_kw"),
            ),
        }

    return profiles


def _load_client_capacities() -> Dict[str, float]:
    capacities: Dict[str, float] = {}
    for client_id, profile in _load_client_profiles().items():
        battery_kwh = _coerce_float(profile.get("battery_capacity_kwh"))
        if battery_kwh is not None:
            capacities[str(client_id)] = float(battery_kwh)
    return capacities


def _normalize_market_regime_override(value: Any) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_")
    if normalized in {"net_billing", "market_premium"}:
        return normalized
    return "auto"


__all__ = [
    "_coerce_float",
    "_first_positive_number",
    "_load_client_capacities",
    "_load_client_profiles",
    "_normalize_market_regime_override",
]
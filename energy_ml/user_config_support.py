from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional


BATTERY_TEMPLATE_CAPACITY_KWH = {
    "LFP": 10.0,
    "Lead-Acid": 5.0,
    "VRFB": 20.0,
}


BATTERY_SPECIFICATIONS = {
    "LFP": {
        "name": "Lithium Iron Phosphate (LFP)",
        "efficiency": 0.95,
        "cycles_max": 8000,
        "degradation_per_cycle": 0.0000125,
        "cost_usd_per_kwh": 350,
        "cost_uah_per_kwh": 13000,
        "c_rate_charge": 0.5,
        "c_rate_discharge": 1.0,
        "dod_max": 0.9,
        "temperature_range": (-20, 60),
        "description": "Best for daily cycling, long lifespan, safe chemistry",
        "degradation_cost_uah_per_cycle_per_kwh": 13000 / 8000,
        "arbitrage_suitability": 9,
    },
    "Lead-Acid": {
        "name": "Lead-Acid (Deep Cycle)",
        "efficiency": 0.85,
        "cycles_max": 600,
        "degradation_per_cycle": 0.00017,
        "cost_usd_per_kwh": 150,
        "cost_uah_per_kwh": 5500,
        "c_rate_charge": 0.2,
        "c_rate_discharge": 0.3,
        "dod_max": 0.5,
        "temperature_range": (-10, 45),
        "description": "Lower upfront cost but frequent replacement needed",
        "degradation_cost_uah_per_cycle_per_kwh": 5500 / 600,
        "arbitrage_suitability": 4,
    },
    "VRFB": {
        "name": "Vanadium Redox Flow Battery",
        "efficiency": 0.75,
        "cycles_max": 20000,
        "degradation_per_cycle": 0.000005,
        "cost_usd_per_kwh": 600,
        "cost_uah_per_kwh": 22000,
        "c_rate_charge": 0.25,
        "c_rate_discharge": 0.25,
        "dod_max": 1.0,
        "temperature_range": (5, 45),
        "description": "Best for long-duration storage, minimal degradation",
        "degradation_cost_uah_per_cycle_per_kwh": 22000 / 20000,
        "arbitrage_suitability": 7,
    },
}


LOAD_PROFILE_TEMPLATES = {
    "standard": {
        "name": "Standard Business Hours (9-18)",
        "description": "Office or retail operation, active 9 AM - 6 PM",
        "peak_kw": 10.0,
        "base_kw": 2.0,
        "hourly_coefficients": [
            0.2, 0.2, 0.2, 0.2, 0.2, 0.3,
            0.4, 0.6, 0.8,
            1.0, 1.0, 0.9, 0.8, 0.9, 1.0, 1.0, 0.9, 0.8,
            0.6, 0.5, 0.4, 0.3, 0.3, 0.2,
        ],
        "weekend_factor": 0.3,
        "seasonal_variation": 0.15,
    },
    "multi-shift": {
        "name": "Multi-Shift Manufacturing (2-Shift)",
        "description": "Manufacturing: 6 AM-2 PM + 10 PM-6 AM",
        "peak_kw": 15.0,
        "base_kw": 3.0,
        "hourly_coefficients": [
            0.8, 0.8, 0.7, 0.6, 0.5, 0.4,
            1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
            0.3, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.3,
            0.9, 0.9,
        ],
        "weekend_factor": 0.7,
        "seasonal_variation": 0.25,
    },
    "24_7": {
        "name": "24/7 Continuous Operations",
        "description": "Continuous process with minimal variation",
        "peak_kw": 20.0,
        "base_kw": 18.0,
        "hourly_coefficients": [
            0.9, 0.9, 0.9, 0.9, 0.9, 0.95,
            1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 0.95, 0.95, 0.9, 0.9,
        ],
        "weekend_factor": 0.95,
        "seasonal_variation": 0.1,
    },
    "custom": {
        "name": "Custom Hourly Profile",
        "description": "Define your own 24-hour load pattern",
        "peak_kw": 10.0,
        "base_kw": 2.0,
        "hourly_coefficients": [0.5] * 24,
        "weekend_factor": 0.6,
        "seasonal_variation": 0.2,
    },
}


def get_battery_specifications(battery_type: str, capacity_kwh: Optional[float] = None) -> Dict[str, Any]:
    spec = BATTERY_SPECIFICATIONS.get(battery_type)
    if spec is None:
        return {}

    materialized_spec = spec.copy()
    normalized_capacity = 1.0 if capacity_kwh is None else max(capacity_kwh, 0.0)
    materialized_spec["degradation_cost_uah_per_cycle"] = (
        materialized_spec["degradation_cost_uah_per_cycle_per_kwh"] * normalized_capacity
    )
    return materialized_spec


def get_load_profile_templates() -> Dict[str, Dict[str, Any]]:
    return deepcopy(LOAD_PROFILE_TEMPLATES)


def build_battery_templates() -> Dict[str, Dict[str, Any]]:
    templates = {}
    for battery_type, capacity_kwh in BATTERY_TEMPLATE_CAPACITY_KWH.items():
        specs = get_battery_specifications(battery_type)
        if not specs:
            continue
        templates[battery_type] = {
            "name": specs["name"],
            "capacity_kwh": capacity_kwh,
            "efficiency": specs["efficiency"],
            "description": specs["description"],
        }
    return templates


def build_profile_templates() -> Dict[str, Dict[str, Any]]:
    templates = get_load_profile_templates()
    return {
        profile_type: {
            "name": template["name"],
            "peak_load_kw": template["peak_kw"],
            "description": template["description"],
        }
        for profile_type, template in templates.items()
    }
"""Preset helpers for energy ML configuration models."""

from __future__ import annotations


DEGRADATION_COST_DEFAULTS = {
    "LFP": 1.35,
    "Lead-Acid": 4.59,
    "VRFB": 0.1,
}

BATTERY_CYCLE_DEFAULTS = {
    "LFP": 8000,
    "Lead-Acid": 600,
    "VRFB": 20000,
}


def resolve_degradation_cost_default(battery_type: str | None) -> float:
    return DEGRADATION_COST_DEFAULTS.get(battery_type, 1.0)


def resolve_cycles_to_eol_default(battery_type: str | None) -> int:
    return BATTERY_CYCLE_DEFAULTS.get(battery_type, 5000)


def build_standard_work_profile_payload(peak_load_kw: float) -> dict:
    coefficients = {hour: 0.1 for hour in range(24)}
    for hour in range(9, 19):
        coefficients[hour] = 1.0

    return {
        "profile_type": "standard",
        "name": "Standard Work Hours (9-18)",
        "description": "Office hours with peak load 9 AM - 6 PM",
        "hourly_coefficients": coefficients,
        "peak_load_kw": peak_load_kw,
    }


def build_two_shift_profile_payload(peak_load_kw: float) -> dict:
    coefficients = {hour: 0.2 for hour in range(24)}
    for hour in range(6, 15):
        coefficients[hour] = 1.0
    for hour in list(range(22, 24)) + list(range(0, 7)):
        coefficients[hour] = 1.0

    return {
        "profile_type": "multi-shift",
        "name": "Two Shift Operation",
        "description": "6AM-2PM and 10PM-6AM shifts",
        "hourly_coefficients": coefficients,
        "peak_load_kw": peak_load_kw,
    }


def build_continuous_profile_payload(peak_load_kw: float) -> dict:
    coefficients = {hour: 0.8 for hour in range(24)}
    coefficients[2] = 0.6
    coefficients[14] = 0.6

    return {
        "profile_type": "24_7",
        "name": "Continuous Operation (24/7)",
        "description": "Round-the-clock operation with minor variations",
        "hourly_coefficients": coefficients,
        "peak_load_kw": peak_load_kw,
    }


PROFILE_TEMPLATES = {
    "small_office": {
        "profile_name": "Small Office",
        "battery": {
            "type": "LFP",
            "capacity_kwh": 20.0,
            "max_charge_rate_kw": 5.0,
            "max_discharge_rate_kw": 5.0,
        },
        "generation": {
            "solar_capacity_kw": 10.0,
            "wind_capacity_kw": 0.0,
        },
    },
    "retail_store": {
        "profile_name": "Retail Store",
        "battery": {
            "type": "LFP",
            "capacity_kwh": 50.0,
            "max_charge_rate_kw": 15.0,
            "max_discharge_rate_kw": 15.0,
        },
        "generation": {
            "solar_capacity_kw": 25.0,
            "wind_capacity_kw": 0.0,
        },
    },
    "manufacturing": {
        "profile_name": "Manufacturing Plant",
        "battery": {
            "type": "LFP",
            "capacity_kwh": 200.0,
            "max_charge_rate_kw": 50.0,
            "max_discharge_rate_kw": 50.0,
        },
        "generation": {
            "solar_capacity_kw": 100.0,
            "wind_capacity_kw": 50.0,
        },
    },
}
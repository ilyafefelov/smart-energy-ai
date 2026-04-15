from __future__ import annotations

from typing import Callable, Dict, Sequence


def build_actual_payload(
    load_battery_runtime: Callable[[], tuple],
    rng,
    default_capacity_kwh: float,
    default_max_power_kw: float,
) -> Dict:
    lfp_model, lead_acid_model, vrfb_model, _controller_class = load_battery_runtime()
    model_classes = {
        "LFP": lfp_model,
        "LeadAcid": lead_acid_model,
        "VRFB": vrfb_model,
    }
    current_type = rng.choice(list(model_classes))
    model = model_classes[current_type](
        capacity_kwh=default_capacity_kwh,
        max_power_kw=default_max_power_kw,
    )

    power = rng.uniform(-3.0, 3.0)
    degradation = model.calculate_degradation(power, 1.0)
    efficiency = model.get_efficiency(power, model.state.soc)
    max_charge = model.get_max_power(model.state.soc, "charge")
    max_discharge = model.get_max_power(model.state.soc, "discharge")

    return {
        "success": True,
        "battery_type": current_type,
        "capacity_kwh": model.capacity_kwh,
        "max_power_kw": model.max_power_kw,
        "state": {
            "soc": model.state.soc,
            "soh": model.state.soh,
            "temperature_c": model.state.temperature_c,
            "cycles_completed": model.state.cycles_completed,
            "current_power_kw": power,
            "voltage": model.state.voltage,
            "internal_resistance": model.state.internal_resistance,
        },
        "current_efficiency": efficiency,
        "max_charge_power": max_charge,
        "max_discharge_power": max_discharge,
        "recent_degradation": degradation,
        "source": "actual_physics_model",
    }


def _mock_power_limits(battery_name, soc):
    if battery_name == "LeadAcid":
        return 5.0 * (1.0 if soc < 0.8 else 0.5), 5.0 * (soc if soc > 0.3 else 0.2)
    return 5.0 * (1.0 if soc < 0.9 else 0.3), 5.0 * (soc if soc > 0.1 else 0.1)


def _mock_efficiency_and_resistance(battery_name, base_efficiency, soc, soh, power):
    if battery_name == "LeadAcid":
        return base_efficiency * (0.7 if soc < 0.5 else 1.0), 0.05 + (1 - soh) * 0.1
    if battery_name == "VRFB":
        return base_efficiency - (0.02 if abs(power) < 1 else 0), 0.01
    return base_efficiency * (0.9 if soc > 0.9 else 1.0), 0.02 + (1 - soh) * 0.03


def build_mock_payload(
    rng,
    mock_battery_types: Sequence[Dict[str, float | str]],
    timestamp: Callable[[], str],
    default_capacity_kwh: float,
    default_max_power_kw: float,
) -> Dict:
    current_battery = rng.choices(
        mock_battery_types,
        weights=[battery["weight"] for battery in mock_battery_types],
    )[0]
    soc = 0.3 + rng.random() * 0.6
    soh = 0.85 + rng.random() * 0.14
    cycles = rng.random() * (current_battery["cycles"] * 0.8)
    temperature = 15 + rng.random() * 20
    power = rng.uniform(-4.0, 4.0)
    voltage_base = 48 if current_battery["name"] == "LeadAcid" else 52
    voltage = voltage_base + (soc - 0.5) * 4
    efficiency, internal_resistance = _mock_efficiency_and_resistance(
        current_battery["name"],
        current_battery["efficiency"],
        soc,
        soh,
        power,
    )
    max_charge, max_discharge = _mock_power_limits(current_battery["name"], soc)

    return {
        "success": True,
        "battery_type": current_battery["name"],
        "capacity_kwh": default_capacity_kwh,
        "max_power_kw": default_max_power_kw,
        "state": {
            "soc": round(soc, 3),
            "soh": round(soh, 3),
            "temperature_c": round(temperature, 1),
            "cycles_completed": round(cycles, 1),
            "current_power_kw": round(power, 2),
            "voltage": round(voltage, 2),
            "internal_resistance": round(internal_resistance, 4),
        },
        "current_efficiency": round(efficiency, 3),
        "max_charge_power": round(max_charge, 1),
        "max_discharge_power": round(max_discharge, 1),
        "degradation_model": {
            "nominal_cycles": current_battery["cycles"],
            "degradation_per_cycle": 100.0 / current_battery["cycles"],
            "optimal_soc_range": [0.2, 0.8]
            if current_battery["name"] != "LeadAcid"
            else [0.5, 0.8],
            "temperature_coefficient": 0.005,
        },
        "performance_metrics": {
            "round_trip_efficiency": round(efficiency * 0.98, 3),
            "power_fade_factor": round(soh, 3),
            "capacity_fade_factor": round(soh * 0.95, 3),
            "internal_resistance_growth": round(internal_resistance / 0.02, 3),
        },
        "source": "realistic_mock_simulation",
        "timestamp": timestamp(),
    }


def build_error_payload(
    error: Exception,
    timestamp: Callable[[], str],
    default_capacity_kwh: float,
    default_max_power_kw: float,
) -> Dict:
    return {
        "success": False,
        "error": str(error),
        "battery_type": "LFP",
        "capacity_kwh": default_capacity_kwh,
        "max_power_kw": default_max_power_kw,
        "state": {
            "soc": 0.5,
            "soh": 1.0,
            "temperature_c": 25.0,
            "cycles_completed": 0.0,
            "current_power_kw": 0.0,
            "voltage": 52.0,
            "internal_resistance": 0.02,
        },
        "current_efficiency": 0.95,
        "source": "error_fallback",
        "timestamp": timestamp(),
    }
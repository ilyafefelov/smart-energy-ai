"""Dagster assets for tariff optimization (Phase 4D).

Produces tariff cost calculations integrating load profiles and battery models.
"""
import importlib.util
from dagster import asset
import json
from pathlib import Path
import sys
from energy_ml.config_models import UserProfile


def _load_load_simulation_module():
    module_name = "smart_energy_ai_tariff_load_simulation"
    module_path = Path(__file__).resolve().parents[1] / "load_simulation.py"
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    if module_spec is None or module_spec.loader is None:
        raise ImportError(f"Unable to load load simulation helpers from {module_path}")

    module = sys.modules.get(module_name)
    if module is None:
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[module_name] = module
        module_spec.loader.exec_module(module)
    return module


def _load_tariff_models_module():
    module_name = "smart_energy_ai_tariff_models"
    module_path = Path(__file__).resolve().parents[1] / "tariff_models.py"
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    if module_spec is None or module_spec.loader is None:
        raise ImportError(f"Unable to load tariff models from {module_path}")

    module = sys.modules.get(module_name)
    if module is None:
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[module_name] = module
        module_spec.loader.exec_module(module)
    return module


try:
    from energy_ml.load_simulation import generate_yearly_load
except ImportError:
    generate_yearly_load = _load_load_simulation_module().generate_yearly_load


try:
    from energy_ml.tariff_models import UkraineTariffModel as _UkraineTariffModel
except ImportError:
    _UkraineTariffModel = None

if _UkraineTariffModel is None or not hasattr(_UkraineTariffModel, "calculate_365day_cost") or not hasattr(_UkraineTariffModel, "estimate_savings_with_battery"):
    UkraineTariffModel = _load_tariff_models_module().UkraineTariffModel
else:
    UkraineTariffModel = _UkraineTariffModel


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@asset
def tariff_optimization_analysis(user_profile: UserProfile) -> dict:
    """Analyze annual tariff costs and battery optimization potential.
    
    Uses NKREKU 2026 Group A tariff rates with load profile from UserProfile.
    Estimates savings potential from battery optimization.
    
    Returns dict with cost breakdown and savings analysis.
    """
    # Get load profile - for now use synthetic if not available
    # In full integration, load_profiles asset would provide this
    load_result = generate_yearly_load(user_profile.load_profile)
    hourly_loads_8760 = load_result['hourly']
    
    # Initialize tariff model
    tariff = UkraineTariffModel()
    
    # Calculate current costs (grid only)
    cost_result = tariff.calculate_365day_cost(hourly_loads_8760)
    
    # Calculate battery optimization potential
    battery_cfg = user_profile.battery
    charge_efficiency = getattr(battery_cfg, 'charge_efficiency', battery_cfg.efficiency)
    discharge_efficiency = getattr(battery_cfg, 'discharge_efficiency', battery_cfg.efficiency)
    savings_result = tariff.estimate_savings_with_battery(
        hourly_loads_8760,
        battery_capacity_kwh=battery_cfg.capacity_kwh,
        charge_efficiency=charge_efficiency,
        discharge_efficiency=discharge_efficiency,
    )
    
    # Compile output
    output = {
        'tariff_model': 'NKREKU 2026 Group A',
        'year': 2026,
        'on_peak_rate_uah_per_mwh': tariff.on_peak_rate,
        'off_peak_rate_uah_per_mwh': tariff.off_peak_rate,
        'annual_costs': {
            'total_cost_uah': cost_result.total_cost_uah,
            'on_peak_cost_uah': cost_result.on_peak_cost,
            'off_peak_cost_uah': cost_result.off_peak_cost,
            'on_peak_hours': cost_result.on_peak_hours,
            'off_peak_hours': cost_result.off_peak_hours,
        },
        'battery_optimization': {
            'original_cost_uah': savings_result['original_cost_uah'],
            'optimized_cost_uah': savings_result['optimized_cost_uah'],
            'savings_uah': savings_result['savings_uah'],
            'savings_percent': savings_result['savings_percent'],
            'battery_capacity_kwh': battery_cfg.capacity_kwh,
            'on_peak_discharge_kwh': savings_result['on_peak_discharge_kwh'],
            'off_peak_charge_kwh': savings_result['off_peak_charge_kwh'],
        },
        'daily_costs_sample': cost_result.daily_costs[:7],  # First week
    }
    
    # Write to JSON
    path = OUTPUT_DIR / "tariff_analysis_2026.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    
    return output

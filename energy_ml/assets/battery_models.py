"""Dagster assets for battery degradation modeling (Phase 4B).

Produces degradation_costs.json per battery type and integrates with UserProfile.
"""
import importlib.util
from dagster import asset
import json
import sys
from energy_ml.config_models import UserProfile, BatteryConfig
from pathlib import Path


def _load_battery_degradation_module():
    module_name = "smart_energy_ai_battery_degradation"
    module_path = Path(__file__).resolve().parents[1] / "battery_degradation.py"
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    if module_spec is None or module_spec.loader is None:
        raise ImportError(f"Unable to load battery degradation models from {module_path}")

    module = sys.modules.get(module_name)
    if module is None:
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[module_name] = module
        module_spec.loader.exec_module(module)
    return module


try:
    from energy_ml.battery_degradation import LFPModel, LeadAcidModel, VRFBModel
except ImportError:
    _BATTERY_DEGRADATION = _load_battery_degradation_module()
    LFPModel = _BATTERY_DEGRADATION.LFPModel
    LeadAcidModel = _BATTERY_DEGRADATION.LeadAcidModel
    VRFBModel = _BATTERY_DEGRADATION.VRFBModel

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

@asset
def battery_degradation_costs(user_profile: UserProfile):
    """Compute degradation costs for the user's battery and write JSON output."""
    battery_cfg: BatteryConfig = user_profile.battery
    # choose model
    if battery_cfg.type == 'LFP':
        model = LFPModel(battery_cfg)
    elif battery_cfg.type == 'Lead-Acid':
        model = LeadAcidModel(battery_cfg)
    else:
        model = VRFBModel(battery_cfg)

    # run a 1-year (365 cycle approx) projection and 50-year projection
    one_year = model.simulate_cycles(cycles=365, dod=0.8, c_rate=0.5)
    fifty_year = model.simulate_cycles(cycles=365*50, dod=0.8, c_rate=0.5)

    out = {
        'battery_type': battery_cfg.type,
        'capacity_kwh': battery_cfg.capacity_kwh,
        'one_year': {
            'cycles': one_year.cycles,
            'soh': one_year.soh,
            'degradation_cost_usd': one_year.degradation_cost
        },
        'fifty_year': {
            'cycles': fifty_year.cycles,
            'soh': fifty_year.soh,
            'degradation_cost_usd': fifty_year.degradation_cost
        }
    }

    path = OUTPUT_DIR / f"degradation_costs_{battery_cfg.type}.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)

    return out

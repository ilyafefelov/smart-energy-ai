"""Dagster assets for battery degradation modeling (Phase 4B).

Produces degradation_costs.json per battery type and integrates with UserProfile.
"""
from dagster import asset
import json
from energy_ml.config_models import UserProfile, BatteryConfig
from energy_ml.battery_degradation import LFPModel, LeadAcidModel, VRFBModel
from pathlib import Path

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

"""Dagster asset for generating load profiles (Phase 4C).

Provides simulate_load_profile asset which accepts a UserProfile and
produces a JSON file with hourly series and statistics.
"""
import importlib.util
from dagster import asset, AssetIn
import os
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

from energy_ml.config_models import UserProfile


def _load_load_simulation_module():
    module_name = "smart_energy_ai_load_simulation"
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


try:
    from energy_ml.load_simulation import generate_yearly_load, simple_generation_hourly, estimate_self_consumption
except ImportError:
    _LOAD_SIMULATION = _load_load_simulation_module()
    generate_yearly_load = _LOAD_SIMULATION.generate_yearly_load
    simple_generation_hourly = _LOAD_SIMULATION.simple_generation_hourly
    estimate_self_consumption = _LOAD_SIMULATION.estimate_self_consumption


@asset(ins={'user_profile': AssetIn()})
def simulate_load_profile(user_profile: UserProfile):
    """Simulate load profile for the given user profile and write JSON output.

    Output file: load_profile_{profile_type}.json in ./artifacts
    """
    profile = user_profile.load_profile
    sim = generate_yearly_load(profile)

    # create simple generation series
    gen_hours = simple_generation_hourly(user_profile)

    sc = estimate_self_consumption(sim['hourly'], gen_hours)

    result = {
        'metadata': {
            'profile_name': profile.name,
            'profile_type': profile.profile_type,
            'generated_at': datetime.now(timezone.utc).isoformat()
        },
        'simulation': sim,
        'generation': {
            'annual_energy_kwh': round(sum(gen_hours), 3)
        },
        'self_consumption': sc
    }

    # ensure artifacts dir
    outdir = os.path.join(os.getcwd(), 'artifacts')
    os.makedirs(outdir, exist_ok=True)
    # Replace special characters in filename (e.g., "/" in "24/7")
    safe_profile_type = profile.profile_type.replace('/', '_')
    fname = f"load_profile_{safe_profile_type}.json"
    path = os.path.join(outdir, fname)
    with open(path, 'w', encoding='utf8') as f:
        json.dump(result, f, indent=2)

    return path

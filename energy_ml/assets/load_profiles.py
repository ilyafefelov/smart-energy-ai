"""Dagster asset for generating load profiles (Phase 4C).

Provides simulate_load_profile asset which accepts a UserProfile and
produces a JSON file with hourly series and statistics.
"""
from dagster import asset, AssetIn
import os
import json
from datetime import datetime

from energy_ml.load_simulation import generate_yearly_load, simple_generation_hourly, estimate_self_consumption
from energy_ml.config_models import UserProfile


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
            'generated_at': datetime.utcnow().isoformat() + 'Z'
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

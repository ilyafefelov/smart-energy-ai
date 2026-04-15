from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def make_operation_profile(module):
    return module.OperationProfile(
        daily_cycles=1.2,
        seasonal_variation=0.3,
        capacity_factor=0.8,
        grid_services_revenue=0.0,
        energy_arbitrage_spread=45.0,
    )


def test_lcos_and_arbitrage_outputs_are_positive_and_structured() -> None:
    module = load_module("economics_under_test", "src/physics/economics.py")
    model = module.EconomicModel(module.BatteryTechnology.LFP, 280.0)
    profile = make_operation_profile(module)

    lcos = model.calculate_lcos(profile)
    arbitrage = model.calculate_arbitrage_value([30.0, 45.0, 60.0], profile)

    assert lcos["lcos_usd_per_kwh"] > 0
    assert lcos["lcos_usd_per_mwh"] == lcos["lcos_usd_per_kwh"] * 1000
    assert lcos["capex_component"] == 280.0 * model.params.capex_per_kwh
    assert lcos["total_costs"] >= lcos["capex_component"]
    assert lcos["effective_lifetime_years"] <= model.params.system_lifetime_years

    assert arbitrage["avg_price_spread"] == 45.0
    assert arbitrage["annual_arbitrage_mwh"] > 0
    assert arbitrage["annual_net_value"] <= arbitrage["annual_gross_value"]
    assert arbitrage["pv_arbitrage_value"] > arbitrage["annual_net_value"]


def test_calculate_npv_irr_returns_positive_npv_and_irr_for_profitable_cash_flows() -> None:
    module = load_module("economics_npv_under_test", "src/physics/economics.py")
    model = module.EconomicModel(module.BatteryTechnology.LFP, 280.0)

    npv, irr = model.calculate_npv_irr([-1000.0, 700.0, 700.0])

    assert npv > 0
    assert irr is not None
    assert irr > 0


def test_compare_technologies_and_sensitivity_analysis_cover_all_technologies() -> None:
    module = load_module("economics_compare_under_test", "src/physics/economics.py")
    model = module.EconomicModel(module.BatteryTechnology.LFP, 280.0)
    profile = make_operation_profile(module)
    original_capex = model.params.capex_per_kwh

    comparison = model.compare_technologies(profile, [30.0, 45.0, 60.0])
    sensitivity = model.sensitivity_analysis(
        profile,
        parameter_ranges={
            "daily_cycles": (0.8, 1.6),
            "capex_per_kwh": (100.0, 200.0),
        },
        num_points=3,
    )

    assert set(comparison.keys()) == {tech.value for tech in module.BatteryTechnology}
    assert all(result["payback_years"] > 0 for result in comparison.values())

    assert sensitivity["daily_cycles"]["parameter_values"] == [0.8, 1.2000000000000002, 1.6]
    assert len(sensitivity["capex_per_kwh"]["lcos_values"]) == 3
    assert model.params.capex_per_kwh == original_capex
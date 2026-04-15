from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_get_stress_factor_is_baselined_at_nominal_conditions() -> None:
    module = load_module("battery_lfp_under_test", "src/physics/battery_lfp.py")
    model = module.DegradationModel(module.BatterySpecs())

    nominal = module.OperatingConditions(soc=0.5, temperature=25.0, cycle_depth=0.8, c_rate=0.5)
    cool_low_rate = module.OperatingConditions(soc=0.4, temperature=10.0, cycle_depth=0.5, c_rate=0.1)

    assert model.get_stress_factor(nominal) == 1.0
    assert model.get_stress_factor(cool_low_rate) == 1.0


def test_marginal_cost_increases_for_hot_high_soc_operation() -> None:
    module = load_module("battery_lfp_cost_under_test", "src/physics/battery_lfp.py")
    model = module.DegradationModel(module.BatterySpecs())

    nominal = module.OperatingConditions(soc=0.5, temperature=25.0, cycle_depth=0.5, c_rate=0.5)
    stressed = module.OperatingConditions(soc=0.95, temperature=45.0, cycle_depth=0.9, c_rate=1.0)

    assert model.calculate_marginal_cost(stressed) > model.calculate_marginal_cost(nominal)


def test_predict_knee_point_and_cost_matrix_cover_core_outputs() -> None:
    module = load_module("battery_lfp_matrix_under_test", "src/physics/battery_lfp.py")
    model = module.DegradationModel(module.BatterySpecs())

    assert model.predict_knee_point(current_soh=0.8, avg_temperature=30.0, cycles_per_day=1.0) == (0, 0.8)

    days_to_knee, final_soh = model.predict_knee_point(current_soh=0.95, avg_temperature=35.0, cycles_per_day=1.5)
    assert days_to_knee > 0
    assert 0.6 <= final_soh < 0.95

    cost_matrix = model.calculate_cycle_cost_matrix(
        soc_points=np.array([0.5, 0.95]),
        temp_points=np.array([25.0, 45.0]),
    )

    assert cost_matrix.shape == (2, 2)
    assert cost_matrix[0, 0] < cost_matrix[1, 1]

    operating_window = model.get_optimal_operating_window()
    assert operating_window["soc_range"] == (0.2, 0.9)
    assert operating_window["temperature_range"] == (15.0, 35.0)
    assert operating_window["c_rate_range"] == (0.1, 0.8)
    assert operating_window["max_dod"] == 0.8
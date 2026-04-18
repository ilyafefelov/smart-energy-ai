from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(module_name: str, relative_path: str, injected_modules: dict[str, object]):
    module_path = REPO_ROOT / relative_path
    previous = {}

    for name, module in injected_modules.items():
        previous[name] = sys.modules.get(name)
        sys.modules[name] = module

    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        for name, old in previous.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old


class FakeEnv:
    pass


class FakeBox:
    def __init__(self, low, high, dtype=None):
        self.low = low
        self.high = high
        self.dtype = dtype

    def sample(self):
        return np.zeros(len(self.low), dtype=np.float32)


class FakeConfig:
    def get_battery_config(self):
        return {
            "capacity_kwh": 100.0,
            "min_soc": 0.1,
            "max_soc": 0.95,
            "charge_efficiency": 0.95,
            "discharge_efficiency": 0.95,
        }

    def get_grid_config(self):
        return {"max_import_power_kw": 100.0}


def load_rl_environment_module():
    gym_mod = types.ModuleType("gymnasium")
    gym_mod.Env = FakeEnv
    gym_mod.spaces = types.SimpleNamespace(Box=FakeBox)
    return load_module(
        "rl_environment_under_test",
        "src/rl_environment.py",
        injected_modules={"gymnasium": gym_mod},
    )


def make_env(module):
    weather = pd.DataFrame(
        {
            "temp": np.linspace(10.0, 12.3, 24),
            "radiation": np.linspace(0.0, 230.0, 24),
            "clouds": np.linspace(20.0, 80.0, 24),
        }
    )
    prices = pd.DataFrame(
        {
            "price_normalized_minmax": np.linspace(0.1, 0.9, 24),
            "price_uah_original": np.linspace(100.0, 240.0, 24),
        }
    )
    return module.SmartEnergyEnv(weather, prices, config=FakeConfig())


def test_reset_and_step_return_expected_state_and_done_flag() -> None:
    module = load_rl_environment_module()
    env = make_env(module)

    state = env.reset()
    assert state.shape == (5,)
    assert np.allclose(state, np.array([10.0, 0.0, 20.0, 0.1, 0.5], dtype=np.float32))

    action = np.array([0.2, 0.0, 0.5, 0.0], dtype=np.float32)
    next_state, reward, done, info = env.step(action)

    assert next_state.shape == (5,)
    assert isinstance(reward, float)
    assert done is False
    assert info["hour"] == 0
    assert info["battery_soc"] > 50.0
    assert info["hourly_cost"] == 50.0 * 100.0

    for _ in range(23):
        _, _, done, _ = env.step(np.zeros(4, dtype=np.float32))

    assert done is True


def test_render_uses_latest_step_info_without_key_errors(capsys) -> None:
    module = load_rl_environment_module()
    env = make_env(module)
    env.reset()
    env.step(np.array([0.0, 0.0, 0.5, 0.0], dtype=np.float32))

    env.render()

    captured = capsys.readouterr()
    assert "Hour  0:" in captured.out
    assert "Cost=" in captured.out
    assert "Price=" in captured.out
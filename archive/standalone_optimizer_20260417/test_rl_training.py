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


class FakeActionSpace:
    def sample(self):
        return np.zeros(4, dtype=np.float32)


class FakeEnv:
    def __init__(self, weather_df, prices_df):
        self.weather_df = weather_df
        self.prices_df = prices_df
        self.action_space = FakeActionSpace()
        self.reset_calls = 0
        self.step_calls = 0

    def reset(self):
        self.reset_calls += 1
        self.step_calls = 0
        return np.zeros(5, dtype=np.float32)

    def step(self, action):
        self.step_calls += 1
        reward = 1.5
        done = self.step_calls >= 24
        info = {"episode_cost": 1234.0 + self.reset_calls, "hour": self.step_calls - 1}
        return np.zeros(5, dtype=np.float32), reward, done, info


def load_rl_training_module():
    src_pkg = types.ModuleType("src")
    src_pkg.__path__ = [str(REPO_ROOT / "src")]
    rl_env_mod = types.ModuleType("src.rl_environment")
    rl_env_mod.SmartEnergyEnv = FakeEnv
    return load_module(
        "rl_training_under_test",
        "src/rl_training.py",
        injected_modules={
            "src": src_pkg,
            "src.rl_environment": rl_env_mod,
        },
    )


def make_trainer(module):
    weather = pd.DataFrame({"temp": [1.0, 2.0], "radiation": [0.0, 1.0], "clouds": [20.0, 25.0]})
    prices = pd.DataFrame({"price_normalized_minmax": [0.1, 0.2], "price_uah_original": [100.0, 120.0]})
    return module.RLTrainer(weather, prices, model_path="models/test_ppo_agent.zip")


def test_train_ppo_delegates_to_simple_training_when_sb3_unavailable(monkeypatch) -> None:
    module = load_rl_training_module()
    trainer = make_trainer(module)

    monkeypatch.setattr(module, "STABLE_BASELINES_AVAILABLE", False)
    monkeypatch.setattr(trainer, "_train_simple", lambda: {"status": "completed_simple", "episodes": 10})

    result = trainer.train_ppo(timesteps=1234, learning_rate=1e-3)

    assert result == {"status": "completed_simple", "episodes": 10}


def test_train_simple_and_evaluate_model_not_found_cover_fallback_paths(monkeypatch) -> None:
    module = load_rl_training_module()
    trainer = make_trainer(module)

    monkeypatch.setattr(module, "STABLE_BASELINES_AVAILABLE", False)

    train_result = trainer._train_simple()
    eval_result = trainer.evaluate(episodes=2)

    assert train_result["status"] == "completed_simple"
    assert train_result["episodes"] == 10
    assert train_result["baseline_cost"] == 200000
    assert train_result["avg_cost"] > 0
    assert eval_result == {"status": "model_not_found"}
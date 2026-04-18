from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(module_name: str, relative_path: str, injected_modules: dict[str, object] | None = None):
    module_path = REPO_ROOT / relative_path
    injected_modules = injected_modules or {}
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


def test_simulate_training_uses_fallback_baseline_consistently(monkeypatch) -> None:
    src_pkg = types.ModuleType("src")
    src_pkg.__path__ = [str(REPO_ROOT / "src")]
    baseline_mod = types.ModuleType("src.baseline_calculator")

    def calculate_real_baseline(_scenario: str):
        raise RuntimeError("baseline unavailable")

    baseline_mod.calculate_real_baseline = calculate_real_baseline

    module = load_module(
        "training_analyzer_under_test",
        "src/training_analyzer.py",
        injected_modules={
            "src": src_pkg,
            "src.baseline_calculator": baseline_mod,
        },
    )

    monkeypatch.setitem(sys.modules, "src", src_pkg)
    monkeypatch.setitem(sys.modules, "src.baseline_calculator", baseline_mod)
    monkeypatch.setattr(module.np.random, "normal", lambda mean, std: 0.0)

    analyzer = module.TrainingAnalyzer()
    summary = analyzer.simulate_training(num_episodes=5)

    assert summary["total_episodes"] == 5
    assert summary["baseline_cost"] == 3788.0
    assert summary["final_cost"] < summary["baseline_cost"]
    assert summary["best_cost"] <= summary["final_cost"]
    assert summary["cost_reduction_pct"] > 0
    assert len(summary["episodes"]) == 5
    assert len(summary["costs"]) == 5
    assert len(analyzer.to_dataframe()) == 5


def test_generate_training_data_returns_report_dataframe_and_analyzer(monkeypatch) -> None:
    src_pkg = types.ModuleType("src")
    src_pkg.__path__ = [str(REPO_ROOT / "src")]
    baseline_mod = types.ModuleType("src.baseline_calculator")
    baseline_mod.calculate_real_baseline = lambda scenario: {
        "comparison": {
            "baseline_cost_uah": 4000.0,
            "optimized_cost_uah": 2000.0,
        }
    }

    module = load_module(
        "training_analyzer_generate_under_test",
        "src/training_analyzer.py",
        injected_modules={
            "src": src_pkg,
            "src.baseline_calculator": baseline_mod,
        },
    )

    monkeypatch.setitem(sys.modules, "src", src_pkg)
    monkeypatch.setitem(sys.modules, "src.baseline_calculator", baseline_mod)
    monkeypatch.setattr(module.np.random, "normal", lambda mean, std: 0.0)

    payload = module.generate_training_data()

    assert set(payload.keys()) == {"summary", "dataframe", "report", "analyzer"}
    assert payload["summary"]["total_episodes"] == 50
    assert not payload["dataframe"].empty
    assert "RL TRAINING SESSION REPORT" in payload["report"]
    assert payload["analyzer"].training_data
#!/usr/bin/env python3
"""Compatibility wrapper for the canonical root ML integration bridge."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_root_bridge():
    root_path = Path(__file__).resolve().parents[1] / "ml_integration_api.py"
    spec = spec_from_file_location("smart_energy_ai_root_ml_integration_api", root_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load root ML bridge from {root_path}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_ROOT_BRIDGE = _load_root_bridge()

INCUMBENT_SERVING_MODE = _ROOT_BRIDGE.INCUMBENT_SERVING_MODE
LEARNED_POLICY_SERVING_MODE = _ROOT_BRIDGE.LEARNED_POLICY_SERVING_MODE
sys = _ROOT_BRIDGE.sys

setup_logging = _ROOT_BRIDGE.setup_logging
load_user_config = _ROOT_BRIDGE._load_user_config
get_recommendation = _ROOT_BRIDGE.get_recommendation
get_forecast = _ROOT_BRIDGE.get_forecast
get_pipeline_status = _ROOT_BRIDGE.get_pipeline_status
set_optimization_strategy = _ROOT_BRIDGE.set_optimization_strategy
get_optimization_strategy = _ROOT_BRIDGE.get_optimization_strategy
get_battery_physics = _ROOT_BRIDGE.get_battery_physics
get_renewable_forecast = _ROOT_BRIDGE.get_renewable_forecast
main = _ROOT_BRIDGE.main

__all__ = [
    "INCUMBENT_SERVING_MODE",
    "LEARNED_POLICY_SERVING_MODE",
    "get_battery_physics",
    "get_forecast",
    "get_optimization_strategy",
    "get_pipeline_status",
    "get_recommendation",
    "get_renewable_forecast",
    "load_user_config",
    "main",
    "set_optimization_strategy",
    "setup_logging",
    "sys",
]


if __name__ == "__main__":
    main()

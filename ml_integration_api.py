#!/usr/bin/env python3
"""Compatibility wrapper for the canonical scripts ML integration bridge.

Keep all bridge implementation logic in ``scripts/ml_integration_api.py``.
This module exists only to preserve legacy invocations such as
``python ml_integration_api.py`` while callers migrate to the canonical path.
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_canonical_bridge():
    root_path = Path(__file__).resolve().parent / "scripts" / "ml_integration_api.py"
    spec = spec_from_file_location("smart_energy_ai_scripts_ml_integration_api", root_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load canonical ML bridge from {root_path}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_CANONICAL_BRIDGE = _load_canonical_bridge()

INCUMBENT_SERVING_MODE = _CANONICAL_BRIDGE.INCUMBENT_SERVING_MODE
LEARNED_POLICY_SERVING_MODE = _CANONICAL_BRIDGE.LEARNED_POLICY_SERVING_MODE
sys = _CANONICAL_BRIDGE.sys

setup_logging = _CANONICAL_BRIDGE.setup_logging
load_user_config = _CANONICAL_BRIDGE._load_user_config
get_recommendation = _CANONICAL_BRIDGE.get_recommendation
get_forecast = _CANONICAL_BRIDGE.get_forecast
get_pipeline_status = _CANONICAL_BRIDGE.get_pipeline_status
set_optimization_strategy = _CANONICAL_BRIDGE.set_optimization_strategy
get_optimization_strategy = _CANONICAL_BRIDGE.get_optimization_strategy
get_battery_physics = _CANONICAL_BRIDGE.get_battery_physics
get_renewable_forecast = _CANONICAL_BRIDGE.get_renewable_forecast
main = _CANONICAL_BRIDGE.main
_load_user_config = _CANONICAL_BRIDGE._load_user_config
_save_user_config = _CANONICAL_BRIDGE._save_user_config


def __getattr__(name: str):
    return getattr(_CANONICAL_BRIDGE, name)


__all__ = [
    "INCUMBENT_SERVING_MODE",
    "LEARNED_POLICY_SERVING_MODE",
    "_load_user_config",
    "_save_user_config",
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
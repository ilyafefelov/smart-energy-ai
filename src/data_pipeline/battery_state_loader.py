"""Helpers for loading persisted battery state for tenant simulations."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List

import numpy as np


logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
SIMULATOR_STATE_SOURCE = "SIMULATOR_BACKED"
CONFIG_STATE_SOURCE = "CONFIG_FALLBACK"


def _normalize_tenant_id(raw_tenant_id: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", str(raw_tenant_id).strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "unknown_tenant"


def _safe_float(value: Any, default: float) -> float:
    try:
        numeric = float(value)
        return numeric if np.isfinite(numeric) else default
    except (TypeError, ValueError):
        return default


def _candidate_battery_state_paths(tenant_id: str) -> List[Path]:
    normalized_tenant_id = _normalize_tenant_id(tenant_id)
    return [
        REPO_ROOT / "dashboard" / "data" / "tenants" / normalized_tenant_id / "battery_state.json",
        REPO_ROOT / "dashboard" / "data" / "battery_state.json",
        REPO_ROOT / "data" / "tenants" / normalized_tenant_id / "battery_state.json",
        REPO_ROOT / "data" / "battery_state.json",
    ]


def _load_operational_battery_state(config: Dict[str, Any]) -> Dict[str, Any]:
    tenant_id = config.get("tenant_id") or config.get("id") or "unknown_tenant"

    for battery_state_path in _candidate_battery_state_paths(str(tenant_id)):
        if not battery_state_path.exists():
            continue

        try:
            with open(battery_state_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)

            if not isinstance(payload, dict):
                continue

            relative_path = battery_state_path.relative_to(REPO_ROOT).as_posix()
            return {
                "soc": _safe_float(payload.get("soc"), 50.0),
                "temperature": _safe_float(payload.get("temperature"), 25.0),
                "voltage": _safe_float(payload.get("voltage"), 400.0),
                "current": _safe_float(payload.get("current"), 0.0),
                "health": _safe_float(payload.get("health"), 100.0),
                "cycles": _safe_float(payload.get("cycles"), 0.0),
                "last_update": str(payload.get("lastUpdate") or payload.get("last_update") or ""),
                "source": SIMULATOR_STATE_SOURCE,
                "state_source": "simulator_backed_telemetry",
                "state_source_detail": relative_path,
                "telemetry_classification": "simulated_operational_telemetry",
            }
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load simulator-backed battery state from %s: %s", battery_state_path, exc)

    return {
        "soc": 50.0,
        "temperature": 25.0,
        "voltage": 400.0,
        "current": 0.0,
        "health": 100.0,
        "cycles": 0.0,
        "last_update": None,
        "source": CONFIG_STATE_SOURCE,
        "state_source": "config_fallback",
        "state_source_detail": "synthetic_config_defaults",
        "telemetry_classification": "fabricated_training_scaffolding",
    }


__all__ = [
    "CONFIG_STATE_SOURCE",
    "REPO_ROOT",
    "SIMULATOR_STATE_SOURCE",
    "_candidate_battery_state_paths",
    "_load_operational_battery_state",
    "_normalize_tenant_id",
    "_safe_float",
]
"""
Feature Engine Selection Utilities.

Centralized engine selection logic with deterministic precedence:
1) explicit config override,
2) environment override,
3) automatic hardware detection.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from .nvtabular_engine import create_nvtabular_engine, is_nvtabular_available
from .polars_engine import create_polars_engine, is_polars_available


ENGINE_ENV_VAR = "SMART_ENERGY_ENGINE"
STRICT_ENV_VAR = "SMART_ENERGY_ENGINE_STRICT"


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _normalize_mode(value: Optional[str]) -> str:
    mode = (value or "auto").strip().lower()
    if mode in {"gpu", "nvtabular"}:
        return "nvtabular"
    if mode in {"cpu", "polars"}:
        return "polars"
    return "auto"


def select_feature_engine(config: Optional[Dict[str, Any]] = None) -> Tuple[Any, Dict[str, Any]]:
    """
    Select and instantiate the feature engine.

    Returns:
        Tuple(engine_instance, selection_metadata)
    """
    cfg = config or {}
    requested = _normalize_mode(cfg.get("execution_mode") or os.getenv(ENGINE_ENV_VAR))
    strict = _as_bool(cfg.get("strict_engine", False) or os.getenv(STRICT_ENV_VAR))

    polars_available = is_polars_available()
    nvtabular_available = is_nvtabular_available()

    selected_name = ""
    fallback_reason = ""
    engine = None

    if requested == "nvtabular":
        engine = create_nvtabular_engine(cfg)
        if engine is not None:
            selected_name = "nvtabular"
        elif strict:
            raise RuntimeError("NVTabular engine was requested, but GPU dependencies are unavailable")
        else:
            fallback_reason = "nvtabular unavailable; falling back to polars"

    if engine is None and requested == "polars":
        if not polars_available:
            raise RuntimeError("Polars engine was requested, but polars is not installed")
        engine = create_polars_engine(cfg)
        selected_name = "polars"

    if engine is None and requested == "auto":
        if nvtabular_available:
            engine = create_nvtabular_engine(cfg)
            if engine is not None:
                selected_name = "nvtabular"
            else:
                fallback_reason = "gpu detected but NVTabular initialization failed; falling back to polars"

        if engine is None:
            if not polars_available:
                raise RuntimeError("No supported feature engine available (NVTabular and Polars unavailable)")
            engine = create_polars_engine(cfg)
            selected_name = "polars"

    if engine is None:
        # Safety net for invalid input combinations.
        if not polars_available:
            raise RuntimeError("Engine selection failed and polars fallback is unavailable")
        engine = create_polars_engine(cfg)
        selected_name = "polars"
        if not fallback_reason:
            fallback_reason = "invalid or unavailable requested engine; defaulted to polars"

    metadata = {
        "requested_engine": requested,
        "selected_engine": selected_name,
        "polars_available": polars_available,
        "nvtabular_available": nvtabular_available,
        "strict_mode": strict,
        "fallback_reason": fallback_reason,
        "selected_at": datetime.now(timezone.utc).isoformat(),
    }
    return engine, metadata

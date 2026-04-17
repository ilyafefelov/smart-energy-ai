"""Reusable Dagster schedule asset loading and normalization helpers."""

from __future__ import annotations

import glob
import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float and fall back for invalid or NaN inputs."""
    try:
        numeric = float(value)
        if numeric != numeric:
            return default
        return numeric
    except Exception:
        return default


def _optional_float(value: Any) -> Optional[float]:
    """Convert a value to float while preserving missing or NaN as None."""
    try:
        numeric = float(value)
        if numeric != numeric:
            return None
        return numeric
    except Exception:
        return None


def _optional_bool(value: Any) -> Optional[bool]:
    """Convert a value to bool while preserving missing values as None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    return None


def _optional_text(value: Any) -> Optional[str]:
    """Convert a value to text while preserving missing or blank values as None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _find_latest_asset_file(project_root: Path, asset_name: str) -> Optional[Tuple[Path, Path]]:
    """Find the newest Dagster storage root containing the target asset."""
    pattern = str(project_root / ".tmp_dagster_home_*")
    roots = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)

    dagster_home_env = os.getenv("DAGSTER_HOME")
    persistent_roots = []
    if dagster_home_env:
        persistent_roots.append(Path(dagster_home_env))
    persistent_roots.append(project_root / "data" / "dagster_home")

    seen_roots = set()
    candidate_roots = []
    for root in [*map(Path, roots), *persistent_roots]:
        resolved_root = root.resolve()
        if resolved_root in seen_roots:
            continue
        seen_roots.add(resolved_root)
        candidate_roots.append(root)

    for root_path in candidate_roots:
        candidate = root_path / "storage" / asset_name
        if candidate.exists():
            return candidate, root_path

    return None


def _load_pickled_asset(path: Path):
    """Load a Dagster temporary asset payload stored as a pickle file."""
    with path.open("rb") as handle:
        return pickle.load(handle)


def _to_rows(dataframe: Any) -> List[Dict[str, Any]]:
    """Normalize supported payload shapes to a list of row dictionaries."""
    if hasattr(dataframe, "to_dicts"):
        return list(dataframe.to_dicts())

    if isinstance(dataframe, list):
        return [row for row in dataframe if isinstance(row, dict)]

    return []


def _normalize_action(action_kw: float) -> str:
    """Map schedule power direction to the dashboard action contract."""
    if action_kw > 0.05:
        return "SELL"
    if action_kw < -0.05:
        return "BUY"
    return "HOLD"


def _select_client_rows(rows: List[Dict[str, Any]], tenant_id: str) -> Tuple[List[Dict[str, Any]], str]:
    """Select the requested tenant rows or fall back to the first available client."""
    if not rows:
        return [], ""

    if "client_id" not in rows[0]:
        return rows, ""

    available_client_ids: List[str] = []
    seen = set()
    for row in rows:
        client_id = str(row.get("client_id", ""))
        if client_id and client_id not in seen:
            seen.add(client_id)
            available_client_ids.append(client_id)

    if tenant_id in seen:
        selected = tenant_id
    elif available_client_ids:
        selected = available_client_ids[0]
    else:
        selected = ""

    if not selected:
        return rows, ""

    filtered = [row for row in rows if str(row.get("client_id", "")) == selected]
    return filtered, selected


def _normalize_schedule(rows: List[Dict[str, Any]], fx_rate: float) -> List[Dict[str, Any]]:
    """Normalize schedule rows for JSON transport to the dashboard/API layer."""
    normalized: List[Dict[str, Any]] = []

    rows_sorted = sorted(rows, key=lambda row: int(_safe_float(row.get("hour", 0))))
    for row in rows_sorted[:24]:
        hour_offset = int(_safe_float(row.get("hour", 0))) % 24
        action_kw = _safe_float(row.get("action_kw", 0.0))
        action = _normalize_action(action_kw)
        net_cost_eur = _safe_float(row.get("net_cost_eur", 0.0))
        price_eur_mwh = _safe_float(row.get("price_eur_mwh", 0.0))

        normalized.append(
            {
                "hour": hour_offset,
                "hour_offset": hour_offset,
                "action": action,
                "action_kw": round(action_kw, 4),
                "net_cost_eur": round(net_cost_eur, 6),
                "expected_profit_uah": round(max(0.0, -net_cost_eur * fx_rate), 2),
                "price_eur_mwh": round(price_eur_mwh, 6),
                "price_uah_kwh": round((price_eur_mwh * fx_rate) / 1000.0, 3),
                "charge_kwh": _optional_float(row.get("charge_kwh")),
                "discharge_kwh": _optional_float(row.get("discharge_kwh")),
                "soc_before_kwh": _optional_float(row.get("soc_before_kwh")),
                "soc_after_kwh": _optional_float(row.get("soc_after_kwh")),
                "throughput_total_kwh": _optional_float(row.get("throughput_total_kwh")),
                "load_kwh": _optional_float(row.get("load_kwh")),
                "solar_kwh": _optional_float(row.get("solar_kwh")),
                "grid_import_kwh": _optional_float(row.get("grid_import_kwh")),
                "grid_export_kwh": _optional_float(row.get("grid_export_kwh")),
                "purchase_cost_eur": _optional_float(row.get("purchase_cost_eur")),
                "export_revenue_eur": _optional_float(row.get("export_revenue_eur")),
                "degradation_penalty_eur": _optional_float(row.get("degradation_penalty_eur")),
                "forecast_model_name": _optional_text(row.get("forecast_model_name")),
                "forecast_model_family": _optional_text(row.get("forecast_model_family")),
                "forecast_horizon_mode": _optional_text(row.get("forecast_horizon_mode")),
                "forecast_uncertainty_source": _optional_text(row.get("forecast_uncertainty_source")),
                "forecast_promotion_active": _optional_bool(row.get("forecast_promotion_active")),
                "forecast_promotion_source": _optional_text(row.get("forecast_promotion_source")),
                "solver": str(row.get("solver", "")),
            }
        )

    return normalized


def _build_recommendation(schedule: List[Dict[str, Any]], source_asset: str) -> Dict[str, Any]:
    """Build the current-hour recommendation summary from a normalized schedule."""
    current_row = next(
        (row for row in schedule if int(row.get("hour_offset", row.get("hour", -1))) == 0),
        None,
    )

    if current_row is None:
        current_row = schedule[0] if schedule else {"action": "HOLD", "action_kw": 0.0}

    action = str(current_row.get("action", "HOLD"))
    action_kw = _safe_float(current_row.get("action_kw", 0.0))
    solver = str(current_row.get("solver", ""))

    confidence = 0.9 if source_asset == "optimization_schedule_milp_asset" else 0.8
    rationale = (
        f"Dagster asset {source_asset} recommends {action} "
        f"(action_kw={action_kw:.3f}{', solver=' + solver if solver else ''})."
    )

    return {
        "action": action,
        "confidence": confidence,
        "confidence_percent": int(round(confidence * 100)),
        "rationale": rationale,
    }


__all__ = [
    "_build_recommendation",
    "_find_latest_asset_file",
    "_load_pickled_asset",
    "_normalize_action",
    "_normalize_schedule",
    "_optional_bool",
    "_optional_float",
    "_optional_text",
    "_safe_float",
    "_select_client_rows",
    "_to_rows",
]
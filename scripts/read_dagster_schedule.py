#!/usr/bin/env python3
"""Read latest Dagster materialized schedule asset and output normalized JSON."""

from __future__ import annotations

import argparse
import glob
import json
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ASSET_PRIORITY = [
    "optimization_schedule_milp_asset",
    "optimization_schedule_asset",
]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
        if numeric != numeric:  # NaN check
            return default
        return numeric
    except Exception:
        return default


def _find_latest_asset_file(project_root: Path, asset_name: str) -> Optional[Tuple[Path, Path]]:
    pattern = str(project_root / ".tmp_dagster_home_*")
    roots = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)

    for root in roots:
        root_path = Path(root)
        candidate = root_path / "storage" / asset_name
        if candidate.exists():
            return candidate, root_path

    return None


def _load_pickled_asset(path: Path):
    with path.open("rb") as handle:
        return pickle.load(handle)


def _to_rows(dataframe: Any) -> List[Dict[str, Any]]:
    if hasattr(dataframe, "to_dicts"):
        return list(dataframe.to_dicts())

    if isinstance(dataframe, list):
        return [row for row in dataframe if isinstance(row, dict)]

    return []


def _normalize_action(action_kw: float) -> str:
    if action_kw > 0.05:
        return "BUY"
    if action_kw < -0.05:
        return "SELL"
    return "HOLD"


def _select_client_rows(rows: List[Dict[str, Any]], tenant_id: str) -> Tuple[List[Dict[str, Any]], str]:
    if not rows:
        return [], ""

    if "client_id" not in rows[0]:
        return rows, ""

    available_client_ids = []
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
    normalized: List[Dict[str, Any]] = []

    rows_sorted = sorted(rows, key=lambda row: int(_safe_float(row.get("hour", 0))))
    for row in rows_sorted[:24]:
        hour = int(_safe_float(row.get("hour", 0))) % 24
        action_kw = _safe_float(row.get("action_kw", 0.0))
        action = _normalize_action(action_kw)
        net_cost_eur = _safe_float(row.get("net_cost_eur", 0.0))
        price_eur_mwh = _safe_float(row.get("price_eur_mwh", 0.0))

        normalized.append(
            {
                "hour": hour,
                "action": action,
                "action_kw": round(action_kw, 4),
                "net_cost_eur": round(net_cost_eur, 6),
                "expected_profit_uah": round(max(0.0, -net_cost_eur * fx_rate), 2),
                "price_eur_mwh": round(price_eur_mwh, 6),
                "price_uah_kwh": round((price_eur_mwh * fx_rate) / 1000.0, 3),
                "solver": str(row.get("solver", "")),
            }
        )

    return normalized


def _build_recommendation(schedule: List[Dict[str, Any]], source_asset: str) -> Dict[str, Any]:
    current_hour = datetime.now().hour
    current_row = next((row for row in schedule if int(row.get("hour", -1)) == current_hour), None)

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Read latest Dagster schedule materialization")
    parser.add_argument("--tenant-id", required=True, help="Tenant id for client row selection")
    parser.add_argument("--project-root", default=".", help="Project root path")
    parser.add_argument("--fx-rate", type=float, default=45.0, help="EUR->UAH conversion rate")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()

    selected_asset = None
    selected_file = None
    selected_root = None

    for asset_name in ASSET_PRIORITY:
        located = _find_latest_asset_file(project_root, asset_name)
        if located is not None:
            selected_file, selected_root = located
            selected_asset = asset_name
            break

    if not selected_file or not selected_asset or not selected_root:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": "No Dagster schedule assets found in temporary storage",
                    "project_root": str(project_root),
                }
            )
        )
        raise SystemExit(1)

    try:
        payload = _load_pickled_asset(selected_file)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to read pickled asset: {exc}",
                    "asset": selected_asset,
                    "asset_file": str(selected_file),
                }
            )
        )
        raise SystemExit(1)

    rows = _to_rows(payload)
    selected_rows, selected_client_id = _select_client_rows(rows, args.tenant_id)

    schedule = _normalize_schedule(selected_rows, args.fx_rate)
    recommendation = _build_recommendation(schedule, selected_asset)

    print(
        json.dumps(
            {
                "success": True,
                "source": "dagster_materialized_asset",
                "asset": selected_asset,
                "asset_file": str(selected_file),
                "dagster_home": str(selected_root),
                "tenant_id": args.tenant_id,
                "selected_client_id": selected_client_id,
                "schedule": schedule,
                "recommendation": recommendation,
                "generated_at": datetime.utcnow().isoformat(),
            }
        )
    )


if __name__ == "__main__":
    main()

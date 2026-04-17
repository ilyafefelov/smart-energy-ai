#!/usr/bin/env python3
"""Read latest Dagster materialized schedule asset and output normalized JSON."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_pipeline.dagster_schedule_loader import (
    _build_recommendation,
    _find_latest_asset_file,
    _load_pickled_asset,
    _normalize_schedule,
    _safe_float,
    _select_client_rows,
    _to_rows,
)

ASSET_PRIORITY = [
    "optimization_schedule_milp_asset",
    "optimization_schedule_asset",
]
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
    schedule_start_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

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
                "schedule_start_utc": schedule_start_utc.isoformat(),
                "schedule": schedule,
                "recommendation": recommendation,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    )


if __name__ == "__main__":
    main()

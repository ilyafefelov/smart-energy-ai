#!/usr/bin/env python3
"""Read Dagster optimization schedule asset-check evaluations and emit JSON."""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from dagster import AssetCheckKey, AssetKey, DagsterInstance

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _collect_checks_by_asset() -> Dict[str, tuple[str, ...]]:
    from src.assets.core.optimization_schedule_checks import optimization_schedule_contract_checks

    checks_by_asset: dict[str, list[str]] = {}
    for checks_def in optimization_schedule_contract_checks:
        for spec in checks_def.check_specs:
            asset_name = spec.asset_key.path[-1] if spec.asset_key.path else str(spec.asset_key)
            checks_by_asset.setdefault(asset_name, []).append(spec.name)
    return {asset_name: tuple(check_names) for asset_name, check_names in checks_by_asset.items()}


CHECKS_BY_ASSET = _collect_checks_by_asset()


def _isoformat(timestamp: float | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _jsonable_metadata_value(value: Any) -> Any:
    raw_value = getattr(value, "value", value)
    if isinstance(raw_value, (str, int, float, bool)) or raw_value is None:
        return raw_value
    if isinstance(raw_value, dict):
        return {str(key): _jsonable_metadata_value(item) for key, item in raw_value.items()}
    if isinstance(raw_value, (list, tuple, set)):
        return [_jsonable_metadata_value(item) for item in raw_value]
    return str(raw_value)


def _candidate_dagster_homes(project_root: Path) -> list[tuple[Path, str]]:
    pattern = str(project_root / ".tmp_dagster_home_*")
    temporary_roots = sorted(
        (Path(path) for path in glob.glob(pattern)),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    dagster_home_env = os.getenv("DAGSTER_HOME")
    persistent_roots = [(project_root / "data" / "dagster_home", "persistent")]
    if dagster_home_env:
        persistent_roots.append((Path(dagster_home_env), "environment"))

    seen_roots: set[Path] = set()
    candidates: list[tuple[Path, str]] = []
    for root_path, source in [*[(path, "temporary") for path in temporary_roots], *persistent_roots]:
        try:
            resolved_root = root_path.resolve()
        except FileNotFoundError:
            continue
        if resolved_root in seen_roots or not root_path.exists():
            continue
        seen_roots.add(resolved_root)
        candidates.append((resolved_root, source))
    return candidates


def _ensure_dagster_home_config(dagster_home: Path) -> None:
    dagster_home.mkdir(parents=True, exist_ok=True)
    dagster_yaml = dagster_home / "dagster.yaml"
    if not dagster_yaml.exists():
        dagster_yaml.touch()


def _check_status_from_payload(check: Mapping[str, Any]) -> str:
    status = str(check.get("status") or "not_run").lower()
    if status in {"failed", "warning", "planned", "not_run"}:
        return status
    return "passed"


def summarize_check_states(checks: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    check_list = list(checks)
    total_checks = len(check_list)
    passed_count = sum(1 for check in check_list if _check_status_from_payload(check) == "passed")
    failed_count = sum(1 for check in check_list if _check_status_from_payload(check) == "failed")
    warning_count = sum(1 for check in check_list if _check_status_from_payload(check) == "warning")
    not_run_count = sum(1 for check in check_list if _check_status_from_payload(check) == "not_run")
    planned_count = sum(1 for check in check_list if _check_status_from_payload(check) == "planned")

    if total_checks == 0:
        overall_status = "not_applicable"
    elif failed_count > 0:
        overall_status = "degraded"
    elif warning_count > 0:
        overall_status = "warning"
    elif not_run_count > 0 or planned_count > 0:
        overall_status = "unknown"
    else:
        overall_status = "healthy"

    latest_timestamp = None
    for check in check_list:
        timestamp = check.get("timestamp")
        if isinstance(timestamp, str) and timestamp:
            latest_timestamp = max(latest_timestamp, timestamp) if latest_timestamp else timestamp

    return {
        "overall_status": overall_status,
        "total_checks": total_checks,
        "passed_checks": passed_count,
        "failed_checks": failed_count,
        "warning_checks": warning_count,
        "not_run_checks": not_run_count,
        "planned_checks": planned_count,
        "latest_evaluated_at": latest_timestamp,
        "failing_check_names": [
            f"{check['asset_name']}.{check['check_name']}"
            for check in check_list
            if _check_status_from_payload(check) in {"failed", "warning"}
        ],
        "unevaluated_check_names": [
            f"{check['asset_name']}.{check['check_name']}"
            for check in check_list
            if _check_status_from_payload(check) in {"not_run", "planned"}
        ],
    }


def _build_check_payload(instance: DagsterInstance, asset_name: str, check_name: str) -> Dict[str, Any]:
    record = instance.get_latest_asset_check_evaluation_record(
        AssetCheckKey(asset_key=AssetKey([asset_name]), name=check_name)
    )

    if record is None:
        return {
            "asset_name": asset_name,
            "check_name": check_name,
            "status": "not_run",
            "execution_status": None,
            "severity": None,
            "run_id": None,
            "timestamp": None,
            "description": None,
            "metadata": {},
        }

    evaluation = record.evaluation
    metadata = {
        str(key): _jsonable_metadata_value(value)
        for key, value in (evaluation.metadata.items() if evaluation else [])
    }

    if record.status.value == "PLANNED":
        status = "planned"
    elif evaluation and evaluation.passed:
        status = "passed"
    elif evaluation and getattr(evaluation.severity, "value", "ERROR") == "WARN":
        status = "warning"
    else:
        status = "failed"

    return {
        "asset_name": asset_name,
        "check_name": check_name,
        "status": status,
        "execution_status": record.status.value,
        "severity": getattr(evaluation.severity, "value", None) if evaluation else None,
        "run_id": record.run_id,
        "timestamp": _isoformat(record.create_timestamp),
        "description": evaluation.description if evaluation else None,
        "metadata": metadata,
    }


def _resolve_dagster_home(project_root: Path, dagster_home: str | None) -> tuple[Path, str]:
    if dagster_home:
        return Path(dagster_home).expanduser().resolve(), "explicit"

    candidates = _candidate_dagster_homes(project_root)
    if candidates:
        return candidates[0]

    return (project_root / "data" / "dagster_home").resolve(), "persistent"


def main() -> None:
    parser = argparse.ArgumentParser(description="Read latest Dagster asset check evaluations")
    parser.add_argument("--project-root", default=".", help="Project root path")
    parser.add_argument("--dagster-home", default=None, help="Optional explicit Dagster home path")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    dagster_home, dagster_home_source = _resolve_dagster_home(project_root, args.dagster_home)
    _ensure_dagster_home_config(dagster_home)
    os.environ["DAGSTER_HOME"] = str(dagster_home)

    try:
        instance = DagsterInstance.get()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to load Dagster instance: {exc}",
                    "dagster_home": str(dagster_home),
                    "dagster_home_source": dagster_home_source,
                }
            )
        )
        raise SystemExit(1)

    checks: List[Dict[str, Any]] = []
    assets: List[Dict[str, Any]] = []
    for asset_name, check_names in CHECKS_BY_ASSET.items():
        asset_checks = [_build_check_payload(instance, asset_name, check_name) for check_name in check_names]
        asset_summary = summarize_check_states(asset_checks)
        assets.append(
            {
                "asset_name": asset_name,
                "summary": asset_summary,
                "checks": asset_checks,
            }
        )
        checks.extend(asset_checks)

    print(
        json.dumps(
            {
                "success": True,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "dagster_home": str(dagster_home),
                "dagster_home_source": dagster_home_source,
                "summary": summarize_check_states(checks),
                "assets": assets,
                "checks": checks,
            }
        )
    )


if __name__ == "__main__":
    main()
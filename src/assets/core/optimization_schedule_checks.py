"""Dagster asset checks for optimization schedule contract validation."""

from __future__ import annotations

import json
import math
from collections import Counter
from typing import Any, Dict, Iterable, Tuple

import polars as pl
from dagster import AssetCheckResult, AssetCheckSeverity, asset_check

from .optimization_schedule import optimization_schedule_asset
from .optimization_schedule_milp import optimization_schedule_milp_asset


ROW_COUNT_TARGET = 24
EXPECTED_HOURS = set(range(24))
ACTION_TOLERANCE = 1e-4
FLOW_TOLERANCE = 1e-6


def _serialize_preview(value: Dict[str, Any], limit: int = 5) -> str:
    items = list(value.items())[:limit]
    return json.dumps(dict(items), sort_keys=True)


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None

    if math.isnan(numeric):
        return None

    return numeric


def _coerce_hour(value: Any) -> int | None:
    numeric = _coerce_float(value)
    if numeric is None or not float(numeric).is_integer():
        return None
    return int(numeric)


def _iter_client_frames(schedule: pl.DataFrame) -> Iterable[Tuple[str, pl.DataFrame]]:
    if "client_id" not in schedule.columns:
        yield "default", schedule
        return

    seen: set[str] = set()
    for client_id in schedule.select("client_id").to_series().to_list():
        key = str(client_id)
        if key in seen:
            continue
        seen.add(key)
        if client_id is None:
            yield key, schedule.filter(pl.col("client_id").is_null())
        else:
            yield key, schedule.filter(pl.col("client_id") == client_id)


def evaluate_schedule_completeness(schedule: pl.DataFrame) -> Dict[str, Any]:
    missing_columns = [column for column in ("hour",) if column not in schedule.columns]
    if missing_columns:
        return {
            "passed": False,
            "metadata": {
                "client_count": 0,
                "row_count_violations": 0,
                "duplicate_hour_violations": 0,
                "invalid_hour_violations": 0,
                "missing_hour_violations": 0,
                "missing_columns": ", ".join(missing_columns),
                "failing_clients_preview": "{}",
            },
        }

    row_count_violations = 0
    duplicate_hour_violations = 0
    invalid_hour_violations = 0
    missing_hour_violations = 0
    failing_clients: Dict[str, str] = {}
    client_count = 0

    for client_id, frame in _iter_client_frames(schedule):
        client_count += 1
        parsed_hours = []
        invalid_values = []
        for value in frame.select("hour").to_series().to_list():
            parsed = _coerce_hour(value)
            if parsed is None:
                invalid_values.append(value)
                continue
            parsed_hours.append(parsed)

        hour_counts = Counter(parsed_hours)
        duplicate_hours = sorted(hour for hour, count in hour_counts.items() if count > 1)
        invalid_hours = sorted({hour for hour in parsed_hours if hour not in EXPECTED_HOURS})
        expected_hours_present = {hour for hour in parsed_hours if hour in EXPECTED_HOURS}
        missing_hours = sorted(EXPECTED_HOURS - expected_hours_present)

        violations = []
        if len(frame) != ROW_COUNT_TARGET:
            row_count_violations += 1
            violations.append(f"rows={len(frame)}")
        if duplicate_hours:
            duplicate_hour_violations += 1
            violations.append(f"duplicate_hours={duplicate_hours}")
        if invalid_hours or invalid_values:
            invalid_hour_violations += 1
            violations.append(f"invalid_hours={invalid_hours or invalid_values}")
        if missing_hours:
            missing_hour_violations += 1
            violations.append(f"missing_hours={missing_hours}")

        if violations:
            failing_clients[client_id] = "; ".join(violations)

    return {
        "passed": not failing_clients,
        "metadata": {
            "client_count": client_count,
            "row_count_violations": row_count_violations,
            "duplicate_hour_violations": duplicate_hour_violations,
            "invalid_hour_violations": invalid_hour_violations,
            "missing_hour_violations": missing_hour_violations,
            "missing_columns": "",
            "failing_clients_preview": _serialize_preview(failing_clients),
        },
    }


def evaluate_schedule_numeric_fields(schedule: pl.DataFrame) -> Dict[str, Any]:
    required_columns = ("action_kw", "price_eur_mwh")
    missing_columns = [column for column in required_columns if column not in schedule.columns]
    if missing_columns:
        return {
            "passed": False,
            "metadata": {
                "null_action_kw_count": 0,
                "null_price_eur_mwh_count": 0,
                "missing_columns": ", ".join(missing_columns),
                "failing_rows_preview": "[]",
            },
        }

    null_action_kw_count = 0
    null_price_count = 0
    failing_rows = []

    for row in schedule.iter_rows(named=True):
        row_failures = []
        if _coerce_float(row.get("action_kw")) is None:
            null_action_kw_count += 1
            row_failures.append("action_kw")
        if _coerce_float(row.get("price_eur_mwh")) is None:
            null_price_count += 1
            row_failures.append("price_eur_mwh")
        if row_failures:
            failing_rows.append(
                {
                    "client_id": str(row.get("client_id") or "default"),
                    "hour": row.get("hour"),
                    "fields": row_failures,
                }
            )

    return {
        "passed": null_action_kw_count == 0 and null_price_count == 0,
        "metadata": {
            "null_action_kw_count": null_action_kw_count,
            "null_price_eur_mwh_count": null_price_count,
            "missing_columns": "",
            "failing_rows_preview": json.dumps(failing_rows[:5], sort_keys=True),
        },
    }


def evaluate_schedule_action_semantics(schedule: pl.DataFrame) -> Dict[str, Any]:
    required_columns = ("action_kw", "charge_kwh", "discharge_kwh")
    missing_columns = [column for column in required_columns if column not in schedule.columns]
    if missing_columns:
        return {
            "passed": False,
            "metadata": {
                "simultaneous_charge_discharge_count": 0,
                "action_balance_mismatch_count": 0,
                "missing_columns": ", ".join(missing_columns),
                "failing_rows_preview": "[]",
            },
        }

    simultaneous_count = 0
    mismatch_count = 0
    failing_rows = []

    for row in schedule.iter_rows(named=True):
        action_kw = _coerce_float(row.get("action_kw"))
        charge_kwh = _coerce_float(row.get("charge_kwh"))
        discharge_kwh = _coerce_float(row.get("discharge_kwh"))
        if action_kw is None or charge_kwh is None or discharge_kwh is None:
            continue

        row_failures = []
        if charge_kwh > FLOW_TOLERANCE and discharge_kwh > FLOW_TOLERANCE:
            simultaneous_count += 1
            row_failures.append("simultaneous_charge_discharge")

        expected_action_kw = discharge_kwh - charge_kwh
        if abs(action_kw - expected_action_kw) > ACTION_TOLERANCE:
            mismatch_count += 1
            row_failures.append("action_kw_balance")

        if row_failures:
            failing_rows.append(
                {
                    "client_id": str(row.get("client_id") or "default"),
                    "hour": row.get("hour"),
                    "failures": row_failures,
                }
            )

    return {
        "passed": simultaneous_count == 0 and mismatch_count == 0,
        "metadata": {
            "simultaneous_charge_discharge_count": simultaneous_count,
            "action_balance_mismatch_count": mismatch_count,
            "missing_columns": "",
            "failing_rows_preview": json.dumps(failing_rows[:5], sort_keys=True),
        },
    }


def _build_check_result(evaluation: Dict[str, Any]) -> AssetCheckResult:
    return AssetCheckResult(
        passed=bool(evaluation["passed"]),
        severity=AssetCheckSeverity.ERROR,
        metadata=evaluation["metadata"],
    )


def _make_schedule_completeness_check(asset_def, description: str):
    @asset_check(asset=asset_def, name="schedule_completeness", description=description)
    def _check(schedule: pl.DataFrame) -> AssetCheckResult:
        return _build_check_result(evaluate_schedule_completeness(schedule))

    return _check


def _make_schedule_numeric_fields_check(asset_def, description: str):
    @asset_check(asset=asset_def, name="schedule_numeric_fields", description=description)
    def _check(schedule: pl.DataFrame) -> AssetCheckResult:
        return _build_check_result(evaluate_schedule_numeric_fields(schedule))

    return _check


def _make_schedule_action_semantics_check(asset_def, description: str):
    @asset_check(asset=asset_def, name="schedule_action_semantics", description=description)
    def _check(schedule: pl.DataFrame) -> AssetCheckResult:
        return _build_check_result(evaluate_schedule_action_semantics(schedule))

    return _check


optimization_schedule_completeness_check = _make_schedule_completeness_check(
    optimization_schedule_asset,
    "Validate that the baseline optimization schedule emits a full 24-hour horizon per client with unique offsets.",
)
optimization_schedule_numeric_fields_check = _make_schedule_numeric_fields_check(
    optimization_schedule_asset,
    "Validate that the baseline optimization schedule provides non-null action and price values for every row.",
)
optimization_schedule_action_semantics_check = _make_schedule_action_semantics_check(
    optimization_schedule_asset,
    "Validate that baseline action_kw values match discharge-minus-charge semantics and never charge and discharge simultaneously.",
)

optimization_schedule_milp_completeness_check = _make_schedule_completeness_check(
    optimization_schedule_milp_asset,
    "Validate that the MILP optimization schedule emits a full 24-hour horizon per client with unique offsets.",
)
optimization_schedule_milp_numeric_fields_check = _make_schedule_numeric_fields_check(
    optimization_schedule_milp_asset,
    "Validate that the MILP optimization schedule provides non-null action and price values for every row.",
)
optimization_schedule_milp_action_semantics_check = _make_schedule_action_semantics_check(
    optimization_schedule_milp_asset,
    "Validate that MILP action_kw values match discharge-minus-charge semantics and never charge and discharge simultaneously.",
)


optimization_schedule_contract_checks = [
    optimization_schedule_completeness_check,
    optimization_schedule_numeric_fields_check,
    optimization_schedule_action_semantics_check,
    optimization_schedule_milp_completeness_check,
    optimization_schedule_milp_numeric_fields_check,
    optimization_schedule_milp_action_semantics_check,
]
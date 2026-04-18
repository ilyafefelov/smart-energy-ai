"""Reusable schedule contract evaluators for optimization assets."""

from __future__ import annotations

import json
import math
from collections import Counter
from typing import Any, Dict, Iterable, Tuple

import polars as pl


ROW_COUNT_TARGET = 24
EXPECTED_HOURS = set(range(24))
ACTION_TOLERANCE = 1e-4
FLOW_TOLERANCE = 1e-6
VALID_HORIZON_MODES = {"base", "conservative", "optimistic"}
PROBABILISTIC_HORIZON_SOURCES = {
    "scenario_low_price_eur_mwh",
    "scenario_base_price_eur_mwh",
    "scenario_high_price_eur_mwh",
    "quantile_p10_eur_mwh",
    "quantile_p50_eur_mwh",
    "quantile_p90_eur_mwh",
    "lower_bound_eur_mwh",
    "upper_bound_eur_mwh",
}
ROLLING_METADATA_COLUMNS = (
    "rolling_horizon_enabled",
    "rolling_window_index",
    "rolling_window_start_hour",
    "rolling_window_end_hour",
    "rolling_window_horizon_hours",
    "rolling_window_commit_hours",
    "rolling_state_initial_soc_kwh",
    "rolling_state_initial_throughput_kwh",
    "rolling_window_purchase_cost_eur",
    "rolling_window_export_revenue_eur",
    "rolling_window_degradation_penalty_eur",
    "rolling_window_net_cost_eur",
)


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


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None

    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _filter_client_frame(schedule: pl.DataFrame, client_id: Any) -> pl.DataFrame:
    try:
        if client_id is None:
            return schedule.filter(pl.col("client_id").is_null())
        return schedule.filter(pl.col("client_id") == client_id)
    except TypeError:
        rows = []
        for row in schedule.iter_rows(named=True):
            if row.get("client_id") == client_id:
                rows.append(row)

        frame_type = type(schedule)
        try:
            return frame_type(rows, schema=getattr(schedule, "schema", None))
        except TypeError:
            return frame_type(rows)


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
        yield key, _filter_client_frame(schedule, client_id)


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


def evaluate_schedule_forecast_metadata(schedule: pl.DataFrame) -> Dict[str, Any]:
    required_columns = (
        "forecast_horizon_mode",
        "forecast_horizon_source",
        "forecast_uncertainty_source",
        "forecast_uncertainty_contract_version",
    )
    missing_columns = [column for column in required_columns if column not in schedule.columns]
    if missing_columns:
        return {
            "passed": False,
            "metadata": {
                "missing_forecast_metadata_columns": ", ".join(missing_columns),
                "invalid_forecast_horizon_mode_count": 0,
                "missing_forecast_horizon_source_count": 0,
                "missing_probabilistic_uncertainty_source_count": 0,
                "missing_probabilistic_contract_version_count": 0,
                "forecast_metadata_failing_rows_preview": "[]",
            },
        }

    invalid_mode_count = 0
    missing_horizon_source_count = 0
    missing_probabilistic_uncertainty_source_count = 0
    missing_probabilistic_contract_version_count = 0
    failing_rows = []

    for row in schedule.iter_rows(named=True):
        horizon_mode = _coerce_text(row.get("forecast_horizon_mode"))
        horizon_source = _coerce_text(row.get("forecast_horizon_source"))
        uncertainty_source = _coerce_text(row.get("forecast_uncertainty_source"))
        contract_version = _coerce_text(row.get("forecast_uncertainty_contract_version"))

        row_failures = []
        if horizon_mode not in VALID_HORIZON_MODES:
            invalid_mode_count += 1
            row_failures.append("forecast_horizon_mode")
        if horizon_source is None:
            missing_horizon_source_count += 1
            row_failures.append("forecast_horizon_source")
        elif horizon_source in PROBABILISTIC_HORIZON_SOURCES:
            if uncertainty_source is None:
                missing_probabilistic_uncertainty_source_count += 1
                row_failures.append("forecast_uncertainty_source")
            if contract_version is None:
                missing_probabilistic_contract_version_count += 1
                row_failures.append("forecast_uncertainty_contract_version")

        if row_failures:
            failing_rows.append(
                {
                    "client_id": str(row.get("client_id") or "default"),
                    "hour": row.get("hour"),
                    "fields": row_failures,
                }
            )

    return {
        "passed": (
            invalid_mode_count == 0
            and missing_horizon_source_count == 0
            and missing_probabilistic_uncertainty_source_count == 0
            and missing_probabilistic_contract_version_count == 0
        ),
        "metadata": {
            "missing_forecast_metadata_columns": "",
            "invalid_forecast_horizon_mode_count": invalid_mode_count,
            "missing_forecast_horizon_source_count": missing_horizon_source_count,
            "missing_probabilistic_uncertainty_source_count": (
                missing_probabilistic_uncertainty_source_count
            ),
            "missing_probabilistic_contract_version_count": (
                missing_probabilistic_contract_version_count
            ),
            "forecast_metadata_failing_rows_preview": json.dumps(
                failing_rows[:5],
                sort_keys=True,
            ),
        },
    }


def evaluate_schedule_rolling_horizon_metadata(schedule: pl.DataFrame) -> Dict[str, Any]:
    missing_columns = [column for column in ROLLING_METADATA_COLUMNS if column not in schedule.columns]
    if missing_columns:
        return {
            "passed": False,
            "metadata": {
                "missing_rolling_metadata_columns": ", ".join(missing_columns),
                "missing_rolling_enabled_count": 0,
                "invalid_rolling_window_index_count": 0,
                "invalid_rolling_window_shape_count": 0,
                "invalid_rolling_commit_hours_count": 0,
                "invalid_rolling_initial_soc_count": 0,
                "invalid_rolling_initial_throughput_count": 0,
                "missing_rolling_objective_breakdown_count": 0,
                "rolling_enabled_client_count": 0,
                "rolling_metadata_failing_rows_preview": "[]",
            },
        }

    missing_enabled_count = 0
    invalid_window_index_count = 0
    invalid_window_shape_count = 0
    invalid_commit_hours_count = 0
    invalid_initial_soc_count = 0
    invalid_initial_throughput_count = 0
    missing_objective_breakdown_count = 0
    rolling_enabled_client_count = 0
    failing_rows = []

    for client_id, frame in _iter_client_frames(schedule):
        rows = sorted(frame.iter_rows(named=True), key=lambda row: (_coerce_hour(row.get("hour")) or -1))
        previous_throughput = None
        client_rolling_enabled = False

        for expected_index, row in enumerate(rows):
            row_failures = []
            rolling_enabled = _coerce_bool(row.get("rolling_horizon_enabled"))
            row_hour = _coerce_hour(row.get("hour"))
            rolling_window_index = _coerce_hour(row.get("rolling_window_index"))
            rolling_window_start_hour = _coerce_hour(row.get("rolling_window_start_hour"))
            rolling_window_end_hour = _coerce_hour(row.get("rolling_window_end_hour"))
            rolling_window_horizon_hours = _coerce_hour(row.get("rolling_window_horizon_hours"))
            rolling_window_commit_hours = _coerce_hour(row.get("rolling_window_commit_hours"))
            rolling_state_initial_soc_kwh = _coerce_float(row.get("rolling_state_initial_soc_kwh"))
            rolling_state_initial_throughput_kwh = _coerce_float(
                row.get("rolling_state_initial_throughput_kwh")
            )

            if rolling_enabled is None:
                missing_enabled_count += 1
                row_failures.append("rolling_horizon_enabled")

            if (
                _coerce_float(row.get("rolling_window_purchase_cost_eur")) is None
                or _coerce_float(row.get("rolling_window_export_revenue_eur")) is None
                or _coerce_float(row.get("rolling_window_degradation_penalty_eur")) is None
                or _coerce_float(row.get("rolling_window_net_cost_eur")) is None
            ):
                missing_objective_breakdown_count += 1
                row_failures.append("rolling_window_objective")

            if rolling_enabled is True:
                client_rolling_enabled = True
                if rolling_window_index != expected_index:
                    invalid_window_index_count += 1
                    row_failures.append("rolling_window_index")
                if rolling_window_start_hour != row_hour:
                    invalid_window_index_count += 1
                    row_failures.append("rolling_window_start_hour")

                expected_horizon_hours = None
                if rolling_window_start_hour is not None and rolling_window_end_hour is not None:
                    expected_horizon_hours = rolling_window_end_hour - rolling_window_start_hour + 1
                if (
                    rolling_window_horizon_hours is None
                    or rolling_window_horizon_hours < 1
                    or expected_horizon_hours is None
                    or rolling_window_horizon_hours != expected_horizon_hours
                ):
                    invalid_window_shape_count += 1
                    row_failures.append("rolling_window_horizon_hours")

                if rolling_window_commit_hours != 1:
                    invalid_commit_hours_count += 1
                    row_failures.append("rolling_window_commit_hours")

                soc_before_kwh = _coerce_float(row.get("soc_before_kwh"))
                if (
                    rolling_state_initial_soc_kwh is None
                    or soc_before_kwh is None
                    or abs(rolling_state_initial_soc_kwh - soc_before_kwh) > ACTION_TOLERANCE
                ):
                    invalid_initial_soc_count += 1
                    row_failures.append("rolling_state_initial_soc_kwh")

                if rolling_state_initial_throughput_kwh is None:
                    invalid_initial_throughput_count += 1
                    row_failures.append("rolling_state_initial_throughput_kwh")
                elif previous_throughput is not None and abs(rolling_state_initial_throughput_kwh - previous_throughput) > ACTION_TOLERANCE:
                    invalid_initial_throughput_count += 1
                    row_failures.append("rolling_state_transition")

            if row_failures:
                failing_rows.append(
                    {
                        "client_id": client_id,
                        "hour": row.get("hour"),
                        "fields": row_failures,
                    }
                )

            throughput_total_kwh = _coerce_float(row.get("throughput_total_kwh"))
            if throughput_total_kwh is not None:
                previous_throughput = throughput_total_kwh

        if client_rolling_enabled:
            rolling_enabled_client_count += 1

    return {
        "passed": not failing_rows,
        "metadata": {
            "missing_rolling_metadata_columns": "",
            "missing_rolling_enabled_count": missing_enabled_count,
            "invalid_rolling_window_index_count": invalid_window_index_count,
            "invalid_rolling_window_shape_count": invalid_window_shape_count,
            "invalid_rolling_commit_hours_count": invalid_commit_hours_count,
            "invalid_rolling_initial_soc_count": invalid_initial_soc_count,
            "invalid_rolling_initial_throughput_count": invalid_initial_throughput_count,
            "missing_rolling_objective_breakdown_count": missing_objective_breakdown_count,
            "rolling_enabled_client_count": rolling_enabled_client_count,
            "rolling_metadata_failing_rows_preview": json.dumps(failing_rows[:5], sort_keys=True),
        },
    }


__all__ = [
    "ACTION_TOLERANCE",
    "EXPECTED_HOURS",
    "FLOW_TOLERANCE",
    "ROLLING_METADATA_COLUMNS",
    "ROW_COUNT_TARGET",
    "evaluate_schedule_action_semantics",
    "evaluate_schedule_completeness",
    "evaluate_schedule_forecast_metadata",
    "evaluate_schedule_numeric_fields",
    "evaluate_schedule_rolling_horizon_metadata",
]
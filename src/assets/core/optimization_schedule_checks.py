"""Dagster asset checks for optimization schedule contract validation."""

from __future__ import annotations

from typing import Any, Dict, Sequence

import polars as pl
from dagster import AssetCheckResult, AssetCheckSeverity, asset_check

from src.data_pipeline.optimization_history_reconciliation import (
    evaluate_reconciliation_rows,
    resolve_optimization_history_db_url,
)
from src.data_pipeline.optimization_schedule_validators import (
    evaluate_schedule_action_semantics,
    evaluate_schedule_completeness,
    evaluate_schedule_numeric_fields,
)
from .optimization_schedule import optimization_schedule_asset
from .optimization_schedule_milp import optimization_schedule_milp_asset


def _build_check_result(
    evaluation: Dict[str, Any],
    *,
    severity: Any = AssetCheckSeverity.ERROR,
) -> AssetCheckResult:
    return AssetCheckResult(
        passed=bool(evaluation["passed"]),
        severity=severity,
        metadata=evaluation["metadata"],
    )


def _warning_severity() -> Any:
    return getattr(AssetCheckSeverity, "WARN", AssetCheckSeverity.ERROR)


def _schedule_rows(schedule: pl.DataFrame) -> list[dict[str, Any]]:
    if hasattr(schedule, "to_dicts"):
        return [dict(row) for row in schedule.to_dicts()]
    return []


def _non_empty_values(rows: Sequence[dict[str, Any]], key: str) -> set[str]:
    values: set[str] = set()
    for row in rows:
        raw = row.get(key)
        if raw is None:
            continue
        text = str(raw).strip()
        if text:
            values.add(text)
    return values


def evaluate_schedule_lineage(schedule: pl.DataFrame) -> Dict[str, Any]:
    rows = _schedule_rows(schedule)
    required_columns = ["forecast_run_id", "optimization_run_id", "forecast_model_version"]
    available_columns = list(getattr(schedule, "columns", []))
    missing_columns = [column for column in required_columns if column not in available_columns]

    if not rows:
        return {
            "passed": not missing_columns,
            "metadata": {
                "status": "empty_schedule",
                "missing_lineage_columns": ",".join(missing_columns),
                "missing_lineage_column_count": len(missing_columns),
                "null_forecast_run_id_count": 0,
                "null_optimization_run_id_count": 0,
                "null_forecast_model_version_count": 0,
                "multi_forecast_run_clients": 0,
                "multi_optimization_run_clients": 0,
            },
        }

    forecast_ids_by_client: dict[str, set[str]] = {}
    optimization_ids_by_client: dict[str, set[str]] = {}
    null_forecast_run_id_count = 0
    null_optimization_run_id_count = 0
    null_forecast_model_version_count = 0

    for row in rows:
        client_id = str(row.get("client_id") or "client_default")
        forecast_run_id = str(row.get("forecast_run_id") or "").strip()
        optimization_run_id = str(row.get("optimization_run_id") or "").strip()
        model_version = str(row.get("forecast_model_version") or "").strip()

        if not forecast_run_id:
            null_forecast_run_id_count += 1
        else:
            forecast_ids_by_client.setdefault(client_id, set()).add(forecast_run_id)

        if not optimization_run_id:
            null_optimization_run_id_count += 1
        else:
            optimization_ids_by_client.setdefault(client_id, set()).add(optimization_run_id)

        if not model_version:
            null_forecast_model_version_count += 1

    multi_forecast_run_clients = sum(1 for values in forecast_ids_by_client.values() if len(values) > 1)
    multi_optimization_run_clients = sum(1 for values in optimization_ids_by_client.values() if len(values) > 1)
    passed = (
        not missing_columns
        and null_forecast_run_id_count == 0
        and null_optimization_run_id_count == 0
        and null_forecast_model_version_count == 0
        and multi_forecast_run_clients == 0
        and multi_optimization_run_clients == 0
    )

    return {
        "passed": passed,
        "metadata": {
            "status": "validated",
            "missing_lineage_columns": ",".join(missing_columns),
            "missing_lineage_column_count": len(missing_columns),
            "null_forecast_run_id_count": null_forecast_run_id_count,
            "null_optimization_run_id_count": null_optimization_run_id_count,
            "null_forecast_model_version_count": null_forecast_model_version_count,
            "multi_forecast_run_clients": multi_forecast_run_clients,
            "multi_optimization_run_clients": multi_optimization_run_clients,
        },
    }


def _load_recent_history_rows(*, days: int = 14, limit: int = 5000) -> tuple[list[dict[str, Any]], str | None]:
    from sqlalchemy import create_engine, text

    select_sql = text(
        """
        SELECT
          id,
          tenant_id,
          timestamp,
          predicted_action,
          cost_baseline,
          cost_rl,
          energy_kwh,
          price_uah_kwh,
          tariff_window,
          economics_method,
          realized_net_uah,
          forecast_run_id,
          forecast_model_version,
          optimization_run_id,
          decision_snapshot,
          command_id,
          schedule_id
        FROM optimization_history
        WHERE timestamp >= NOW() - make_interval(days => :days)
        ORDER BY timestamp DESC
        LIMIT :limit
        """
    )

    try:
        engine = create_engine(resolve_optimization_history_db_url(), pool_pre_ping=True)
        with engine.begin() as conn:
            rows = conn.execute(select_sql, {"days": int(days), "limit": int(limit)}).mappings().all()
        return [dict(row) for row in rows], None
    except Exception as exc:
        return [], str(exc)


def evaluate_schedule_realized_value_reconciliation(schedule: pl.DataFrame) -> Dict[str, Any]:
    rows = _schedule_rows(schedule)
    if not rows:
        return {
            "passed": True,
            "metadata": {
                "status": "empty_schedule",
                "history_source_status": "not_checked",
                "history_source_error": "",
            },
        }

    history_rows, error = _load_recent_history_rows()
    if error is not None:
        return {
            "passed": False,
            "metadata": {
                "status": "history_unavailable",
                "history_source_status": "unavailable",
                "history_source_error": error,
            },
        }

    expected_tenants = _non_empty_values(rows, "client_id")
    filtered_history_rows = [
        row
        for row in history_rows
        if not row.get("tenant_id") or str(row.get("tenant_id")).strip() in expected_tenants
    ]
    evaluation = evaluate_reconciliation_rows(
        filtered_history_rows,
        note="dagster_schedule_reconciliation_check",
        expected_forecast_run_ids=sorted(_non_empty_values(rows, "forecast_run_id")),
        expected_optimization_run_ids=sorted(_non_empty_values(rows, "optimization_run_id")),
    )
    evaluation["metadata"]["history_source_status"] = "loaded"
    evaluation["metadata"]["history_source_error"] = ""
    evaluation["metadata"]["filtered_history_row_count"] = len(filtered_history_rows)
    return evaluation


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


def _make_schedule_lineage_check(asset_def, description: str):
    @asset_check(asset=asset_def, name="schedule_lineage", description=description)
    def _check(schedule: pl.DataFrame) -> AssetCheckResult:
        return _build_check_result(evaluate_schedule_lineage(schedule))

    return _check


def _make_schedule_realized_value_reconciliation_check(asset_def, description: str):
    @asset_check(asset=asset_def, name="schedule_realized_value_reconciliation", description=description)
    def _check(schedule: pl.DataFrame) -> AssetCheckResult:
        return _build_check_result(
            evaluate_schedule_realized_value_reconciliation(schedule),
            severity=_warning_severity(),
        )

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
optimization_schedule_lineage_check = _make_schedule_lineage_check(
    optimization_schedule_asset,
    "Validate that the baseline optimization schedule emits stable forecast and optimization lineage fields for every client horizon.",
)
optimization_schedule_realized_value_reconciliation_check = _make_schedule_realized_value_reconciliation_check(
    optimization_schedule_asset,
    "Compare baseline schedule lineage against recent optimization_history rows and surface realized-value reconciliation gaps.",
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
optimization_schedule_milp_lineage_check = _make_schedule_lineage_check(
    optimization_schedule_milp_asset,
    "Validate that the MILP optimization schedule emits stable forecast and optimization lineage fields for every client horizon.",
)
optimization_schedule_milp_realized_value_reconciliation_check = _make_schedule_realized_value_reconciliation_check(
    optimization_schedule_milp_asset,
    "Compare MILP schedule lineage against recent optimization_history rows and surface realized-value reconciliation gaps.",
)


optimization_schedule_contract_checks = [
    optimization_schedule_completeness_check,
    optimization_schedule_numeric_fields_check,
    optimization_schedule_action_semantics_check,
    optimization_schedule_lineage_check,
    optimization_schedule_realized_value_reconciliation_check,
    optimization_schedule_milp_completeness_check,
    optimization_schedule_milp_numeric_fields_check,
    optimization_schedule_milp_action_semantics_check,
    optimization_schedule_milp_lineage_check,
    optimization_schedule_milp_realized_value_reconciliation_check,
]
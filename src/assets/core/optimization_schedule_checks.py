"""Dagster asset checks for optimization schedule contract validation."""

from __future__ import annotations

from typing import Any, Dict

import polars as pl
from dagster import AssetCheckResult, AssetCheckSeverity, asset_check

from src.data_pipeline.optimization_schedule_validators import (
    evaluate_schedule_action_semantics,
    evaluate_schedule_completeness,
    evaluate_schedule_numeric_fields,
)
from .optimization_schedule import optimization_schedule_asset
from .optimization_schedule_milp import optimization_schedule_milp_asset


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
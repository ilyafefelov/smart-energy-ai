"""Unit tests for Dagster optimization schedule asset checks."""

from __future__ import annotations

import polars as pl

from src.assets.core.optimization_schedule_checks import (
    evaluate_schedule_action_semantics,
    evaluate_schedule_completeness,
    evaluate_schedule_numeric_fields,
    optimization_schedule_contract_checks,
)
from src.definitions import defs


def _valid_schedule() -> pl.DataFrame:
    rows = []
    for hour in range(24):
        charge_kwh = 5.0 if hour < 6 else 0.0
        discharge_kwh = 6.0 if 17 <= hour <= 20 else 0.0
        rows.append(
            {
                "client_id": "client_a",
                "hour": hour,
                "action_kw": discharge_kwh - charge_kwh,
                "charge_kwh": charge_kwh,
                "discharge_kwh": discharge_kwh,
                "price_eur_mwh": 40.0 + hour,
            }
        )
    return pl.DataFrame(rows)


def test_schedule_contract_checks_pass_for_valid_schedule() -> None:
    schedule = _valid_schedule()

    completeness = evaluate_schedule_completeness(schedule)
    numeric_fields = evaluate_schedule_numeric_fields(schedule)
    action_semantics = evaluate_schedule_action_semantics(schedule)

    assert completeness["passed"] is True
    assert numeric_fields["passed"] is True
    assert action_semantics["passed"] is True


def test_schedule_contract_checks_fail_for_duplicate_missing_and_inconsistent_rows() -> None:
    schedule = _valid_schedule().filter(pl.col("hour") != 23)
    schedule = schedule.with_columns(
        pl.when(pl.col("hour") == 4).then(3).otherwise(pl.col("hour")).alias("hour"),
        pl.when(pl.col("hour") == 10).then(None).otherwise(pl.col("price_eur_mwh")).alias("price_eur_mwh"),
        pl.when(pl.col("hour") == 17).then(1.5).otherwise(pl.col("action_kw")).alias("action_kw"),
        pl.when(pl.col("hour") == 17).then(2.0).otherwise(pl.col("charge_kwh")).alias("charge_kwh"),
    )

    completeness = evaluate_schedule_completeness(schedule)
    numeric_fields = evaluate_schedule_numeric_fields(schedule)
    action_semantics = evaluate_schedule_action_semantics(schedule)

    assert completeness["passed"] is False
    assert completeness["metadata"]["row_count_violations"] == 1
    assert completeness["metadata"]["duplicate_hour_violations"] == 1
    assert completeness["metadata"]["missing_hour_violations"] == 1

    assert numeric_fields["passed"] is False
    assert numeric_fields["metadata"]["null_price_eur_mwh_count"] == 1

    assert action_semantics["passed"] is False
    assert action_semantics["metadata"]["simultaneous_charge_discharge_count"] == 1
    assert action_semantics["metadata"]["action_balance_mismatch_count"] == 1


def test_definitions_register_schedule_checks_and_job() -> None:
    assert len(optimization_schedule_contract_checks) == 6
    assert len(defs.asset_checks) == 6
    job_def = defs.resolve_job_def("optimization_schedule_contract_checks")

    assert job_def is not None
    assert "client_state_asset" in job_def.graph.node_dict
    assert "price_forecast_asset" in job_def.graph.node_dict
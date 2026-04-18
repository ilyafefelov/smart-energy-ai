"""Unit tests for Dagster optimization schedule asset checks."""

from __future__ import annotations

from datetime import datetime

import polars as pl

from src.assets.core.optimization_schedule import (
    OPTIMIZATION_SCHEDULE_SCHEMA,
    build_empty_optimization_schedule,
    build_optimization_schedule_frame,
)
from src.assets.core.optimization_schedule_checks import (
    evaluate_schedule_lineage,
    evaluate_schedule_realized_value_reconciliation,
    evaluate_schedule_action_semantics,
    evaluate_schedule_completeness,
    evaluate_schedule_forecast_metadata,
    evaluate_schedule_numeric_fields,
    evaluate_schedule_rolling_horizon_metadata,
    optimization_schedule_contract_checks,
    optimization_schedule_lineage_check,
    optimization_schedule_realized_value_reconciliation_check,
)
from src.definitions import defs


def _valid_schedule() -> pl.DataFrame:
    rows = []
    throughput_before_kwh = 0.0
    soc_before_kwh = 100.0
    for hour in range(24):
        charge_kwh = 5.0 if hour < 6 else 0.0
        discharge_kwh = 6.0 if 17 <= hour <= 20 else 0.0
        throughput_total_kwh = throughput_before_kwh + charge_kwh + discharge_kwh
        soc_after_kwh = soc_before_kwh + charge_kwh - discharge_kwh
        rolling_window_horizon_hours = 24 - hour
        rolling_window_net_cost_eur = 10.0 + hour
        rows.append(
            {
                "client_id": "client_a",
                "hour": hour,
                "action_kw": discharge_kwh - charge_kwh,
                "charge_kwh": charge_kwh,
                "discharge_kwh": discharge_kwh,
                "soc_before_kwh": soc_before_kwh,
                "soc_after_kwh": soc_after_kwh,
                "throughput_total_kwh": throughput_total_kwh,
                "price_eur_mwh": 40.0 + hour,
                "forecast_horizon_mode": "conservative",
                "forecast_horizon_source": "scenario_low_price_eur_mwh",
                "forecast_uncertainty_source": "walk_forward_residual_std",
                "forecast_uncertainty_contract_version": "probabilistic_forecast_v1",
                "rolling_horizon_enabled": True,
                "rolling_window_index": hour,
                "rolling_window_start_hour": hour,
                "rolling_window_end_hour": hour + rolling_window_horizon_hours - 1,
                "rolling_window_horizon_hours": rolling_window_horizon_hours,
                "rolling_window_commit_hours": 1,
                "rolling_state_initial_soc_kwh": soc_before_kwh,
                "rolling_state_initial_throughput_kwh": throughput_before_kwh,
                "rolling_window_purchase_cost_eur": rolling_window_net_cost_eur,
                "rolling_window_export_revenue_eur": 0.0,
                "rolling_window_degradation_penalty_eur": 0.0,
                "rolling_window_net_cost_eur": rolling_window_net_cost_eur,
            }
        )
        throughput_before_kwh = throughput_total_kwh
        soc_before_kwh = soc_after_kwh
    return pl.DataFrame(rows)


def test_schedule_contract_checks_pass_for_valid_schedule() -> None:
    schedule = _valid_schedule()

    completeness = evaluate_schedule_completeness(schedule)
    numeric_fields = evaluate_schedule_numeric_fields(schedule)
    action_semantics = evaluate_schedule_action_semantics(schedule)
    forecast_metadata = evaluate_schedule_forecast_metadata(schedule)
    rolling_metadata = evaluate_schedule_rolling_horizon_metadata(schedule)

    assert completeness["passed"] is True
    assert numeric_fields["passed"] is True
    assert action_semantics["passed"] is True
    assert forecast_metadata["passed"] is True
    assert rolling_metadata["passed"] is True


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


def test_schedule_lineage_checks_detect_missing_and_inconsistent_lineage(monkeypatch) -> None:
    schedule = _valid_schedule().with_columns(
        pl.lit("forecast-demo").alias("forecast_run_id"),
        pl.lit("registry:demo").alias("forecast_model_version"),
        pl.when(pl.col("hour") == 0).then(pl.lit("optimization-a")).otherwise(pl.lit("optimization-b")).alias("optimization_run_id"),
    )

    lineage = evaluate_schedule_lineage(schedule)
    lineage_result = optimization_schedule_lineage_check(schedule)

    assert lineage["passed"] is False
    assert lineage["metadata"]["multi_optimization_run_clients"] == 1
    assert lineage_result.passed is False

    valid_lineage_schedule = schedule.with_columns(pl.lit("optimization-a").alias("optimization_run_id"))
    matching_history_rows = [
        {
            "id": 1,
            "tenant_id": "client_a",
            "timestamp": datetime(2026, 3, 6, 10, 0, 0),
            "predicted_action": 0,
            "cost_baseline": 40.0,
            "cost_rl": 24.0,
            "energy_kwh": 4.0,
            "price_uah_kwh": 10.0,
            "tariff_window": "",
            "economics_method": "tariff_interval",
            "realized_net_uah": -24.0,
            "decision_snapshot": {
                "forecast_run_id": "forecast-demo",
                "optimization_run_id": "optimization-a",
            },
        }
    ]
    monkeypatch.setattr(
        "src.assets.core.optimization_schedule_checks._load_recent_history_rows",
        lambda **kwargs: (matching_history_rows, None),
    )

    reconciliation = evaluate_schedule_realized_value_reconciliation(valid_lineage_schedule)
    reconciliation_result = optimization_schedule_realized_value_reconciliation_check(valid_lineage_schedule)

    assert reconciliation["passed"] is True
    assert reconciliation["metadata"]["status"] == "reconciled"
    assert reconciliation["metadata"]["canonical_savings_total_uah"] == 6.0
    assert reconciliation["metadata"]["realized_net_total_uah"] == -24.0
    assert reconciliation_result.passed is True

    monkeypatch.setattr(
        "src.assets.core.optimization_schedule_checks._load_recent_history_rows",
        lambda **kwargs: (
            [
                {
                    "id": 2,
                    "tenant_id": "client_a",
                    "timestamp": datetime(2026, 3, 6, 10, 0, 0),
                    "predicted_action": 0,
                    "cost_baseline": 40.0,
                    "cost_rl": 24.0,
                    "energy_kwh": 4.0,
                    "price_uah_kwh": 10.0,
                    "tariff_window": "offpeak",
                    "economics_method": "tariff_interval",
                    "realized_net_uah": -24.0,
                    "decision_snapshot": {},
                }
            ],
            None,
        ),
    )

    missing_lineage = evaluate_schedule_realized_value_reconciliation(valid_lineage_schedule)
    assert missing_lineage["passed"] is False
    assert missing_lineage["metadata"]["lineage_missing_row_count"] == 1


def test_schedule_lineage_checks_fail_for_missing_forecast_provenance() -> None:
    schedule = _valid_schedule().with_columns(
        pl.lit("forecast-demo").alias("forecast_run_id"),
        pl.lit("registry:demo").alias("forecast_model_version"),
        pl.lit("optimization-a").alias("optimization_run_id"),
        pl.lit(None).alias("forecast_horizon_source"),
    )

    lineage = evaluate_schedule_lineage(schedule)
    lineage_result = optimization_schedule_lineage_check(schedule)

    assert lineage["passed"] is False
    assert lineage["metadata"]["missing_forecast_horizon_source_count"] == 24
    assert lineage_result.passed is False


def test_schedule_lineage_checks_fail_for_rolling_horizon_transition_breakage() -> None:
    schedule = _valid_schedule().with_columns(
        pl.lit("forecast-demo").alias("forecast_run_id"),
        pl.lit("registry:demo").alias("forecast_model_version"),
        pl.lit("optimization-a").alias("optimization_run_id"),
        pl.when(pl.col("hour") == 5)
        .then(999.0)
        .otherwise(pl.col("rolling_state_initial_throughput_kwh"))
        .alias("rolling_state_initial_throughput_kwh"),
    )

    lineage = evaluate_schedule_lineage(schedule)

    assert lineage["passed"] is False
    assert lineage["metadata"]["invalid_rolling_initial_throughput_count"] >= 1


def test_schedule_frame_builder_uses_canonical_schema_for_empty_and_sparse_rows() -> None:
    empty_schedule = build_empty_optimization_schedule()
    sparse_schedule = build_optimization_schedule_frame(
        [
            {
                "client_id": "client_a",
                "hour": 0,
                "action_kw": 0.0,
                "charge_kwh": 0.0,
                "discharge_kwh": 0.0,
                "soc_before_kwh": 50.0,
                "soc_after_kwh": 50.0,
                "throughput_total_kwh": 0.0,
                "price_eur_mwh": 42.0,
                "load_kwh": 5.0,
                "solar_kwh": 0.0,
                "grid_import_kwh": 5.0,
                "grid_export_kwh": 0.0,
                "purchase_cost_eur": 0.21,
                "export_revenue_eur": 0.0,
                "degradation_penalty_eur": 0.0,
                "net_cost_eur": 0.21,
                "total_net_cost_eur": 5.04,
                "algorithm": "mip_scheduler",
                "solver": "highs",
            }
        ]
    )

    assert empty_schedule.schema == OPTIMIZATION_SCHEDULE_SCHEMA
    assert sparse_schedule.schema == OPTIMIZATION_SCHEDULE_SCHEMA
    assert sparse_schedule.columns == list(OPTIMIZATION_SCHEDULE_SCHEMA.keys())
    assert sparse_schedule.get_column("final_soc_kwh").to_list() == [None]
    assert sparse_schedule.get_column("throughput_limit_kwh").to_list() == [None]
    assert sparse_schedule.get_column("rolling_horizon_enabled").to_list() == [None]
    assert sparse_schedule.get_column("rolling_window_net_cost_eur").to_list() == [None]


def test_definitions_register_schedule_checks_and_job() -> None:
    assert len(optimization_schedule_contract_checks) == 10
    assert len(defs.asset_checks) == 10
    job_def = defs.resolve_job_def("optimization_schedule_contract_checks")

    assert job_def is not None
    assert "client_state_asset" in job_def.graph.node_dict
    assert "price_forecast_asset" in job_def.graph.node_dict
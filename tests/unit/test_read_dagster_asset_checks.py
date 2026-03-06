"""Unit tests for Dagster asset-check summary normalization."""

from __future__ import annotations

from scripts.read_dagster_asset_checks import summarize_check_states


def test_summarize_check_states_marks_healthy_when_all_checks_pass() -> None:
    summary = summarize_check_states(
        [
            {"asset_name": "optimization_schedule_asset", "check_name": "schedule_completeness", "status": "passed", "timestamp": "2026-03-06T08:00:00+00:00"},
            {"asset_name": "optimization_schedule_asset", "check_name": "schedule_numeric_fields", "status": "passed", "timestamp": "2026-03-06T08:01:00+00:00"},
        ]
    )

    assert summary["overall_status"] == "healthy"
    assert summary["passed_checks"] == 2
    assert summary["failed_checks"] == 0
    assert summary["latest_evaluated_at"] == "2026-03-06T08:01:00+00:00"


def test_summarize_check_states_marks_unknown_for_unevaluated_checks() -> None:
    summary = summarize_check_states(
        [
            {"asset_name": "optimization_schedule_asset", "check_name": "schedule_completeness", "status": "not_run", "timestamp": None},
            {"asset_name": "optimization_schedule_asset", "check_name": "schedule_numeric_fields", "status": "planned", "timestamp": None},
        ]
    )

    assert summary["overall_status"] == "unknown"
    assert summary["not_run_checks"] == 1
    assert summary["planned_checks"] == 1
    assert len(summary["unevaluated_check_names"]) == 2


def test_summarize_check_states_marks_degraded_for_failures() -> None:
    summary = summarize_check_states(
        [
            {"asset_name": "optimization_schedule_asset", "check_name": "schedule_completeness", "status": "failed", "timestamp": "2026-03-06T08:02:00+00:00"},
            {"asset_name": "optimization_schedule_milp_asset", "check_name": "schedule_action_semantics", "status": "warning", "timestamp": "2026-03-06T08:03:00+00:00"},
        ]
    )

    assert summary["overall_status"] == "degraded"
    assert summary["failed_checks"] == 1
    assert summary["warning_checks"] == 1
    assert summary["failing_check_names"] == [
        "optimization_schedule_asset.schedule_completeness",
        "optimization_schedule_milp_asset.schedule_action_semantics",
    ]
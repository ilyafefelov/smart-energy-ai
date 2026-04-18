"""Reusable helpers for optimization history reconciliation flows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence

from src.data_pipeline.optimization_economics import (
    _resolve_canonical_prices,
    _safe_number,
    compute_canonical_costs,
    determine_tariff_window,
)


@dataclass
class ReconcileResult:
    scanned: int = 0
    eligible: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0


@dataclass(frozen=True)
class RowReconcileOutcome:
    row_id: int
    eligible: bool
    status: str
    update_params: Optional[Dict[str, Any]] = None
    canonical_baseline_cost: Optional[float] = None
    canonical_optimized_cost: Optional[float] = None
    stored_baseline_cost: Optional[float] = None
    stored_optimized_cost: Optional[float] = None
    realized_net_uah: Optional[float] = None
    forecast_run_id: Optional[str] = None
    optimization_run_id: Optional[str] = None


def resolve_optimization_history_db_url() -> str:
    import os

    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit

    host = os.getenv("APP_DB_HOST") or os.getenv("DB_HOST") or "localhost"
    port = os.getenv("APP_DB_PORT") or os.getenv("DB_PORT") or "5432"
    user = os.getenv("APP_DB_USER") or os.getenv("DB_USER") or "dagster"
    password = os.getenv("APP_DB_PASSWORD") or os.getenv("DB_PASSWORD") or "dagster"
    database = os.getenv("APP_DB_NAME") or os.getenv("OPTIMIZATION_DB_NAME") or "smart_energy_ai"
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def _normalize_lineage_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_snapshot(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except ValueError:
            return None
        if isinstance(parsed, Mapping):
            return parsed
    return None


def _read_snapshot_lineage(snapshot: Mapping[str, Any] | None, key: str) -> Optional[str]:
    if snapshot is None:
        return None

    candidates = [
        snapshot.get(key),
        snapshot.get("lineage", {}).get(key) if isinstance(snapshot.get("lineage"), Mapping) else None,
        snapshot.get("provenance", {}).get(key) if isinstance(snapshot.get("provenance"), Mapping) else None,
        snapshot.get("inference_lineage", {}).get(key) if isinstance(snapshot.get("inference_lineage"), Mapping) else None,
        snapshot.get("contract", {}).get(key) if isinstance(snapshot.get("contract"), Mapping) else None,
    ]
    for candidate in candidates:
        normalized = _normalize_lineage_value(candidate)
        if normalized is not None:
            return normalized
    return None


def _extract_row_lineage(row: Mapping[str, Any]) -> tuple[Optional[str], Optional[str]]:
    snapshot = _coerce_snapshot(row.get("decision_snapshot"))
    forecast_run_id = _normalize_lineage_value(row.get("forecast_run_id")) or _read_snapshot_lineage(snapshot, "forecast_run_id")
    optimization_run_id = _normalize_lineage_value(row.get("optimization_run_id")) or _read_snapshot_lineage(snapshot, "optimization_run_id")
    return forecast_run_id, optimization_run_id


def _is_unchanged_cost_pair(
    previous_baseline: Optional[float],
    previous_optimized: Optional[float],
    baseline_cost: float,
    optimized_cost: float,
) -> bool:
    return (
        previous_baseline is not None
        and previous_optimized is not None
        and abs(previous_baseline - baseline_cost) < 1e-6
        and abs(previous_optimized - optimized_cost) < 1e-6
    )


def evaluate_row_for_reconciliation(row: Dict[str, Any], note: str) -> RowReconcileOutcome:
    row_id = int(row["id"])
    ts = row["timestamp"]
    predicted_action = int(row["predicted_action"])
    forecast_run_id, optimization_run_id = _extract_row_lineage(row)

    energy_kwh = _safe_number(row["energy_kwh"])
    unit_price = _safe_number(row["price_uah_kwh"])
    if energy_kwh is None or energy_kwh <= 0 or unit_price is None or unit_price <= 0:
        return RowReconcileOutcome(
            row_id=row_id,
            eligible=False,
            status="skipped",
            stored_baseline_cost=_safe_number(row.get("cost_baseline")),
            stored_optimized_cost=_safe_number(row.get("cost_rl")),
            realized_net_uah=_safe_number(row.get("realized_net_uah")),
            forecast_run_id=forecast_run_id,
            optimization_run_id=optimization_run_id,
        )

    tariff_window = str(row.get("tariff_window") or "").lower()
    derived_window = determine_tariff_window(ts if isinstance(ts, datetime) else datetime.now(timezone.utc))
    peak_price, off_peak_price = _resolve_canonical_prices(unit_price, tariff_window, derived_window)

    baseline_cost, optimized_cost = compute_canonical_costs(
        predicted_action=predicted_action,
        energy_kwh=energy_kwh,
        unit_price_uah_kwh=unit_price,
        peak_price=peak_price,
        off_peak_price=off_peak_price,
    )

    old_baseline = _safe_number(row["cost_baseline"])
    old_rl = _safe_number(row["cost_rl"])
    if _is_unchanged_cost_pair(old_baseline, old_rl, baseline_cost, optimized_cost):
        return RowReconcileOutcome(
            row_id=row_id,
            eligible=True,
            status="unchanged",
            canonical_baseline_cost=baseline_cost,
            canonical_optimized_cost=optimized_cost,
            stored_baseline_cost=old_baseline,
            stored_optimized_cost=old_rl,
            realized_net_uah=_safe_number(row.get("realized_net_uah")),
            forecast_run_id=forecast_run_id,
            optimization_run_id=optimization_run_id,
        )

    return RowReconcileOutcome(
        row_id=row_id,
        eligible=True,
        status="updated",
        update_params={
            "id": row_id,
            "cost_baseline": baseline_cost,
            "cost_rl": optimized_cost,
            "reconciliation_note": note,
        },
        canonical_baseline_cost=baseline_cost,
        canonical_optimized_cost=optimized_cost,
        stored_baseline_cost=old_baseline,
        stored_optimized_cost=old_rl,
        realized_net_uah=_safe_number(row.get("realized_net_uah")),
        forecast_run_id=forecast_run_id,
        optimization_run_id=optimization_run_id,
    )


def evaluate_reconciliation_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    note: str,
    expected_forecast_run_ids: Sequence[str] | None = None,
    expected_optimization_run_ids: Sequence[str] | None = None,
) -> Dict[str, Any]:
    expected_forecast = {
        value for value in (_normalize_lineage_value(item) for item in (expected_forecast_run_ids or [])) if value
    }
    expected_optimization = {
        value for value in (_normalize_lineage_value(item) for item in (expected_optimization_run_ids or [])) if value
    }

    stats = ReconcileResult()
    outcomes: list[RowReconcileOutcome] = []
    history_forecast_ids: set[str] = set()
    history_optimization_ids: set[str] = set()
    lineage_available_rows = 0
    lineage_missing_rows = 0
    lineage_mismatch_rows = 0
    lineage_matched_rows = 0
    canonical_baseline_total = 0.0
    canonical_optimized_total = 0.0
    stored_baseline_total = 0.0
    stored_optimized_total = 0.0
    realized_net_total = 0.0

    for row in rows:
        outcome = evaluate_row_for_reconciliation(dict(row), note)
        outcomes.append(outcome)
        stats.scanned += 1

        if outcome.canonical_baseline_cost is not None:
            canonical_baseline_total += outcome.canonical_baseline_cost
        if outcome.canonical_optimized_cost is not None:
            canonical_optimized_total += outcome.canonical_optimized_cost
        if outcome.stored_baseline_cost is not None:
            stored_baseline_total += outcome.stored_baseline_cost
        if outcome.stored_optimized_cost is not None:
            stored_optimized_total += outcome.stored_optimized_cost
        if outcome.realized_net_uah is not None:
            realized_net_total += outcome.realized_net_uah

        if not outcome.eligible:
            stats.skipped += 1
        else:
            stats.eligible += 1
            if outcome.status == "unchanged":
                stats.unchanged += 1
            elif outcome.status == "updated":
                stats.updated += 1

        lineage_present = outcome.forecast_run_id is not None or outcome.optimization_run_id is not None
        if outcome.forecast_run_id is not None:
            history_forecast_ids.add(outcome.forecast_run_id)
        if outcome.optimization_run_id is not None:
            history_optimization_ids.add(outcome.optimization_run_id)

        if expected_forecast or expected_optimization:
            forecast_ok = not expected_forecast or outcome.forecast_run_id in expected_forecast
            optimization_ok = not expected_optimization or outcome.optimization_run_id in expected_optimization
            forecast_present = not expected_forecast or outcome.forecast_run_id is not None
            optimization_present = not expected_optimization or outcome.optimization_run_id is not None

            if lineage_present:
                lineage_available_rows += 1
            if not forecast_present or not optimization_present:
                lineage_missing_rows += 1
            elif forecast_ok and optimization_ok:
                lineage_matched_rows += 1
            else:
                lineage_mismatch_rows += 1
        elif lineage_present:
            lineage_available_rows += 1

    canonical_savings_total = canonical_baseline_total - canonical_optimized_total
    stored_savings_total = stored_baseline_total - stored_optimized_total
    if not outcomes:
        status = "no_history_rows"
        passed = True
    elif expected_forecast or expected_optimization:
        if lineage_missing_rows:
            status = "history_lineage_missing"
            passed = False
        elif lineage_mismatch_rows:
            status = "history_lineage_mismatch"
            passed = False
        else:
            status = "reconciled"
            passed = True
    else:
        status = "evaluated"
        passed = True

    metadata = {
        "status": status,
        "history_row_count": stats.scanned,
        "eligible_history_row_count": stats.eligible,
        "updated_history_row_count": stats.updated,
        "unchanged_history_row_count": stats.unchanged,
        "skipped_history_row_count": stats.skipped,
        "lineage_available_row_count": lineage_available_rows,
        "lineage_missing_row_count": lineage_missing_rows,
        "lineage_mismatch_row_count": lineage_mismatch_rows,
        "lineage_matched_row_count": lineage_matched_rows,
        "expected_forecast_run_ids": ",".join(sorted(expected_forecast)) if expected_forecast else "",
        "expected_optimization_run_ids": ",".join(sorted(expected_optimization)) if expected_optimization else "",
        "history_forecast_run_ids": ",".join(sorted(history_forecast_ids)),
        "history_optimization_run_ids": ",".join(sorted(history_optimization_ids)),
        "canonical_baseline_total_uah": round(canonical_baseline_total, 6),
        "canonical_optimized_total_uah": round(canonical_optimized_total, 6),
        "canonical_savings_total_uah": round(canonical_savings_total, 6),
        "stored_baseline_total_uah": round(stored_baseline_total, 6),
        "stored_optimized_total_uah": round(stored_optimized_total, 6),
        "stored_savings_total_uah": round(stored_savings_total, 6),
        "stored_vs_canonical_savings_delta_uah": round(canonical_savings_total - stored_savings_total, 6),
        "realized_net_total_uah": round(realized_net_total, 6),
    }

    return {
        "passed": passed,
        "stats": {
            "scanned": stats.scanned,
            "eligible": stats.eligible,
            "updated": stats.updated,
            "unchanged": stats.unchanged,
            "skipped": stats.skipped,
        },
        "metadata": metadata,
        "outcomes": outcomes,
    }


__all__ = [
    "ReconcileResult",
    "RowReconcileOutcome",
    "evaluate_reconciliation_rows",
    "evaluate_row_for_reconciliation",
    "resolve_optimization_history_db_url",
]
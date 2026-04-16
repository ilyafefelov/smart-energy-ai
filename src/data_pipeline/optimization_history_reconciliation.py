"""Reusable helpers for optimization history reconciliation flows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

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

    energy_kwh = _safe_number(row["energy_kwh"])
    unit_price = _safe_number(row["price_uah_kwh"])
    if energy_kwh is None or energy_kwh <= 0 or unit_price is None or unit_price <= 0:
        return RowReconcileOutcome(row_id=row_id, eligible=False, status="skipped")

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
        return RowReconcileOutcome(row_id=row_id, eligible=True, status="unchanged")

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
    )


__all__ = [
    "ReconcileResult",
    "RowReconcileOutcome",
    "evaluate_row_for_reconciliation",
]
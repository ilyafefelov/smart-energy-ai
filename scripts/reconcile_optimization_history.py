#!/usr/bin/env python3
"""Reconcile optimization_history economics for a bounded recent window."""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List

from sqlalchemy import create_engine, text

from src.data_pipeline.optimization_history_reconciliation import (
    evaluate_reconciliation_rows,
    evaluate_row_for_reconciliation,
    resolve_optimization_history_db_url,
)
from src.data_pipeline.optimization_economics import (
    _resolve_canonical_prices,
    _safe_number,
    compute_canonical_costs,
    determine_tariff_window,
)


def resolve_db_url() -> str:
    return resolve_optimization_history_db_url()


def reconcile(days: int, limit: int, dry_run: bool, note: str) -> Dict[str, Any]:
    engine = create_engine(resolve_db_url(), pool_pre_ping=True)
    touched_ids: List[int] = []

    select_sql = text(
        """
        SELECT
          id,
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
                    tenant_id,
                    decision_snapshot,
                    command_id,
                    schedule_id
        FROM optimization_history
        WHERE timestamp >= NOW() - make_interval(days => :days)
        ORDER BY timestamp DESC
        LIMIT :limit
        """
    )

    update_sql = text(
        """
        UPDATE optimization_history
        SET
          cost_baseline = :cost_baseline,
          cost_rl = :cost_rl,
          economics_method = 'tariff_interval',
          economics_version = 'v2',
          fallback_reason = NULL,
          is_reconciled = TRUE,
          reconciled_at = NOW(),
          reconciliation_note = :reconciliation_note,
          updated_at = NOW()
        WHERE id = :id
        """
    )

    with engine.begin() as conn:
        rows = conn.execute(select_sql, {"days": int(days), "limit": int(limit)}).mappings().all()
        evaluation = evaluate_reconciliation_rows(rows, note=note)

        for outcome in evaluation["outcomes"]:
            if not outcome.eligible:
                continue

            if outcome.status == "unchanged":
                continue

            touched_ids.append(outcome.row_id)
            if not dry_run:
                conn.execute(update_sql, outcome.update_params)

    return {
        "success": True,
        "dry_run": dry_run,
        "days": days,
        "limit": limit,
        "stats": evaluation["stats"],
        "reconciliation": evaluation["metadata"],
        "updated_ids": touched_ids[:100],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reconcile optimization_history economics for recent rows")
    parser.add_argument("--days", type=int, default=14, help="Bounded lookback window in days")
    parser.add_argument("--limit", type=int, default=5000, help="Maximum rows to inspect")
    parser.add_argument("--dry-run", action="store_true", help="Compute reconciliation without writing changes")
    parser.add_argument("--note", type=str, default="reconcile_optimization_history", help="Reconciliation note written to rows")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = reconcile(days=args.days, limit=args.limit, dry_run=args.dry_run, note=args.note)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

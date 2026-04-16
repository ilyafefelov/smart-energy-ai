#!/usr/bin/env python3
"""Reconcile optimization_history economics for a bounded recent window."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import create_engine, text

from src.data_pipeline.optimization_history_reconciliation import (
    ReconcileResult,
    evaluate_row_for_reconciliation,
)
from src.data_pipeline.optimization_economics import (
    _resolve_canonical_prices,
    _safe_number,
    compute_canonical_costs,
    determine_tariff_window,
)
def resolve_db_url() -> str:
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit

    host = os.getenv("APP_DB_HOST") or os.getenv("DB_HOST") or "localhost"
    port = os.getenv("APP_DB_PORT") or os.getenv("DB_PORT") or "5432"
    user = os.getenv("APP_DB_USER") or os.getenv("DB_USER") or "dagster"
    password = os.getenv("APP_DB_PASSWORD") or os.getenv("DB_PASSWORD") or "dagster"
    database = os.getenv("APP_DB_NAME") or os.getenv("OPTIMIZATION_DB_NAME") or "smart_energy_ai"
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def reconcile(days: int, limit: int, dry_run: bool, note: str) -> Dict[str, Any]:
    engine = create_engine(resolve_db_url(), pool_pre_ping=True)
    stats = ReconcileResult()
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
          economics_method
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

        for row in rows:
            stats.scanned += 1
            outcome = evaluate_row_for_reconciliation(row, note)
            if not outcome.eligible:
                stats.skipped += 1
                continue

            stats.eligible += 1
            if outcome.status == "unchanged":
                stats.unchanged += 1
                continue

            touched_ids.append(outcome.row_id)
            if not dry_run:
                conn.execute(update_sql, outcome.update_params)
            stats.updated += 1

    return {
        "success": True,
        "dry_run": dry_run,
        "days": days,
        "limit": limit,
        "stats": {
            "scanned": stats.scanned,
            "eligible": stats.eligible,
            "updated": stats.updated,
            "unchanged": stats.unchanged,
            "skipped": stats.skipped,
        },
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

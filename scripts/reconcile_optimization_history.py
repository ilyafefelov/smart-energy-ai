#!/usr/bin/env python3
"""Reconcile optimization_history economics for a bounded recent window."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import create_engine, text


@dataclass
class ReconcileResult:
    scanned: int = 0
    eligible: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0


def determine_tariff_window(ts: datetime) -> str:
    hour = ts.hour
    if 8 <= hour <= 20:
        return "peak"
    if hour in (7, 21):
        return "shoulder"
    return "offpeak"


def _safe_number(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def compute_canonical_costs(
    *,
    predicted_action: int,
    energy_kwh: float,
    unit_price_uah_kwh: float,
    peak_price: Optional[float],
    off_peak_price: Optional[float],
) -> Tuple[float, float]:
    baseline_cost = max(0.0, energy_kwh * unit_price_uah_kwh)

    peak = peak_price if peak_price is not None else unit_price_uah_kwh
    off_peak = off_peak_price if off_peak_price is not None else unit_price_uah_kwh

    optimized_rate = unit_price_uah_kwh
    if predicted_action == 0:  # charge
        optimized_rate = min(unit_price_uah_kwh, off_peak)
    elif predicted_action == 1:  # discharge
        spread = max(0.0, peak - off_peak)
        optimized_rate = max(0.0, unit_price_uah_kwh - spread)

    optimized_cost = max(0.0, energy_kwh * optimized_rate)
    return baseline_cost, optimized_cost


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
            row_id = int(row["id"])
            ts = row["timestamp"]
            predicted_action = int(row["predicted_action"])

            energy_kwh = _safe_number(row["energy_kwh"])
            unit_price = _safe_number(row["price_uah_kwh"])
            if energy_kwh is None or energy_kwh <= 0 or unit_price is None or unit_price <= 0:
                stats.skipped += 1
                continue

            stats.eligible += 1

            tariff_window = str(row.get("tariff_window") or "").lower()
            derived_window = determine_tariff_window(ts if isinstance(ts, datetime) else datetime.now(timezone.utc))

            peak_price = unit_price if tariff_window == "peak" else (unit_price if derived_window == "peak" else unit_price * 1.15)
            off_peak_price = unit_price if tariff_window == "offpeak" else (unit_price if derived_window == "offpeak" else unit_price * 0.85)

            baseline_cost, optimized_cost = compute_canonical_costs(
                predicted_action=predicted_action,
                energy_kwh=energy_kwh,
                unit_price_uah_kwh=unit_price,
                peak_price=peak_price,
                off_peak_price=off_peak_price,
            )

            old_baseline = _safe_number(row["cost_baseline"])
            old_rl = _safe_number(row["cost_rl"])
            unchanged = old_baseline is not None and old_rl is not None and abs(old_baseline - baseline_cost) < 1e-6 and abs(old_rl - optimized_cost) < 1e-6

            if unchanged:
                stats.unchanged += 1
                continue

            touched_ids.append(row_id)
            if not dry_run:
                conn.execute(
                    update_sql,
                    {
                        "id": row_id,
                        "cost_baseline": baseline_cost,
                        "cost_rl": optimized_cost,
                        "reconciliation_note": note,
                    },
                )
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

"""Reusable market data validation helpers.

This module owns the market-row DataFrame cleanup rules that are independent of
Dagster orchestration. Asset layers decide when to call validation and how to
handle fallback data.
"""

from __future__ import annotations

from datetime import datetime
import logging

import polars as pl


logger = logging.getLogger(__name__)


def _validate_market_data(df: pl.DataFrame) -> pl.DataFrame:
    """Validate and clean market data while preserving the existing schema contract."""
    logger.info("Validating market data: %s records", len(df))

    df = df.filter(
        (pl.col("price_eur_mwh") > 0)
        & (pl.col("price_eur_mwh") < 500)
        & (pl.col("volume_mwh") > 0)
    )

    df = df.sort("timestamp")

    df = df.with_columns(
        [
            (pl.col("price_eur_mwh") > pl.col("price_eur_mwh").mean() * 2).alias("price_spike"),
            (pl.col("volume_mwh") < 100).alias("low_volume"),
            pl.lit(datetime.now()).alias("fetched_at"),
        ]
    )

    logger.info("Market data validation complete: %s valid records", len(df))
    return df


__all__ = ["_validate_market_data"]
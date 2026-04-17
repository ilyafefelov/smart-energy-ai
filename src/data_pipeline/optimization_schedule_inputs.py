"""Helpers for shaping optimization schedule inputs."""

from __future__ import annotations

from typing import List

import polars as pl


def _extract_price_horizon(
    price_forecast: pl.DataFrame,
    *,
    horizon_mode: str = "base",
) -> List[float]:
    column_candidates = {
        "base": [
            "scenario_base_price_eur_mwh",
            "predicted_price_eur_mwh",
            "price_eur_mwh",
        ],
        "conservative": [
            "scenario_low_price_eur_mwh",
            "lower_bound_eur_mwh",
            "scenario_base_price_eur_mwh",
            "predicted_price_eur_mwh",
            "price_eur_mwh",
        ],
        "optimistic": [
            "scenario_high_price_eur_mwh",
            "upper_bound_eur_mwh",
            "scenario_base_price_eur_mwh",
            "predicted_price_eur_mwh",
            "price_eur_mwh",
        ],
    }

    for column in column_candidates.get(horizon_mode, column_candidates["base"]):
        if column in price_forecast.columns:
            return [float(value) for value in price_forecast.select(column).to_series().to_list()]
    return []


def _get_client_series(client_df: pl.DataFrame, column: str, horizon: int, fallback: float) -> List[float]:
    if column not in client_df.columns or len(client_df) == 0:
        return [fallback] * horizon

    values = client_df.select(column).to_series().to_list()
    if not values:
        return [fallback] * horizon

    tail = [float(value) for value in values[-horizon:]]
    if len(tail) < horizon:
        tail = [float(tail[-1])] * (horizon - len(tail)) + tail
    return tail


__all__ = ["_extract_price_horizon", "_get_client_series"]
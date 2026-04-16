"""Helpers for shaping optimization schedule inputs."""

from __future__ import annotations

from typing import List

import polars as pl


def _extract_price_horizon(price_forecast: pl.DataFrame) -> List[float]:
    if "predicted_price_eur_mwh" in price_forecast.columns:
        return price_forecast.select("predicted_price_eur_mwh").to_series().to_list()
    if "price_eur_mwh" in price_forecast.columns:
        return price_forecast.select("price_eur_mwh").to_series().to_list()
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
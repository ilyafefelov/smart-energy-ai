"""Helpers for shaping optimization schedule inputs."""

from __future__ import annotations

from typing import Any, List, Mapping

import polars as pl


HORIZON_COLUMN_CANDIDATES = {
    "base": [
        "scenario_base_price_eur_mwh",
        "quantile_p50_eur_mwh",
        "predicted_price_eur_mwh",
        "price_eur_mwh",
    ],
    "conservative": [
        "scenario_low_price_eur_mwh",
        "quantile_p10_eur_mwh",
        "lower_bound_eur_mwh",
        "scenario_base_price_eur_mwh",
        "quantile_p50_eur_mwh",
        "predicted_price_eur_mwh",
        "price_eur_mwh",
    ],
    "optimistic": [
        "scenario_high_price_eur_mwh",
        "quantile_p90_eur_mwh",
        "upper_bound_eur_mwh",
        "scenario_base_price_eur_mwh",
        "quantile_p50_eur_mwh",
        "predicted_price_eur_mwh",
        "price_eur_mwh",
    ],
}

PROBABILISTIC_HORIZON_COLUMNS = frozenset(
    {
        "scenario_low_price_eur_mwh",
        "scenario_base_price_eur_mwh",
        "scenario_high_price_eur_mwh",
        "quantile_p10_eur_mwh",
        "quantile_p50_eur_mwh",
        "quantile_p90_eur_mwh",
        "lower_bound_eur_mwh",
        "upper_bound_eur_mwh",
    }
)


def _coerce_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _extract_complete_price_series(
    rows: list[Mapping[str, Any]],
    column: str,
) -> List[float] | None:
    prices: List[float] = []
    for row in rows:
        value = row.get(column)
        if value is None:
            return None
        try:
            prices.append(float(value))
        except (TypeError, ValueError):
            return None
    return prices


def _resolve_price_horizon(
    price_forecast: pl.DataFrame,
    *,
    horizon_mode: str = "base",
) -> dict[str, Any]:
    rows = price_forecast.to_dicts() if len(price_forecast) else []
    if not rows:
        return {
            "prices": [],
            "source_column": None,
            "uncertainty_source": None,
            "uncertainty_contract_version": None,
        }

    first_row = rows[0]
    for column in HORIZON_COLUMN_CANDIDATES.get(horizon_mode, HORIZON_COLUMN_CANDIDATES["base"]):
        prices = _extract_complete_price_series(rows, column)
        if prices is not None:
            return {
                "prices": prices,
                "source_column": column,
                "uncertainty_source": _coerce_optional_text(first_row.get("uncertainty_source")),
                "uncertainty_contract_version": _coerce_optional_text(
                    first_row.get("uncertainty_contract_version")
                ),
            }

    return {
        "prices": [],
        "source_column": None,
        "uncertainty_source": _coerce_optional_text(first_row.get("uncertainty_source")),
        "uncertainty_contract_version": _coerce_optional_text(
            first_row.get("uncertainty_contract_version")
        ),
    }


def _extract_price_horizon(
    price_forecast: pl.DataFrame,
    *,
    horizon_mode: str = "base",
) -> List[float]:
    return list(_resolve_price_horizon(price_forecast, horizon_mode=horizon_mode)["prices"])


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


__all__ = [
    "HORIZON_COLUMN_CANDIDATES",
    "PROBABILISTIC_HORIZON_COLUMNS",
    "_extract_price_horizon",
    "_get_client_series",
    "_resolve_price_horizon",
]
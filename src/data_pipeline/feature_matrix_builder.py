"""Reusable feature matrix builder helpers."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import polars as pl

from src.engines.selection import select_feature_engine


def _to_polars(df: Any) -> pl.DataFrame:
    if isinstance(df, pl.DataFrame):
        return df
    if hasattr(df, "to_pandas"):
        return pl.from_pandas(df.to_pandas())
    return pl.from_pandas(df)


def build_feature_matrix(
    market_data: pl.DataFrame,
    weather_data: pl.DataFrame,
    client_state: pl.DataFrame,
    engine: Optional[Any] = None,
    engine_config: Optional[Dict[str, Any]] = None,
) -> Tuple[pl.DataFrame, Dict[str, Any]]:
    """Build a feature matrix and return `(features, engine_selection_metadata)`."""

    selection_meta: Dict[str, Any] = {
        "requested_engine": "auto",
        "selected_engine": "unknown",
        "fallback_reason": "",
    }

    selected_engine = engine
    if selected_engine is None:
        selected_engine, selection_meta = select_feature_engine(engine_config or {"execution_mode": "auto"})
    else:
        selection_meta["selected_engine"] = str(getattr(selected_engine, "engine_name", "resource_engine"))

    if hasattr(selected_engine, "process_features"):
        if "nvtabular" in selection_meta.get("selected_engine", ""):
            result = selected_engine.process_features(
                market_data.to_pandas(), weather_data.to_pandas(), client_state.to_pandas()
            )
        else:
            result = selected_engine.process_features(market_data, weather_data, client_state)
    else:
        merged = market_data.join(weather_data, on="timestamp", how="inner").join(
            client_state, on="timestamp", how="inner"
        )
        result = merged.with_columns(
            [
                pl.col("price_eur_mwh").shift(1).alias("price_lag_1h"),
                pl.col("price_eur_mwh").rolling_mean(window_size=24).alias("price_24h_avg"),
                (pl.col("load_actual") - pl.col("solar_gen_actual").fill_null(0.0)).alias("net_load"),
            ]
        )
        selection_meta["fallback_reason"] = "resource engine lacks process_features; used local fallback builder"

    feature_df = _to_polars(result).sort("timestamp")

    if "feature_engine" not in feature_df.columns:
        feature_df = feature_df.with_columns(
            [
                pl.lit(selection_meta.get("selected_engine", "unknown")).alias("feature_engine"),
                pl.lit(selection_meta.get("fallback_reason", "")).alias("engine_fallback_reason"),
            ]
        )

    return feature_df, selection_meta


__all__ = ["_to_polars", "build_feature_matrix"]
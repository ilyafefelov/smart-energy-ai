"""
Feature Matrix Asset.

Builds ML-ready feature tables from market, weather, and client state assets
using the selected feature engine (Polars or NVTabular).
"""

from __future__ import annotations

import polars as pl
from dagster import AssetIn, asset

from src.data_pipeline.feature_matrix_builder import build_feature_matrix


@asset(
    group_name="feature_engineering",
    description="Hybrid feature matrix from market/weather/client state assets",
    ins={
        "market_data": AssetIn("market_data_asset"),
        "weather_data": AssetIn("weather_asset"),
        "client_state": AssetIn("client_state_asset"),
    },
    metadata={
        "engine_mode": "auto",
        "output": "ml_feature_matrix",
    },
)
def feature_matrix_asset(context, market_data: pl.DataFrame, weather_data: pl.DataFrame, client_state: pl.DataFrame) -> pl.DataFrame:
    engine = getattr(context.resources, "feature_engine", None)
    feature_df, meta = build_feature_matrix(
        market_data=market_data,
        weather_data=weather_data,
        client_state=client_state,
        engine=engine,
        engine_config={"execution_mode": "auto"},
    )

    context.log.info(
        "feature_matrix built with engine=%s rows=%d fallback_reason=%s",
        meta.get("selected_engine"),
        len(feature_df),
        meta.get("fallback_reason", ""),
    )
    return feature_df

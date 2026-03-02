"""Tests for feature matrix asset helper logic."""

from datetime import datetime, timedelta

import numpy as np
import polars as pl

from src.assets.core.feature_matrix import build_feature_matrix
from src.engines.polars_engine import create_polars_engine


def _sample_frames(rows: int = 96):
    base = datetime(2026, 1, 1)
    timestamps = [base + timedelta(hours=i) for i in range(rows)]

    market_data = pl.DataFrame(
        {
            "timestamp": timestamps,
            "price_eur_mwh": [50.0 + 10.0 * np.sin(i / 6.0) for i in range(rows)],
            "price_uah_mwh": [2000.0 + 400.0 * np.sin(i / 6.0) for i in range(rows)],
            "volume_mwh": [900.0 + (i % 24) * 5.0 for i in range(rows)],
            "source": ["TEST"] * rows,
        }
    )

    weather_data = pl.DataFrame(
        {
            "timestamp": timestamps,
            "temperature": [15.0 + 5.0 * np.sin(i / 12.0) for i in range(rows)],
            "solar_radiation": [max(0.0, 600.0 * np.sin((i % 24) / 24.0 * np.pi)) for i in range(rows)],
            "wind_speed": [4.0 + (i % 6) * 0.5 for i in range(rows)],
            "cloudcover": [40.0 + (i % 10) for i in range(rows)],
            "source": ["TEST"] * rows,
        }
    )

    client_state = pl.DataFrame(
        {
            "timestamp": timestamps,
            "client_id": ["client_test"] * rows,
            "battery_soc": [40.0 + (i % 20) for i in range(rows)],
            "battery_temp": [24.0 + (i % 5) * 0.5 for i in range(rows)],
            "load_actual": [30.0 + (i % 12) for i in range(rows)],
            "solar_gen_actual": [max(0.0, 20.0 * np.sin((i % 24) / 24.0 * np.pi)) for i in range(rows)],
            "source": ["TEST"] * rows,
        }
    )

    return market_data, weather_data, client_state


def test_build_feature_matrix_polars_engine_returns_expected_columns():
    market_data, weather_data, client_state = _sample_frames()
    engine = create_polars_engine({})

    feature_df, meta = build_feature_matrix(
        market_data=market_data,
        weather_data=weather_data,
        client_state=client_state,
        engine=engine,
    )

    assert len(feature_df) > 0
    assert "timestamp" in feature_df.columns
    assert "feature_engine" in feature_df.columns
    assert "engine_fallback_reason" in feature_df.columns
    assert "price_current" in feature_df.columns
    assert meta["selected_engine"] in {"polars_cpu", "polars"}


def test_build_feature_matrix_auto_selection_smoke():
    market_data, weather_data, client_state = _sample_frames(120)

    feature_df, meta = build_feature_matrix(
        market_data=market_data,
        weather_data=weather_data,
        client_state=client_state,
        engine=None,
        engine_config={"execution_mode": "auto"},
    )

    assert len(feature_df) > 0
    assert meta["selected_engine"] in {"polars", "nvtabular"}

from datetime import datetime

import polars as pl

from src.data_pipeline.market_validation import _validate_market_data


def test_validate_market_data_filters_rows_and_adds_flags() -> None:
    frame = pl.DataFrame(
        [
            {
                "timestamp": datetime(2026, 3, 6, 1, 0),
                "price_eur_mwh": 50.0,
                "price_uah_mwh": 2000.0,
                "volume_mwh": 120.0,
                "source": "OREE",
            },
            {
                "timestamp": datetime(2026, 3, 6, 0, 0),
                "price_eur_mwh": -1.0,
                "price_uah_mwh": -40.0,
                "volume_mwh": 100.0,
                "source": "BROKEN",
            },
            {
                "timestamp": datetime(2026, 3, 6, 2, 0),
                "price_eur_mwh": 120.0,
                "price_uah_mwh": 4800.0,
                "volume_mwh": 90.0,
                "source": "OREE",
            },
        ]
    )

    result = _validate_market_data(frame)

    assert result.height == 2
    assert result["timestamp"].to_list() == [datetime(2026, 3, 6, 1, 0), datetime(2026, 3, 6, 2, 0)]
    assert "price_spike" in result.columns
    assert "low_volume" in result.columns
    assert "fetched_at" in result.columns
    assert result["low_volume"].to_list() == [False, True]
from datetime import datetime

import polars as pl

from src.data_pipeline.solar_features import _add_solar_features


def test_add_solar_features_adds_expected_columns() -> None:
    df = pl.DataFrame(
        {
            "timestamp": [datetime(2026, 6, 6, 12, 0), datetime(2026, 12, 6, 3, 0)],
            "solar_radiation": [800.0, 0.0],
            "cloudcover": [25.0, 90.0],
        }
    )

    result = _add_solar_features(df, 50.45)

    assert "effective_solar" in result.columns
    assert result["effective_solar"].to_list() == [600.0, 0.0]
    assert result["season"].to_list() == ["summer", "winter"]
    assert result["is_daylight"].to_list() == [True, False]
    assert result["sky_condition"].to_list() == ["partly_cloudy", "cloudy"]
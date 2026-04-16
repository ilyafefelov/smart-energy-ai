from datetime import datetime

import polars as pl

from src.data_pipeline.weather_validation import _validate_weather_data


def test_validate_weather_data_clips_bounds_and_adds_flags() -> None:
    frame = pl.DataFrame(
        {
            "timestamp": [datetime(2026, 3, 6, 1, 0)],
            "temperature": [100.0],
            "solar_radiation": [1500.0],
            "wind_speed": [60.0],
            "cloudcover": [120.0],
            "precipitation": [200.0],
            "pressure": [2000.0],
            "humidity": [120.0],
            "source": ["OPEN_METEO"],
        }
    )

    result = _validate_weather_data(frame)

    assert result["temperature"].item() == 50.0
    assert result["solar_radiation"].item() == 1200.0
    assert result["wind_speed"].item() == 50.0
    assert result["cloudcover"].item() == 100.0
    assert result["precipitation"].item() == 100.0
    assert result["pressure"].item() == 1050.0
    assert result["humidity"].item() == 100.0
    assert result["high_solar"].item() is True
    assert result["high_wind"].item() is True
    assert result["heavy_rain"].item() is True
    assert "fetched_at" in result.columns
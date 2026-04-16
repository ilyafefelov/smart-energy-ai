from datetime import datetime

import polars as pl

from src.data_pipeline.client_state_validation import (
    _generate_fallback_client_data,
    _validate_client_data,
)


def test_validate_client_data_clips_bounds_and_adds_flags() -> None:
    frame = pl.DataFrame(
        {
            "timestamp": [datetime(2026, 3, 6, 1, 0)],
            "client_id": ["client_1"],
            "battery_soc": [120.0],
            "battery_temp": [70.0],
            "solar_gen_actual": [1500.0],
            "load_actual": [1200.0],
            "grid_power": [1200.0],
            "system_efficiency": [2.0],
        }
    )

    result = _validate_client_data(frame)

    assert result["battery_soc"].item() == 100.0
    assert result["battery_temp"].item() == 60.0
    assert result["solar_gen_actual"].item() == 1000.0
    assert result["load_actual"].item() == 1000.0
    assert result["grid_power"].item() == 1000.0
    assert result["system_efficiency"].item() == 1.0
    assert result["low_battery_warning"].item() is False
    assert result["high_temp_warning"].item() is True
    assert result["high_grid_usage"].item() is True
    assert "generated_at" in result.columns


def test_generate_fallback_client_data_returns_24_hour_scaffold() -> None:
    rows = _generate_fallback_client_data()

    assert len(rows) == 24
    assert rows[0]["client_id"] == "fallback_client"
    assert rows[0]["source"] == "CONFIG_FALLBACK"
    assert rows[0]["state_source"] == "config_fallback"
    assert rows[0]["inverter_status"] == "IDLE"
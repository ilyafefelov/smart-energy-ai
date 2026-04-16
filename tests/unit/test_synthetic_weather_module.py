from src.data_pipeline.synthetic_weather import _generate_synthetic_weather


def test_generate_synthetic_weather_returns_expected_shape_and_ranges() -> None:
    result = _generate_synthetic_weather()

    assert len(result) == 168
    assert {"timestamp", "temperature", "solar_radiation", "wind_speed", "cloudcover", "precipitation", "pressure", "humidity", "source"}.issubset(result[0].keys())
    assert all(record["source"] == "SYNTHETIC" for record in result)
    assert all(0 <= record["cloudcover"] <= 100 for record in result)
    assert all(record["solar_radiation"] >= 0 for record in result)
    assert all(record["wind_speed"] >= 0 for record in result)
    assert all(20 <= record["humidity"] <= 100 for record in result)
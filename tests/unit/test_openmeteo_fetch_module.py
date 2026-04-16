from src.data_pipeline import openmeteo_fetch


def test_fetch_openmeteo_data_parses_hourly_payload(monkeypatch) -> None:
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "hourly": {
                    "time": ["2026-03-06T00:00", "2026-03-06T01:00"],
                    "temperature_2m": [2.0, 3.0],
                    "shortwave_radiation": [0.0, 10.0],
                    "windspeed_10m": [4.0, 5.0],
                    "cloudcover": [20.0, 30.0],
                    "precipitation": [0.0, 0.1],
                    "surface_pressure": [1010.0, 1011.0],
                    "relativehumidity_2m": [70.0, 71.0],
                }
            }

    monkeypatch.setattr(openmeteo_fetch.requests, "get", lambda *args, **kwargs: Response())

    fetched = openmeteo_fetch._fetch_openmeteo_data(50.45, 30.52, "UTC")

    assert len(fetched) == 2
    assert fetched[0]["source"] == "OPEN_METEO"
    assert fetched[1]["wind_speed"] == 5.0
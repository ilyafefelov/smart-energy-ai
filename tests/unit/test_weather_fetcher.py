from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_fetch_weather_forecast_writes_csv_on_success(monkeypatch, tmp_path, capsys) -> None:
    module = load_module("weather_fetcher_under_test", "src/weather_fetcher.py")

    output_dir = tmp_path / "projects" / "smart-energy-ai" / "data" / "raw"
    output_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    called_urls: list[str] = []

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "hourly": {
                    "time": ["2026-04-14T00:00", "2026-04-14T01:00"],
                    "temperature_2m": [12.5, 13.0],
                    "shortwave_radiation": [150.0, 200.0],
                    "cloud_cover": [20, 35],
                }
            }

    def fake_get(url: str):
        called_urls.append(url)
        return FakeResponse()

    monkeypatch.setattr(module.requests, "get", fake_get)

    module.fetch_weather_forecast(lat=49.84, lon=24.03)

    output_path = output_dir / "weather_forecast.csv"
    assert output_path.exists()

    frame = pd.read_csv(output_path)
    assert list(frame.columns) == ["timestamp", "temp", "radiation", "clouds"]
    assert frame["temp"].tolist() == [12.5, 13.0]
    assert frame["radiation"].tolist() == [150.0, 200.0]
    assert frame["clouds"].tolist() == [20, 35]
    assert called_urls == [
        "https://api.open-meteo.com/v1/forecast?latitude=49.84&longitude=24.03&hourly=temperature_2m,shortwave_radiation,cloud_cover&forecast_days=3"
    ]

    captured = capsys.readouterr()
    assert "Weather data saved to projects/smart-energy-ai/data/raw/weather_forecast.csv" in captured.out


def test_fetch_weather_forecast_prints_failure_without_writing_csv(monkeypatch, tmp_path, capsys) -> None:
    module = load_module("weather_fetcher_failure_under_test", "src/weather_fetcher.py")

    monkeypatch.chdir(tmp_path)

    class FakeResponse:
        status_code = 503

    monkeypatch.setattr(module.requests, "get", lambda url: FakeResponse())

    module.fetch_weather_forecast()

    output_path = tmp_path / "projects" / "smart-energy-ai" / "data" / "raw" / "weather_forecast.csv"
    assert not output_path.exists()

    captured = capsys.readouterr()
    assert "Failed to fetch weather data." in captured.out
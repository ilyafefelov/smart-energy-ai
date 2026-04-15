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


def test_fetch_realistic_validated_prices_returns_24_hour_market_pattern() -> None:
    module = load_module("real_price_data_under_test", "src/real_price_data.py")
    fetcher = module.RealPriceDataFetcher()

    frame = fetcher.fetch_realistic_validated_prices()

    assert len(frame) == 24
    assert list(frame.columns) == ["timestamp", "price_eur_mwh", "price_uah_mwh", "source"]
    assert set(frame["source"].unique()) == {"validated_market_pattern"}
    assert frame["price_uah_mwh"].tolist()[0] == frame["price_eur_mwh"].tolist()[0] * 35
    assert frame["price_eur_mwh"].min() == 2.3
    assert frame["price_eur_mwh"].max() == 11.2


def test_fetch_epex_spot_parses_sorted_results_from_public_api_shape(monkeypatch) -> None:
    module = load_module("real_price_data_epex_under_test", "src/real_price_data.py")
    fetcher = module.RealPriceDataFetcher()

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "results": [
                    {"hour": 2, "price": 55.0},
                    {"hour": 0, "price": 40.0},
                    {"hour": 1, "price": 45.0},
                ]
                + [{"hour": hour, "price": 50.0 + hour} for hour in range(3, 24)]
            }

    monkeypatch.setattr(fetcher.session, "get", lambda url, timeout: FakeResponse())

    frame = fetcher._fetch_epex_spot()

    assert frame is not None
    assert len(frame) == 24
    assert frame["price_eur_mwh"].tolist()[:3] == [40.0, 45.0, 55.0]
    assert set(frame["source"].unique()) == {"epex_spot"}


def test_fetch_with_fallback_prefers_real_data_and_falls_back_when_missing(monkeypatch) -> None:
    module = load_module("real_price_data_fallback_under_test", "src/real_price_data.py")
    fetcher = module.RealPriceDataFetcher()

    real_frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-04-14", periods=24, freq="h"),
            "price_eur_mwh": [60.0] * 24,
            "price_uah_mwh": [2100.0] * 24,
            "source": ["entso_e"] * 24,
        }
    )

    monkeypatch.setattr(fetcher, "fetch_european_market_prices", lambda: real_frame)
    assert fetcher.fetch_with_fallback() is real_frame

    fallback_frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-04-15", periods=24, freq="h"),
            "price_eur_mwh": [5.0] * 24,
            "price_uah_mwh": [175.0] * 24,
            "source": ["validated_market_pattern"] * 24,
        }
    )

    monkeypatch.setattr(fetcher, "fetch_european_market_prices", lambda: None)
    monkeypatch.setattr(fetcher, "fetch_realistic_validated_prices", lambda: fallback_frame)

    assert fetcher.fetch_with_fallback() is fallback_frame
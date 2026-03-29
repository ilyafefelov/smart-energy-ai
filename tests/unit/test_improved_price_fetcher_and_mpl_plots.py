from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(module_name: str, relative_path: str, injected_modules: dict[str, object] | None = None):
    module_path = REPO_ROOT / relative_path
    injected_modules = injected_modules or {}
    previous = {}

    for name, module in injected_modules.items():
        previous[name] = sys.modules.get(name)
        sys.modules[name] = module

    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        for name, old in previous.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old


def sample_prices(source: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-03-06", periods=24, freq="h"),
            "price_eur_mwh": [5.0 + hour for hour in range(24)],
            "price_uah_mwh": [(5.0 + hour) * 35 for hour in range(24)],
            "source": [source] * 24,
        }
    )


def test_improved_price_fetcher_priority_chain_and_fallback(monkeypatch) -> None:
    src_pkg = types.ModuleType("src")
    src_pkg.__path__ = [str(REPO_ROOT / "src")]
    playwright_mod = types.ModuleType("src.oree_playwright_scraper")
    real_price_mod = types.ModuleType("src.real_price_data")

    class OREEPlaywrightScraper:
        def fetch_prices(self):
            return sample_prices("oree_playwright")

    class RealPriceDataFetcher:
        def fetch_european_market_prices(self):
            return sample_prices("european_market")

    playwright_mod.OREEPlaywrightScraper = OREEPlaywrightScraper
    real_price_mod.RealPriceDataFetcher = RealPriceDataFetcher
    src_pkg.oree_playwright_scraper = playwright_mod
    src_pkg.real_price_data = real_price_mod

    module = load_module(
        "improved_price_fetcher_under_test",
        "src/improved_price_fetcher.py",
        injected_modules={
            "src": src_pkg,
            "src.oree_playwright_scraper": playwright_mod,
            "src.real_price_data": real_price_mod,
        },
    )
    monkeypatch.setitem(sys.modules, "src", src_pkg)
    monkeypatch.setitem(sys.modules, "src.oree_playwright_scraper", playwright_mod)
    monkeypatch.setitem(sys.modules, "src.real_price_data", real_price_mod)

    fetcher = module.ImprovedRealPriceDataFetcher()
    playwright_df = fetcher.fetch_oree_playwright()
    european_df = fetcher.fetch_european_api()
    fallback_df = fetcher.fetch_validated_pattern()

    assert len(playwright_df) == 24
    assert playwright_df["source"].iloc[0] == "oree_playwright"
    assert len(european_df) == 24
    assert european_df["source"].iloc[0] == "european_market"
    assert len(fallback_df) == 24
    assert fallback_df["source"].iloc[0] == "validated_market_pattern"

    monkeypatch.setattr(fetcher, "fetch_oree_playwright", lambda: None)
    monkeypatch.setattr(fetcher, "fetch_european_api", lambda: sample_prices("european_market"))
    chosen = fetcher.fetch_prices_with_ukraine_priority()
    assert chosen["source"].iloc[0] == "european_market"

    monkeypatch.setattr(fetcher, "fetch_oree_playwright", lambda: None)
    monkeypatch.setattr(fetcher, "fetch_european_api", lambda: None)
    chosen = fetcher.fetch_prices_with_ukraine_priority()
    assert chosen["source"].iloc[0] == "validated_market_pattern"


def test_generate_plots_mpl_writes_expected_images(monkeypatch, tmp_path) -> None:
    module = load_module("generate_plots_mpl_under_test", "src/generate_plots_mpl.py")
    frame = pd.DataFrame(
        {
            "Hour": list(range(24)),
            "Price": [100.0] * 24,
            "Solar": [10.0] * 24,
            "SOC": [50.0] * 24,
        }
    )
    saved = []

    monkeypatch.setattr(module.pd, "read_csv", lambda path: frame)
    monkeypatch.setattr(module.plt, "savefig", lambda path: saved.append(path))
    monkeypatch.chdir(tmp_path)

    module.generate_plots()

    assert saved == [
        "projects/smart-energy-ai/plots/price_solar_mpl.png",
        "projects/smart-energy-ai/plots/battery_soc_mpl.png",
    ]
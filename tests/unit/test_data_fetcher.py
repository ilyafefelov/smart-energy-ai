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


def test_fetch_sample_energy_data_writes_24_hour_dummy_frame(monkeypatch, tmp_path) -> None:
    module = load_module("data_fetcher_under_test", "src/data_fetcher.py")

    output_dir = tmp_path / "projects" / "smart-energy-ai" / "data" / "raw"
    output_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    data = module.fetch_sample_energy_data()

    assert len(data) == 24
    assert list(data.columns) == ["timestamp", "price_eur_mwh", "solar_gen_kw", "source"]
    assert set(data["source"].unique()) == {"sample_data_dummy"}
    assert (output_dir / "sample_energy_data.csv").exists()


def test_fetch_real_energy_data_uses_ingesters_and_fallback_prices(monkeypatch) -> None:
    src_pkg = types.ModuleType("src")
    src_pkg.__path__ = [str(REPO_ROOT / "src")]
    pipeline_pkg = types.ModuleType("src.data_pipeline")
    pipeline_pkg.__path__ = [str(REPO_ROOT / "src" / "data_pipeline")]
    src_pkg.data_pipeline = pipeline_pkg

    weather_mod = types.ModuleType("src.data_pipeline.ingest_weather")
    price_mod = types.ModuleType("src.data_pipeline.ingest_prices")

    class WeatherIngester:
        def fetch_weather(self):
            return {"hourly": True}

        def parse_weather_data(self, payload):
            assert payload == {"hourly": True}
            return pd.DataFrame({"temperature": [1.0, 2.0], "solar_gen_kw": [5.0, 7.0]})

    class PriceIngester:
        def __init__(self, frame=None):
            self.frame = frame

        def fetch_oree_prices(self):
            return self.frame

    weather_mod.WeatherIngester = WeatherIngester
    price_mod.PriceIngester = lambda: PriceIngester(pd.DataFrame({"price_eur_mwh": [100.0, 120.0], "source": ["oree", "oree"]}))

    module = load_module(
        "data_fetcher_real_under_test",
        "src/data_fetcher.py",
        injected_modules={
            "src": src_pkg,
            "src.data_pipeline": pipeline_pkg,
            "src.data_pipeline.ingest_weather": weather_mod,
            "src.data_pipeline.ingest_prices": price_mod,
        },
    )
    monkeypatch.setitem(sys.modules, "src", src_pkg)
    monkeypatch.setitem(sys.modules, "src.data_pipeline", pipeline_pkg)
    monkeypatch.setitem(sys.modules, "src.data_pipeline.ingest_weather", weather_mod)
    monkeypatch.setitem(sys.modules, "src.data_pipeline.ingest_prices", price_mod)

    real_df = module.fetch_real_energy_data()
    assert len(real_df) == 2
    assert real_df["price_eur_mwh"].tolist() == [100.0, 120.0]

    price_mod.PriceIngester = lambda: PriceIngester(pd.DataFrame())
    fallback_df = module.fetch_real_energy_data()
    assert len(fallback_df) == 24
    assert set(fallback_df["source"].unique()) == {"realistic_fallback"}
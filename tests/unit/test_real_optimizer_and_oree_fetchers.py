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


def test_real_data_optimizer_fetches_and_optimizes_with_stubbed_ingesters(monkeypatch) -> None:
    src_pkg = types.ModuleType("src")
    src_pkg.__path__ = [str(REPO_ROOT / "src")]
    pipeline_pkg = types.ModuleType("src.data_pipeline")
    pipeline_pkg.__path__ = [str(REPO_ROOT / "src" / "data_pipeline")]
    src_pkg.data_pipeline = pipeline_pkg

    weather_mod = types.ModuleType("src.data_pipeline.ingest_weather")
    price_mod = types.ModuleType("src.data_pipeline.ingest_prices")

    class WeatherIngester:
        def fetch_weather(self):
            return {"ok": True}

        def parse_weather_data(self, payload):
            assert payload == {"ok": True}
            return pd.DataFrame(
                {
                    "solar_radiation": [500.0] * 24,
                    "cloudcover": [20.0] * 24,
                }
            )

    class PriceIngester:
        def __init__(self, frame=None):
            self.frame = frame

        def fetch_oree_prices(self):
            return self.frame

    weather_mod.WeatherIngester = WeatherIngester
    price_mod.PriceIngester = lambda: PriceIngester(
        pd.DataFrame(
            {
                "price_eur_mwh": [5.0 + hour for hour in range(24)],
                "price_uah_mwh": [(5.0 + hour) * 35 for hour in range(24)],
            }
        )
    )

    module = load_module(
        "optimizer_real_under_test",
        "src/optimizer_real.py",
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
    monkeypatch.setattr(module.np.random, "normal", lambda mean, std: 0.0)

    optimizer = module.RealDataOptimizer()
    prices_eur, solar_kw, factory_load = optimizer.fetch_real_data()
    assert len(prices_eur) == 24
    assert len(solar_kw) == 24
    assert len(factory_load) == 24

    captured = {}
    monkeypatch.setattr(optimizer, "_save_results", lambda df, scenario: captured.setdefault(scenario, df.copy()))
    winter = optimizer.run_optimization("Winter")
    blackout = optimizer.run_optimization("Blackout")

    assert len(winter) == 24
    assert len(blackout) == 24
    assert blackout["Action"].str.contains("OFF-GRID").any()
    assert "Winter" in captured and "Blackout" in captured

    fallback_prices = optimizer._get_realistic_prices(24)
    assert len(fallback_prices) == 24
    action, soc_delta = optimizer._make_optimization_decision(0, 9.0, 0.0, 60.0, 60.0, 50.0, "Normal")
    assert action == "DISCHARGE BATTERY"
    assert soc_delta < 0


def test_oree_real_price_fetcher_parses_html_table(monkeypatch, capsys) -> None:
    module = load_module("oree_real_prices_under_test", "src/oree_real_prices.py")
    fetcher = module.OREERealPriceFetcher()

    html = "<table>" + "".join(
        f"<tr><td>{hour}:00</td><td>{20 + hour} EUR/MWh</td></tr>" for hour in range(24)
    ) + "</table>"

    class Response:
        status_code = 200
        text = html
        content = html.encode("utf-8")

        def raise_for_status(self):
            return None

    monkeypatch.setattr(fetcher.session, "get", lambda url, timeout=20: Response())
    prices = fetcher.fetch_oree_prices()

    assert len(prices) == 24
    assert prices["source"].iloc[0] == "oree_real"

    monkeypatch.setattr(module, "OREERealPriceFetcher", lambda: types.SimpleNamespace(fetch_oree_prices=lambda: prices))
    module.test_oree()
    output = capsys.readouterr().out
    assert "GOT REAL OREE PRICES" in output


def test_oree_selenium_scraper_uses_stubbed_driver_and_prints_setup(capsys, monkeypatch) -> None:
    module = load_module("oree_selenium_scraper_under_test", "src/oree_selenium_scraper.py")

    class FakeChromeDriver:
        def __init__(self, options=None):
            self.page_source = "<table>" + "".join(
                f"<tr><td>{hour}:00</td><td>{30 + hour}</td></tr>" for hour in range(24)
            ) + "</table>"

        def get(self, url):
            return None

        def quit(self):
            return None

    class FakeWebDriverWait:
        def __init__(self, driver, timeout):
            self.driver = driver

        def until(self, predicate):
            return True

    class FakeOptions:
        def __init__(self):
            self.args = []

        def add_argument(self, value):
            self.args.append(value)

    selenium_mod = types.ModuleType("selenium")
    webdriver_mod = types.ModuleType("selenium.webdriver")
    webdriver_mod.Chrome = FakeChromeDriver
    common_by_mod = types.ModuleType("selenium.webdriver.common.by")
    common_by_mod.By = types.SimpleNamespace(TAG_NAME="table")
    support_pkg_mod = types.ModuleType("selenium.webdriver.support")
    support_ui_mod = types.ModuleType("selenium.webdriver.support.ui")
    support_ui_mod.WebDriverWait = FakeWebDriverWait
    support_ec_mod = types.ModuleType("selenium.webdriver.support.expected_conditions")
    support_ec_mod.presence_of_all_elements_located = lambda locator: True
    support_pkg_mod.ui = support_ui_mod
    support_pkg_mod.expected_conditions = support_ec_mod
    chrome_pkg_mod = types.ModuleType("selenium.webdriver.chrome")
    chrome_options_mod = types.ModuleType("selenium.webdriver.chrome.options")
    chrome_options_mod.Options = FakeOptions
    chrome_pkg_mod.options = chrome_options_mod

    monkeypatch.setitem(sys.modules, "selenium", selenium_mod)
    monkeypatch.setitem(sys.modules, "selenium.webdriver", webdriver_mod)
    monkeypatch.setitem(sys.modules, "selenium.webdriver.common.by", common_by_mod)
    monkeypatch.setitem(sys.modules, "selenium.webdriver.support", support_pkg_mod)
    monkeypatch.setitem(sys.modules, "selenium.webdriver.support.ui", support_ui_mod)
    monkeypatch.setitem(sys.modules, "selenium.webdriver.support.expected_conditions", support_ec_mod)
    monkeypatch.setitem(sys.modules, "selenium.webdriver.chrome", chrome_pkg_mod)
    monkeypatch.setitem(sys.modules, "selenium.webdriver.chrome.options", chrome_options_mod)

    prices = module.scrape_oree_with_selenium()
    assert len(prices) == 24
    assert prices["source"].iloc[0] == "oree_selenium"

    module.setup_selenium_instructions()
    output = capsys.readouterr().out
    assert "SETUP SELENIUM FOR OREE SCRAPING" in output
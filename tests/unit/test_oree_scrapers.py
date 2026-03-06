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


def test_oree_effective_scraper_cache_process_and_today_selection(monkeypatch) -> None:
    module = load_module("oree_effective_scraper_under_test", "src/oree_effective_scraper.py")

    cache = module.OREEPriceCache(cache_duration_minutes=5)
    cache.set("cached")
    assert cache.is_valid() is True
    assert cache.get() == "cached"

    scraper = module.OREEEffectiveScraper(use_cache=True)
    processed = scraper._process_oree_data(
        [{"date": "05.03.2026", "prices": [3500.0 + hour for hour in range(24)]}]
    )
    assert len(processed) == 24
    assert processed["source"].iloc[0] == "oree_playwright"

    yesterday = pd.Timestamp.now().normalize() - pd.Timedelta(days=1)
    yesterday_str = yesterday.strftime("%d.%m.%Y")
    yesterday_df = pd.DataFrame(
        {
            "timestamp": pd.date_range(yesterday, periods=24, freq="h"),
            "hour": list(range(24)),
            "price_uah_mwh": [3500.0 + hour for hour in range(24)],
            "price_eur_mwh": [(3500.0 + hour) / 35 for hour in range(24)],
            "date": [yesterday_str] * 24,
            "source": ["oree_playwright"] * 24,
        }
    )
    calls = {"count": 0}

    def fake_scrape():
        calls["count"] += 1
        return yesterday_df

    monkeypatch.setattr(scraper, "scrape_with_playwright", fake_scrape)
    first = scraper.fetch_today_prices()
    second = scraper.fetch_today_prices()

    assert len(first) == 24
    assert first["date"].iloc[0] == yesterday_str
    assert calls["count"] == 1
    assert second.equals(first)


def test_oree_playwright_scraper_table_xls_and_fetch_paths(monkeypatch, tmp_path, capsys) -> None:
    module = load_module("oree_playwright_scraper_under_test", "src/oree_playwright_scraper.py")
    scraper = module.OREEPlaywrightScraper()

    xls_df = pd.DataFrame({"Hour": list(range(24)), "Price": [10.0 + hour for hour in range(24)]})
    parsed_xls = scraper._parse_xls_prices(xls_df)
    assert len(parsed_xls) == 24
    assert parsed_xls["source"].iloc[0] == "oree_xls"

    class FakeCell:
        def __init__(self, text: str):
            self._text = text

        def text_content(self):
            return self._text

    class FakeRow:
        def __init__(self, texts):
            self.texts = texts

        def query_selector_all(self, selector):
            return [FakeCell(text) for text in self.texts]

    class FakeTable:
        def __init__(self):
            self.rows = [FakeRow([f"{hour}:00", f"{20 + hour}"]) for hour in range(24)]

        def query_selector_all(self, selector):
            return self.rows

    parsed_table = scraper._extract_prices_from_table(FakeTable())
    assert len(parsed_table) == 24
    assert parsed_table["source"].iloc[0] == "oree_table"

    class FakeResponse:
        status_code = 200
        content = b"xls-bytes"

    requests_mod = types.ModuleType("requests")
    requests_mod.get = lambda url, timeout=30: FakeResponse()
    monkeypatch.setitem(sys.modules, "requests", requests_mod)
    monkeypatch.setattr(module.pd, "read_excel", lambda path: xls_df)
    downloaded = scraper._download_and_parse_xls("https://example.com/file.xls")
    assert len(downloaded) == 24

    class FakeLink:
        def __init__(self, href: str | None, text: str):
            self._href = href
            self._text = text

        def get_attribute(self, name):
            return self._href if name == "href" else None

        def text_content(self):
            return self._text

    class FakePage:
        def goto(self, url, wait_until=None):
            return None

        def wait_for_selector(self, selector, timeout=0):
            return None

        def query_selector_all(self, selector):
            if selector == "a":
                return [FakeLink(None, "nope")]
            if selector == "table":
                return [FakeTable()]
            return []

    class FakeBrowser:
        def new_page(self):
            return FakePage()

        def close(self):
            return None

    class FakePlaywrightContext:
        def __enter__(self):
            return types.SimpleNamespace(chromium=types.SimpleNamespace(launch=lambda: FakeBrowser()))

        def __exit__(self, exc_type, exc, tb):
            return False

    sync_api_mod = types.ModuleType("playwright.sync_api")
    sync_api_mod.sync_playwright = lambda: FakePlaywrightContext()
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api_mod)

    fetched = scraper.fetch_prices()
    assert len(fetched) == 24
    assert fetched["source"].iloc[0] == "oree_table"

    module.setup_playwright_instructions()
    output = capsys.readouterr().out
    assert "SETUP PLAYWRIGHT FOR OREE PRICE SCRAPING" in output
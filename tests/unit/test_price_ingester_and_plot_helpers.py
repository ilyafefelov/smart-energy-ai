from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_enhanced_price_ingester_parses_sources_and_fallbacks(monkeypatch) -> None:
    module = load_module("enhanced_price_ingester_under_test", "src/enhanced_price_ingester.py")
    ingester = module.EnhancedPriceIngester()

    oree_html = "<table>" + "".join(
        f"<tr><td>{hour}:00</td><td>{10 + hour}.0 EUR/MWh</td></tr>" for hour in range(24)
    ) + "</table>"
    oree_df = ingester._extract_oree_table(module.BeautifulSoup(oree_html, "html.parser"))
    assert len(oree_df) == 24
    assert oree_df["source"].iloc[0] == "oree"

    generic_table = module.BeautifulSoup(
        "<table>" + "".join(f"<tr><td>{hour}</td><td>{20 + hour}</td></tr>" for hour in range(24)) + "</table>",
        "html.parser",
    ).find("table")
    generic_df = ingester._extract_price_from_table(generic_table)
    assert len(generic_df) == 24
    assert generic_df["source"].iloc[0] == "oree_table"

    pxe_data = {"prices": [{"hour": hour, "price": 30 + hour} for hour in range(1, 25)]}
    pxe_df = ingester._parse_pxe_data(pxe_data)
    assert len(pxe_df) == 24
    assert pxe_df["source"].iloc[0] == "pxe"

    hist_html = (
        "<table>"
        "<tr><td>2026-03-01</td><td>120.5</td></tr>"
        "<tr><td>2026-03-02</td><td>125.0</td></tr>"
        "</table>"
    )
    hist_df = ingester._parse_ukrstat_prices(hist_html)
    assert len(hist_df) == 2
    assert hist_df["source"].iloc[0] == "ukrstat_historical"

    monkeypatch.setattr(ingester, "fetch_oree_prices", lambda: None)
    monkeypatch.setattr(ingester, "fetch_pxe_prices", lambda: None)
    fallback_df = ingester.fetch_prices()
    assert len(fallback_df) == 24
    assert set(fallback_df["source"].unique()) == {"realistic_pattern"}

    monkeypatch.setattr(ingester, "fetch_historical_prices", lambda: hist_df)
    assert len(ingester.fetch_historical_for_training()) == 2


def test_business_plot_helper_saves_expected_plot(monkeypatch, tmp_path) -> None:
    module = load_module("generate_business_plot_under_test", "src/generate_business_plot.py")
    frame = pd.DataFrame(
        {
            "Hour": list(range(24)),
            "Solar": [20.0] * 24,
            "Action": ["BUY FROM GRID", "SELL TO GRID", "DISCHARGE BATTERY", "CHARGE FROM GRID"] * 6,
        }
    )
    saved = []

    monkeypatch.setattr(module.pd, "read_csv", lambda path: frame)
    monkeypatch.setattr(module.plt, "savefig", lambda path: saved.append(path))
    monkeypatch.chdir(tmp_path)

    module.generate_business_plots()

    assert saved == ["projects/smart-energy-ai/plots/energy_balance_business.png"]


def test_static_plot_helper_writes_two_images(monkeypatch, tmp_path) -> None:
    module = load_module("generate_plots_under_test", "src/generate_plots.py")
    frame = pd.DataFrame(
        {
            "Hour": list(range(24)),
            "Price": [100.0] * 24,
            "Solar": [10.0] * 24,
            "SOC": [50.0] * 24,
        }
    )
    written = []

    class FakeFigure:
        def add_trace(self, trace):
            return None

        def update_layout(self, **kwargs):
            return None

        def write_image(self, path):
            written.append(path)

    monkeypatch.setattr(module.pd, "read_csv", lambda path: frame)
    monkeypatch.setattr(module.go, "Figure", lambda: FakeFigure())
    monkeypatch.setattr(module.go, "Scatter", lambda **kwargs: kwargs)
    monkeypatch.setattr(module.go, "Bar", lambda **kwargs: kwargs)
    monkeypatch.setattr(module.px, "area", lambda *args, **kwargs: FakeFigure())
    monkeypatch.chdir(tmp_path)

    module.generate_static_plots()

    assert written == [
        "projects/smart-energy-ai/plots/price_solar.png",
        "projects/smart-energy-ai/plots/battery_soc.png",
    ]
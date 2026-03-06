from __future__ import annotations

import importlib.util
import sys
import types
from datetime import datetime
from pathlib import Path

import pandas as pd
import polars as pl


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


def build_dagster_module():
    module = types.ModuleType("dagster")
    module.asset = lambda *args, **kwargs: (lambda func: func)
    module.AssetIn = lambda asset_key: {"asset_key": asset_key}
    return module


def test_asset_factory_generates_isolated_client_assets(monkeypatch) -> None:
    module = load_module(
        "asset_factory_under_test",
        "src/assets/multi_tenant/asset_factory.py",
        injected_modules={"dagster": build_dagster_module()},
    )

    assert module._normalize_tenant_id(" Plant A / West ") == "plant_a_west"
    tenant = module._build_tenant_descriptor({"id": "Plant A / West"})
    assert tenant["tenant_namespace"] == "tenant/plant_a_west"

    client_config = {
        "id": "Plant A / West",
        "name": "Plant A",
        "type": "industrial",
        "location": {"lat": 50.45, "lon": 30.52},
        "energy_system": {
            "battery_capacity_kwh": 120.0,
            "solar_capacity_kw": 80.0,
            "peak_load_kw": 100.0,
            "base_load_kw": 40.0,
            "load_profile": "industrial",
        },
        "economic_params": {"electricity_tariff": 1.3, "feed_in_tariff": 0.8},
    }
    market_data = pl.DataFrame(
        {
            "timestamp": [datetime(2026, 3, 6, 8, 0), datetime(2026, 3, 6, 20, 0)],
            "price_eur_mwh": [100.0, 120.0],
            "client_id": ["shared", "shared"],
        }
    )
    weather_data = pl.DataFrame(
        {
            "timestamp": [datetime(2026, 3, 6, 8, 0), datetime(2026, 3, 6, 20, 0)],
            "solar_radiation": [500.0, 100.0],
            "tenant_id": ["shared", "shared"],
        }
    )

    client_asset = module.create_client_specific_asset(client_config)
    result = client_asset(market_data, weather_data)

    assert set(result["client_id"].unique().to_list()) == {"Plant A / West"}
    assert set(result["tenant_id"].unique().to_list()) == {"plant_a_west"}
    assert "solar_generation_kw" in result.columns
    assert result["load_kw"].to_list()[0] > result["peak_load_kw"].to_list()[0] * 0.4

    duplicate_configs = [client_config, {**client_config, "id": "plant-a-west", "name": "Duplicate"}]
    monkeypatch.setattr(module, "load_customer_configurations", lambda: duplicate_configs)
    generated = module.generate_client_assets()
    assert len(generated) == 1

    analytics = module.multi_client_analytics()
    assert len(analytics) == 2
    assert "storage_class" in analytics.columns


def test_baseline_calculator_compares_naive_and_optimized_costs(tmp_path, monkeypatch) -> None:
    module = load_module("baseline_calculator_under_test", "src/baseline_calculator.py")

    csv_path = tmp_path / "opt_normal.csv"
    pd.DataFrame(
        {
            "Hour": [0, 1, 2, 3],
            "Price": [5.0, 6.0, 7.0, 8.0],
            "Solar": [20.0, 60.0, 55.0, 10.0],
            "Action": ["BUY FROM GRID", "SELL TO GRID", "STORE SOLAR", "DISCHARGE BATTERY"],
            "SOC": [50.0, 60.0, 65.0, 55.0],
        }
    ).to_csv(csv_path, index=False)

    calculator = module.BaselineCalculator(facility_load_kw=50.0)
    comparison = calculator.compare_strategies(str(csv_path))

    assert comparison["baseline"]["strategy"] == "naive_no_battery"
    assert comparison["optimized"]["strategy"] == "optimized_with_battery"
    assert comparison["comparison"]["baseline_cost_uah"] > 0
    assert "roi_analysis" in comparison["comparison"]

    monkeypatch.setattr(module, "calculate_real_baseline", lambda scenario: comparison)
    report = module.generate_baseline_report()
    assert "REAL BASELINE ANALYSIS REPORT" in report
    assert "NORMAL SCENARIO" in report


def test_comprehensive_scraper_builds_excel_network_and_report_paths(monkeypatch) -> None:
    module = load_module("comprehensive_scraper_under_test", "src/comprehensive_energy_scraper.py")
    scraper = module.UkrainianEnergyDataScraper()

    february_df = pd.DataFrame(
        {
            "Дата": pd.to_datetime(["2026-02-01", "2026-02-02"]),
            "Base, грн/МВт.год": [5000.0, 5200.0],
            "Peak, грн/МВт.год": [6500.0, 6700.0],
            "OffPeak, грн/МВт.год": [4500.0, 4600.0],
            "Мінімальна ціна, грн/МВт.год": [4200.0, 4300.0],
            "Максимальна ціна, грн/МВт.год": [7200.0, 7400.0],
            "Середньозважена ціна, грн/МВт.год": [5800.0, 6000.0],
        }
    )

    def fake_read_excel(path):
        if str(path).endswith("indexes_02.2026.xls"):
            return february_df.copy()
        raise ValueError("corrupted january file")

    monkeypatch.setattr(module.pd, "read_excel", fake_read_excel)
    excel_results = scraper.analyze_local_excel_files()
    assert excel_results["february_2026"]["records"] == 2
    assert "error" in excel_results["january_2026"]

    class Response:
        def __init__(self, html: str):
            self.content = html.encode("utf-8")

        def raise_for_status(self):
            return None

    oree_html = "<html><table><tr>" + "".join(f"<th>{index}</th>" for index in range(12)) + "</tr><tr>" + "".join(f"<td>{index}</td>" for index in range(12)) + "</tr></table></html>"
    ua_html = "<html><title>UA Energy</title><section class='market-data'></section><a href='report.xlsx'>Download</a></html>"
    responses = [Response(oree_html), Response(ua_html)]
    monkeypatch.setattr(scraper.session, "get", lambda url: responses.pop(0))

    oree = scraper.scrape_oree_hourly_prices()
    balance = scraper.scrape_uaenergy_balance_data()
    dataset = scraper.create_ml_ready_dataset(excel_results)
    report = scraper.generate_comprehensive_report()

    assert oree["status"] == "success"
    assert oree["rows_extracted"] == 2
    assert balance["page_title"] == "UA Energy"
    assert balance["data_links"][0]["url"] == "report.xlsx"
    assert not dataset.empty
    assert "price_volatility" in dataset.columns
    assert "COMPREHENSIVE UKRAINIAN ENERGY DATA ANALYSIS" in report
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(module_name: str, relative_path: str, injected_modules: dict[str, object]):
    module_path = REPO_ROOT / relative_path
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


def load_analyzer_module():
    matplotlib_mod = types.ModuleType("matplotlib")
    pyplot_mod = types.ModuleType("matplotlib.pyplot")
    seaborn_mod = types.ModuleType("seaborn")
    matplotlib_mod.pyplot = pyplot_mod
    return load_module(
        "ukraine_stats_under_test",
        "src/ukraine_stats_analyzer.py",
        injected_modules={
            "matplotlib": matplotlib_mod,
            "matplotlib.pyplot": pyplot_mod,
            "seaborn": seaborn_mod,
        },
    )


def write_sample_csv(tmp_path: Path) -> Path:
    frame = pd.DataFrame(
        [
            {
                "Тип палива/енергії": "ELECTR",
                "Період": "2018-S1",
                "Показник": "AVG_ELECTR_PRICE_WO_VAT",
                "Показник.1": "Середня ціна грн за 1 кВт·год",
                "Тип споживача": "HOUSEHOLD",
                "Тип споживача.1": "Домогосподарства",
                "Значення cпостереження": "1,50",
            },
            {
                "Тип палива/енергії": "ELECTR",
                "Період": "2018-S2",
                "Показник": "AVG_ELECTR_PRICE_WO_VAT",
                "Показник.1": "Середня ціна грн за 1 кВт·год",
                "Тип споживача": "HOUSEHOLD",
                "Тип споживача.1": "Домогосподарства",
                "Значення cпостереження": "1,80",
            },
            {
                "Тип палива/енергії": "ELECTR",
                "Період": "2019-S1",
                "Показник": "AVG_ELECTR_PRICE_WO_VAT",
                "Показник.1": "Середня ціна грн за 1 кВт·год",
                "Тип споживача": "HOUSEHOLD",
                "Тип споживача.1": "Домогосподарства",
                "Значення cпостереження": "2,00",
            },
            {
                "Тип палива/енергії": "GAS",
                "Період": "2019-S1",
                "Показник": "AVG_GAS_PRICE",
                "Показник.1": "Середня ціна грн",
                "Тип споживача": "HOUSEHOLD",
                "Тип споживача.1": "Домогосподарства",
                "Значення cпостереження": "9,99",
            },
            {
                "Тип палива/енергії": "ELECTR",
                "Період": "2019-S2",
                "Показник": "PRICE_TOTAL",
                "Показник.1": "Загальна ціна грн за 1 кВт·год",
                "Тип споживача": "BUSINESS",
                "Тип споживача.1": "Бізнес",
                "Значення cпостереження": "bad-value",
            },
        ]
    )
    csv_path = tmp_path / "ukraine_stats.csv"
    frame.to_csv(csv_path, index=False)
    return csv_path


def test_load_process_trends_and_ml_features_from_sample_csv(tmp_path) -> None:
    module = load_analyzer_module()
    csv_path = write_sample_csv(tmp_path)
    analyzer = module.UkraineElectricityPriceAnalyzer(str(csv_path))

    summary = analyzer.load_and_process_data()
    trends = analyzer.get_price_trends()
    ml_features = analyzer.create_ml_features()

    assert summary["total_records"] == 5
    assert summary["electricity_records"] == 4
    assert summary["processed_records"] == 3
    assert summary["consumer_types"] == ["HOUSEHOLD"]

    household_trend = trends["HOUSEHOLD"]
    assert household_trend["values"] == [1.5, 1.8, 2.0]
    assert household_trend["unit"] == "UAH/kWh"
    assert household_trend["trend_analysis"]["total_change_pct"] > 0

    assert len(ml_features) == 3
    assert "price_lag1" in ml_features.columns
    assert ml_features.iloc[1]["price_lag1"] == 1.5
    assert ml_features.iloc[2]["price_lag2"] == 1.5
    assert ml_features.iloc[2]["price_rolling_mean_3"] == (1.5 + 1.8 + 2.0) / 3


def test_analyze_ukrainian_electricity_data_returns_report_payload(tmp_path, capsys) -> None:
    module = load_analyzer_module()
    csv_path = write_sample_csv(tmp_path)

    payload = module.analyze_ukrainian_electricity_data(str(csv_path))

    assert set(payload.keys()) == {"summary", "trends", "ml_features", "analyzer", "recommendations"}
    assert payload["summary"]["processed_records"] == 3
    assert payload["recommendations"]["data_quality"] == "HIGH - Official government statistics"
    assert not payload["ml_features"].empty

    captured = capsys.readouterr()
    assert "АНАЛІЗ ДЕРЖАВНОЇ СТАТИСТИКИ ЦІН НА ЕЛЕКТРОЕНЕРГІЮ" in captured.out
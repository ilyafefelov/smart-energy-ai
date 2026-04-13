from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_script_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_combine_datasets_creates_enriched_dataframe(tmp_path: Path, monkeypatch) -> None:
    module = load_script_module("scripts.combine_datasets_under_test", "scripts/combine_datasets.py")
    processed_dir = tmp_path / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    oree_data = pd.DataFrame(
        {
            "Дата": ["01.02.2026", "02.02.2026"],
            "Середньозважена ціна, грн/МВт.год": [4100.0, 4300.0],
            "Base, грн/МВт.год": [3800.0, 3900.0],
            "Peak, грн/МВт.год": [4500.0, 4700.0],
            "OffPeak, грн/МВт.год": [3300.0, 3400.0],
            "Мінімальна ціна, грн/МВт.год": [3000.0, 3200.0],
            "Максимальна ціна, грн/МВт.год": [5000.0, 5100.0],
        }
    )
    sssu_data = pd.DataFrame({"timestamp": ["2026-01-01T00:00:00"], "target": [1.0]})
    oree_data.to_csv(processed_dir / "hourly_prices_02_2026.csv", index=False)
    sssu_data.to_csv(processed_dir / "ukraine_energy_ml_dataset_2026.csv", index=False)

    monkeypatch.setattr(module, "Path", lambda value: tmp_path / value)

    result = module.create_combined_dataset()

    assert list(result["Month"]) == [2, 2]
    assert list(result["Year"]) == [2026, 2026]
    assert result["Середньозважена ціна, грн/МВт.год"].mean() == 4200.0


def test_fetch_oree_helpers_parse_table_and_cli_payload(monkeypatch, capsys) -> None:
    module = load_script_module("scripts.fetch_oree_data_view_under_test", "scripts/fetch_oree_data_view.py")
    cells = "".join(f"<td>{1000 + hour * 10},0</td>" for hour in range(24))
    html = f"<table><tr><td>01.02.2026</td>{cells}</tr></table>"

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {"content": html}

    monkeypatch.setattr(module.requests, "post", lambda *args, **kwargs: Response())

    prices = module.fetch_prices_for_date("01.02.2026")

    assert module.parse_decimal("1 234,5") == 1234.5
    assert module.parse_decimal("0") is None
    assert prices["0"] == 1.0
    assert prices["23"] == 1.23

    monkeypatch.setattr(sys, "argv", ["fetch_oree_data_view.py", "--date", "01.02.2026"])
    exit_code = module.main()
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["hours"]["12"] == 1.12


def test_fetch_oree_main_reports_errors(monkeypatch, capsys) -> None:
    module = load_script_module("scripts.fetch_oree_data_view_error_under_test", "scripts/fetch_oree_data_view.py")
    monkeypatch.setattr(module, "fetch_prices_for_date", lambda _date: (_ for _ in ()).throw(RuntimeError("network down")))
    monkeypatch.setattr(sys, "argv", ["fetch_oree_data_view.py", "--date", "01.02.2026"])

    exit_code = module.main()
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload == {"success": False, "error": "network down", "hours": {}}



from __future__ import annotations

import asyncio
import importlib.util
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


def test_generate_nuxt_structure_prints_tree() -> None:
    module = load_script_module("scripts.generate_nuxt_structure_under_test", "scripts/generate_nuxt_structure.py")

    rendered = module.print_structure({"root": {"file.txt": "desc"}, "items": ["one", "two"]})

    assert "📁 root/" in rendered
    assert "📝 file.txt" in rendered
    assert "• one" in rendered
    assert "• two" in rendered


def test_oree_parser_supports_html_save_and_merge(tmp_path: Path, monkeypatch) -> None:
    module = load_script_module("scripts.parse_oree_indices_under_test", "scripts/parse_oree_indices.py")
    parser = module.OREEPriceParser(raw_dir=tmp_path / "raw", processed_dir=tmp_path / "processed")
    parser.raw_dir.mkdir(parents=True, exist_ok=True)

    html_file = parser.raw_dir / "indexes_01.2026.xls"
    html_file.write_text("<table><tr><th>a</th></tr><tr><td>1</td></tr></table>", encoding="utf-8")
    monkeypatch.setattr(module.pd, "read_html", lambda path: [pd.DataFrame({"col": [1, 2]})])

    parsed = parser.try_parse_file(str(html_file))

    assert list(parsed["col"]) == [1, 2]

    jan_df = pd.DataFrame({" value ": [10]})
    feb_df = pd.DataFrame({"value": [20]})
    monkeypatch.setattr(parser, "try_parse_file", lambda filepath: jan_df if "01.2026" in filepath else feb_df)
    (parser.raw_dir / "indexes_02.2026.xls").write_text("placeholder", encoding="utf-8")

    assert parser.parse_and_save("01") is True
    assert parser.parse_and_save("02") is True
    merged = parser.merge_months()

    assert list((parser.processed_dir / "hourly_prices_01_2026.csv").read_text(encoding="utf-8").splitlines())[0] == "value"
    assert len(merged) == 2
    assert parser.parse_and_save("03") is False


def test_demo_complete_mlops_orchestrates_summary(monkeypatch, capsys) -> None:
    module = load_script_module("scripts.demo_complete_mlops_system_under_test", "scripts/demo_complete_mlops_system.py")

    monkeypatch.setattr(module, "demonstrate_phase1_model_registry", lambda: asyncio.sleep(0, result=True))
    monkeypatch.setattr(module, "demonstrate_phase2_battery_physics", lambda: asyncio.sleep(0, result=True))
    monkeypatch.setattr(module, "demonstrate_phase3_mlops_infrastructure", lambda: asyncio.sleep(0, result=False))
    monkeypatch.setattr(module, "demonstrate_phase4_serving_api", lambda: asyncio.sleep(0, result=True))
    monkeypatch.setattr(module, "demonstrate_phase5_renewable_forecasting", lambda: asyncio.sleep(0, result=True))
    monkeypatch.setattr(module, "demonstrate_complete_system_integration", lambda: asyncio.sleep(0, result=True))

    success = asyncio.run(module.main())
    output = capsys.readouterr().out

    assert success is False
    assert "DEMONSTRATION RESULTS" in output
    assert "Phase 3: ❌ FAILED" in output
    assert "Some phases failed" in output


def test_demo_complete_mlops_phase_helpers_cover_success_and_failure(monkeypatch, capsys) -> None:
    module = load_script_module("scripts.demo_complete_mlops_phase_under_test", "scripts/demo_complete_mlops_system.py")

    success = asyncio.run(module.demonstrate_phase4_serving_api())
    success_output = capsys.readouterr().out
    assert success is True
    assert "Health check passed" in success_output

    monkeypatch.setattr(module, "print_error", lambda message: print(message))
    monkeypatch.setitem(sys.modules, "energy_ml.mlops", SimpleNamespace(get_mlops_system=lambda: (_ for _ in ()).throw(RuntimeError("offline"))))

    failure = asyncio.run(module.demonstrate_complete_system_integration())
    failure_output = capsys.readouterr().out

    assert failure is False
    assert "offline" in failure_output


def test_demo_complete_mlops_mission_summary_prints_specs(capsys) -> None:
    module = load_script_module("scripts.demo_complete_mlops_summary_under_test", "scripts/demo_complete_mlops_system.py")

    module.print_mission_summary()
    output = capsys.readouterr().out

    assert "MISSION ACHIEVEMENTS" in output
    assert "TECHNICAL SPECIFICATIONS MET" in output
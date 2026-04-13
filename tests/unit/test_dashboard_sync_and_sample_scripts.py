from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_script_module(module_name: str, relative_path: str, db_module=None, models_module=None):
    module_path = REPO_ROOT / relative_path

    if db_module is not None or models_module is not None:
        src_package = types.ModuleType("src")
        src_package.__path__ = [str(REPO_ROOT / "src")]
        sys.modules["src"] = src_package
    if db_module is not None:
        sys.modules["src.db"] = db_module
    if models_module is not None:
        sys.modules["src.models"] = models_module

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def build_db_module(session):
    module = types.ModuleType("src.db")
    module.SessionLocal = lambda: session
    return module


def build_models_module():
    module = types.ModuleType("src.models")

    class WeatherForecast:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class MarketPrice:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    module.WeatherForecast = WeatherForecast
    module.MarketPrice = MarketPrice
    return module


def test_notion_sync_collects_commits_markdown_and_summary(tmp_path: Path, monkeypatch) -> None:
    module = load_script_module("scripts.notion_sync_under_test", "scripts/notion_sync.py")

    git_result = SimpleNamespace(
        returncode=0,
        stdout="abc123|feat: add sync|Illya|2026-03-06|extra details\ndef456|fix: test|Illya|2026-03-05|\n",
    )
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: git_result)

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "README.md").write_text("hello\nworld", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")

    commits = module.NotionSync.get_recent_commits(count=2)
    markdown = module.NotionSync.get_markdown_files(tmp_path)
    summary = module.NotionSync.generate_notion_content(commits, markdown)

    assert commits[0]["hash"] == "abc123"
    assert commits[0]["body"] == "extra details"
    assert [entry["name"] for entry in markdown] == ["README.md"]
    assert "Recent Commits" in summary
    assert "Documentation Files" in summary


def test_notion_sync_summary_writes_output_file(tmp_path: Path, monkeypatch, capsys) -> None:
    module = load_script_module("scripts.notion_sync_summary_under_test", "scripts/notion_sync.py")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module.NotionSync, "get_recent_commits", staticmethod(lambda count=15: [{"hash": "abc", "message": "msg", "date": "2026-03-06", "body": "", "author": "Illya"}]))
    monkeypatch.setattr(module.NotionSync, "get_markdown_files", staticmethod(lambda directory=".": [{"name": "README.md", "content": "body", "path": "README.md"}]))
    monkeypatch.setattr(module, "datetime", type("FixedDateTime", (), {"now": staticmethod(lambda: SimpleNamespace(strftime=lambda fmt: "2026-03-06_182700"))}))

    summary = module.NotionSync.sync_summary(project_name="smart energy")
    output = capsys.readouterr().out
    output_file = tmp_path / "notion_sync_2026-03-06_182700.txt"

    assert output_file.exists()
    assert "Recent Commits" in summary
    assert "Sync summary saved" in output
    assert "smart energy" in output_file.read_text(encoding="utf-8")


def test_sample_data_generator_builds_realistic_frames_and_main(monkeypatch, capsys) -> None:
    session = SimpleNamespace(add=lambda record: None, commit=lambda: None, rollback=lambda: None, close=lambda: None)
    module = load_script_module(
        "scripts.generate_sample_data_under_test",
        "scripts/generate_sample_data.py",
        db_module=build_db_module(session),
        models_module=build_models_module(),
    )

    monkeypatch.setattr(module.np.random, "normal", lambda mean, std: 0.0)
    monkeypatch.setattr(module.np, "clip", lambda value, low, high: max(low, min(high, value)))
    start_date = module.datetime(2026, 1, 1, 0, 0, 0)

    generator = module.SampleDataGenerator()
    weather_df = generator.generate_weather_data(days=1, start_date=start_date)
    price_df = generator.generate_price_data(days=1, start_date=start_date)

    assert len(weather_df) == 24
    assert len(price_df) == 24
    assert set(["temperature", "solar_radiation", "humidity"]).issubset(weather_df.columns)
    assert set(["price_eur_mwh", "price_uah_mwh", "source"]).issubset(price_df.columns)
    assert set(price_df["source"]) == {"sample_generated"}

    class FakeGenerator:
        def generate_and_store(self, days=7):
            return pd.DataFrame({"value": [1, 2, 3]}), pd.DataFrame({"value": [4, 5, 6]})

    monkeypatch.setattr(module, "SampleDataGenerator", FakeGenerator)
    module.main()
    output = capsys.readouterr().out

    assert "Sample Data Generated" in output
    assert "Weather: 3 rows" in output
    assert "Prices: 3 rows" in output


def test_sample_data_generator_store_methods_handle_commit_and_rollback(monkeypatch) -> None:
    added_records = []
    state = {"rolled_back": False, "committed": False}

    class Session:
        def add(self, record):
            added_records.append(record)

        def commit(self):
            state["committed"] = True

        def rollback(self):
            state["rolled_back"] = True

        def close(self):
            return None

    session = Session()
    module = load_script_module(
        "scripts.generate_sample_data_store_under_test",
        "scripts/generate_sample_data.py",
        db_module=build_db_module(session),
        models_module=build_models_module(),
    )

    generator = module.SampleDataGenerator()
    weather_df = pd.DataFrame(
        [{"timestamp": 1, "temperature": 2, "solar_radiation": 3, "cloudcover": 4, "wind_speed": 5, "humidity": 6}]
    )
    price_df = pd.DataFrame(
        [{"timestamp": 1, "price_eur_mwh": 2, "price_uah_mwh": 70, "min_price": 1.9, "max_price": 2.1, "source": "sample_generated"}]
    )

    weather_count = generator.store_weather_data(weather_df)
    price_count = generator.store_price_data(price_df)

    assert weather_count == 1
    assert price_count == 1
    assert state["committed"] is True
    assert len(added_records) == 2

    class BrokenSession(Session):
        def add(self, record):
            raise RuntimeError("db offline")

    broken_generator = module.SampleDataGenerator()
    broken_generator.session = BrokenSession()

    assert broken_generator.store_weather_data(weather_df) == 0
    assert state["rolled_back"] is True
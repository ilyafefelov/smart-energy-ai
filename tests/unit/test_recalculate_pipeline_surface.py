from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "recalculate_pipeline.py"


def load_recalculate_pipeline():
    spec = importlib.util.spec_from_file_location("recalculate_pipeline_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_load_user_config_bootstraps_from_seed(tmp_path: Path) -> None:
    module = load_recalculate_pipeline()
    module.CONFIG_DIR = tmp_path / "energy_ml" / "configs"
    module.SEED_CONFIG_FILE = module.CONFIG_DIR / "templates" / "user_config.seed.json"

    seed_config = {
        "battery_type": "VRFB",
        "battery_capacity_kwh": 240,
        "load_profile_type": "custom",
    }
    module.SEED_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    module.SEED_CONFIG_FILE.write_text(json.dumps(seed_config), encoding="utf-8")

    loaded = module.load_user_config()

    assert loaded == seed_config
    assert json.loads((module.CONFIG_DIR / "user_config.json").read_text(encoding="utf-8")) == seed_config


def test_load_user_config_falls_back_on_invalid_json(tmp_path: Path) -> None:
    module = load_recalculate_pipeline()
    module.CONFIG_DIR = tmp_path / "energy_ml" / "configs"
    module.SEED_CONFIG_FILE = module.CONFIG_DIR / "templates" / "user_config.seed.json"
    module.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (module.CONFIG_DIR / "user_config.json").write_text("{invalid", encoding="utf-8")

    loaded = module.load_user_config()

    assert loaded["battery_type"] == "LFP"
    assert loaded["optimization_strategy"] == "balanced"


def test_save_results_and_cache_persists_dashboard_artifacts(tmp_path: Path, monkeypatch) -> None:
    module = load_recalculate_pipeline()
    module.PROJECT_ROOT = tmp_path
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(module.random, "randint", lambda start, end: start + 5)
    monkeypatch.setattr(module.random, "uniform", lambda start, end: (start + end) / 2)

    config = {
        "battery_capacity_kwh": 20,
        "battery_cycles_max": 6000,
        "load_peak_kw": 18,
        "ml_retrain_frequency_days": 3,
    }
    model_results = {"ensemble_accuracy": 0.84}
    validation_results = {"historical_daily_profit_uah": 123.45}

    results_size, cache_size = module.save_results_and_cache(config, model_results, validation_results)

    results = json.loads((tmp_path / "energy_ml" / "outputs" / "latest_ml_results.json").read_text(encoding="utf-8"))
    cache = json.loads((tmp_path / "energy_ml" / "outputs" / "analytics_cache.json").read_text(encoding="utf-8"))

    assert results_size > 0
    assert cache_size > 0
    assert results["config_used"]["battery_capacity_kwh"] == 20
    assert results["validation_metrics"]["historical_daily_profit_uah"] == 123.45
    assert cache["cost_analytics"]["daily_arbitrage_profit"] == 123.45
    assert cache["ml_metrics"]["model_accuracy"] == 0.84
    assert cache["battery_metrics"]["cycles_remaining"] == 5945


def test_main_reports_successful_recalculation(tmp_path: Path, monkeypatch) -> None:
    module = load_recalculate_pipeline()
    module.PROJECT_ROOT = tmp_path
    module.CONFIG_DIR = tmp_path / "energy_ml" / "configs"
    module.STATUS_FILE = module.CONFIG_DIR / "recalculation_status.json"

    statuses = []
    monkeypatch.setattr(module, "update_status", lambda status, progress=0, stage="", details="", **kwargs: statuses.append({
        "status": status,
        "progress": progress,
        "stage": stage,
        "details": details,
        **kwargs,
    }))
    monkeypatch.setattr(module, "load_user_config", lambda: {"battery_type": "LFP", "load_profile_type": "standard"})
    monkeypatch.setattr(module, "simulate_data_loading", lambda config: {"data_quality_score": 0.96})
    monkeypatch.setattr(module, "simulate_feature_engineering", lambda config, data_quality: {"total_features": 48})
    monkeypatch.setattr(module, "simulate_model_training", lambda config, features: {"ensemble_accuracy": 0.86})
    monkeypatch.setattr(module, "simulate_validation_and_backtesting", lambda config, model_results: {"historical_daily_profit_uah": 145.0})
    monkeypatch.setattr(module, "save_results_and_cache", lambda config, model_results, validation_results: (4096, 1024))
    monkeypatch.setattr(module.time, "time", lambda: 100.0)

    time_values = iter([100.0, 108.4])
    monkeypatch.setattr(module.time, "time", lambda: next(time_values))

    exit_code = module.main()

    assert exit_code == 0
    assert statuses[0]["stage"] == "Initializing"
    assert statuses[-1]["status"] == "complete"
    assert statuses[-1]["results"]["accuracy"] == 0.86
    assert statuses[-1]["results"]["features_engineered"] == 48


def test_main_reports_failure_details(tmp_path: Path, monkeypatch) -> None:
    module = load_recalculate_pipeline()
    module.PROJECT_ROOT = tmp_path
    module.CONFIG_DIR = tmp_path / "energy_ml" / "configs"
    module.STATUS_FILE = module.CONFIG_DIR / "recalculation_status.json"

    statuses = []
    monkeypatch.setattr(module, "update_status", lambda status, progress=0, stage="", details="", **kwargs: statuses.append({
        "status": status,
        "progress": progress,
        "stage": stage,
        "details": details,
        **kwargs,
    }))
    monkeypatch.setattr(module, "load_user_config", lambda: (_ for _ in ()).throw(RuntimeError("config missing")))
    monkeypatch.setattr(module.time, "time", lambda: 10.0)

    exit_code = module.main()

    assert exit_code == 1
    assert statuses[0]["stage"] == "Initializing"
    assert statuses[-1]["status"] == "failed"
    assert "config missing" in statuses[-1]["details"]
    assert "RuntimeError: config missing" in statuses[-1]["error_details"]
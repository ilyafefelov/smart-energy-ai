from __future__ import annotations

import builtins
import importlib.util
import io
import json
import sys
from pathlib import Path

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


def test_train_model_config_paths_and_main_flows(tmp_path: Path, monkeypatch, capsys) -> None:
    module = load_script_module("scripts.train_model_under_test", "scripts/train_model.py")
    retraining_dir = tmp_path / "retraining"
    metrics_file = retraining_dir / "job-1-metrics.json"
    progress_file = retraining_dir / "job-1.json"

    monkeypatch.setattr(module, "resolve_retraining_dir", lambda tenant_id: retraining_dir)
    monkeypatch.setenv("ENERGY_ML_CONFIG_DIR", str(tmp_path / "tenant-config"))

    progress_path = module.get_progress_file("tenant-a", "job-1")
    metrics_path = module.get_metrics_file("tenant-a", "job-1")
    assert progress_path == progress_file
    assert metrics_path == metrics_file

    module.update_progress("tenant-a", "job-1", 15, "Loading")
    payload = json.loads(progress_file.read_text(encoding="utf-8"))
    assert payload["progress"] == 15
    assert payload["status"] == "running"
    assert module.parse_overrides('{"epochs": 8}') == {"epochs": 8}
    assert module.parse_overrides("bad-json") == {}

    config_root = tmp_path / "tenant-config"
    config_root.mkdir(parents=True, exist_ok=True)
    (config_root / "user_config.json").write_text(json.dumps({"battery_capacity_kwh": 10}), encoding="utf-8")
    merged = module.merge_config_overrides("tenant-a", {"epochs": 4, "battery_capacity_kwh": 20})
    assert merged["epochs"] == 4
    assert merged["battery_capacity_kwh"] == 20

    statuses = []
    monkeypatch.setattr(module, "update_progress", lambda tenant_id, job_id, progress, message, status="running": statuses.append((progress, message, status)))
    monkeypatch.setattr(module, "merge_config_overrides", lambda tenant_id, overrides: {"epochs": overrides.get("epochs"), "optimization_strategy": "balanced"})
    monkeypatch.setattr(module, "load_training_data", lambda tenant_id, job_id: 100)
    monkeypatch.setattr(module, "preprocess_data", lambda tenant_id, job_id, samples: samples)
    monkeypatch.setattr(module, "train_model", lambda tenant_id, job_id, samples, epochs: statuses.append((80, f"epochs={epochs}", "running")))
    monkeypatch.setattr(module, "optimize_parameters", lambda tenant_id, job_id: None)
    monkeypatch.setattr(module, "save_model", lambda tenant_id, job_id: tmp_path / "model.json")
    monkeypatch.setattr(module, "save_metrics", lambda tenant_id, job_id, epochs, used_config: {"improvementPercent": 7.5})
    monkeypatch.setattr(sys, "argv", ["train_model.py", "--job-id", "job-1", "--tenant-id", "tenant-a", "--config", '{"epochs": 120}'])

    try:
        module.main()
    except SystemExit as exc:
        assert exc.code == 0
    output = capsys.readouterr().out
    assert "TRAINING COMPLETE" in output
    assert any(item[0] == 100 and item[2] == "completed" for item in statuses)
    assert any(item[1] == "epochs=100" for item in statuses)

    monkeypatch.setattr(module, "load_training_data", lambda tenant_id, job_id: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(sys, "argv", ["train_model.py", "--job-id", "job-2", "--tenant-id", "tenant-a"])
    try:
        module.main()
    except SystemExit as exc:
        assert exc.code == 1
    failure_output = capsys.readouterr().out
    assert "ERROR: boom" in failure_output


def test_validate_deployment_success_and_failure(monkeypatch, capsys) -> None:
    module = load_script_module("scripts.validate_deployment_under_test", "scripts/validate_deployment.py")

    files = {
        "C:\\Users\\ilyaf\\clawd\\projects\\smart-energy-ai\\energy_ml\\assets\\ml_star_optimized_pipeline.py": "energy_ml_star_pipeline SmartEnergyAIPredictor",
        "C:\\Users\\ilyaf\\clawd\\projects\\smart-energy-ai\\energy_ml\\energy_ml\\definitions.py": "ml_star_optimized_pipeline ml_star_job",
        "C:\\Users\\ilyaf\\clawd\\projects\\smart-energy-ai\\DEPLOYMENT_GUIDE.md": "guide",
        "C:\\Users\\ilyaf\\clawd\\projects\\smart-energy-ai\\ML_STAR_ACTION_PLAN.md": "plan",
    }
    dirs = {
        "C:\\Users\\ilyaf\\clawd\\projects\\smart-energy-ai\\energy_ml\\assets": True,
        "C:\\Users\\ilyaf\\clawd\\projects\\smart-energy-ai\\energy_ml\\energy_ml": True,
        "C:\\Users\\ilyaf\\clawd\\projects\\smart-energy-ai\\models": True,
    }

    monkeypatch.setattr(module.os.path, "exists", lambda path: path in files or dirs.get(path, False))

    def fake_open(path, mode="r", *args, **kwargs):
        return io.StringIO(files[path])

    monkeypatch.setattr(builtins, "open", fake_open)

    assert module.validate_deployment() is True
    output = capsys.readouterr().out
    assert "DEPLOYMENT VALIDATION" in output
    assert "All files in place" in output

    monkeypatch.setattr(module.os.path, "exists", lambda path: False)
    assert module.validate_deployment() is False


def test_validate_ppo_oree_load_costs_and_pipeline(tmp_path: Path, monkeypatch, capsys) -> None:
    module = load_script_module("scripts.validate_ppo_oree_under_test", "scripts/validate_ppo_oree.py")
    validator = module.PriceDataValidator()
    validator.processed_dir = tmp_path / "processed"
    validator.results_dir = tmp_path / "results"
    validator.processed_dir.mkdir(parents=True, exist_ok=True)
    validator.results_dir.mkdir(parents=True, exist_ok=True)

    prices = pd.DataFrame(
        {
            "Дата": ["01.02.2026", "02.02.2026"],
            "Середньозважена ціна, грн/МВт.год": [4000.0, 5000.0],
            "Мінімальна ціна, грн/МВт.год": [3000.0, 3200.0],
            "Максимальна ціна, грн/МВт.год": [6000.0, 6500.0],
            "Base, грн/МВт.год": [4200.0, 4300.0],
            "Peak, грн/МВт.год": [4800.0, 5000.0],
            "OffPeak, грн/МВт.год": [3600.0, 3500.0],
        }
    )
    prices.to_csv(validator.processed_dir / "hourly_prices_02_2026.csv", index=False)

    loaded = validator.load_oree_data()
    assert len(loaded) == 2

    baseline_df, baseline_total = validator.calculate_baseline_cost(loaded.copy())
    optimized = validator.calculate_optimized_cost(loaded.copy(), optimization_factor=0.5)

    assert len(baseline_df) == 2
    assert baseline_total == 10800.0
    assert optimized["optimized_total"] == 5400.0
    assert optimized["daily_savings"] == 2700.0

    validator.analyze_price_patterns(loaded.copy())
    analysis_output = capsys.readouterr().out
    assert "PRICE PATTERN ANALYSIS" in analysis_output
    assert "BATTERY ARBITRAGE OPPORTUNITY" in analysis_output

    monkeypatch.setattr(validator, "analyze_price_patterns", lambda prices_df: None)
    monkeypatch.setattr(
        module,
        "datetime",
        type(
            "FixedDateTime",
            (),
            {"now": staticmethod(lambda: __import__("datetime").datetime(2026, 3, 6, 12, 0, 0))},
        ),
    )
    assert validator.validate_ml_integration() is True
    result_file = validator.results_dir / "ppo_validation_feb2026.json"
    assert result_file.exists()
    result_payload = json.loads(result_file.read_text(encoding="utf-8"))
    assert result_payload["days_analyzed"] == 7
    assert result_payload["improvement_pct"] == 57.9


def test_validate_ppo_oree_handles_missing_price_file(tmp_path: Path, capsys) -> None:
    module = load_script_module("scripts.validate_ppo_oree_missing_under_test", "scripts/validate_ppo_oree.py")
    validator = module.PriceDataValidator()
    validator.processed_dir = tmp_path / "processed"
    validator.results_dir = tmp_path / "results"

    assert validator.load_oree_data() is None
    assert validator.validate_ml_integration() is False
    output = capsys.readouterr().out
    assert "Price file not found" in output
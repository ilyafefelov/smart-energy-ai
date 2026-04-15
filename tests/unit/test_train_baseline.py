from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import numpy as np
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


class FakeModel:
    def __init__(self, *args, **kwargs) -> None:
        self.feature_importances_ = np.array([0.4, 0.35, 0.25])
        self.training_targets = None

    def fit(self, features, targets) -> None:
        self.training_targets = list(targets)

    def predict(self, features):
        count = len(features)
        if self.training_targets is not None and count == len(self.training_targets):
            return np.array(self.training_targets)
        return np.zeros(count)


def test_train_baseline_reports_fallback_when_price_ingester_returns_empty_frame(monkeypatch, tmp_path, capsys) -> None:
    src_pkg = types.ModuleType("src")
    src_pkg.__path__ = [str(REPO_ROOT / "src")]
    pipeline_pkg = types.ModuleType("src.data_pipeline")
    pipeline_pkg.__path__ = [str(REPO_ROOT / "src" / "data_pipeline")]
    src_pkg.data_pipeline = pipeline_pkg

    price_mod = types.ModuleType("src.data_pipeline.ingest_prices")

    class PriceIngester:
        def fetch_oree_prices(self):
            return pd.DataFrame()

    price_mod.PriceIngester = PriceIngester

    module = load_module(
        "train_baseline_under_test",
        "src/train_baseline.py",
        injected_modules={
            "src": src_pkg,
            "src.data_pipeline": pipeline_pkg,
            "src.data_pipeline.ingest_prices": price_mod,
        },
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(sys.modules, "src", src_pkg)
    monkeypatch.setitem(sys.modules, "src.data_pipeline", pipeline_pkg)
    monkeypatch.setitem(sys.modules, "src.data_pipeline.ingest_prices", price_mod)
    monkeypatch.setattr(module, "RandomForestRegressor", FakeModel)
    monkeypatch.setattr(module.joblib, "dump", lambda model, path: Path(path).write_text("model"))
    monkeypatch.setattr(module, "mean_absolute_error", lambda actual, predicted: 0.0)

    model = module.train_baseline_with_real_data()

    assert isinstance(model, FakeModel)
    assert (tmp_path / "projects" / "smart-energy-ai" / "models" / "baseline_price_model.joblib").exists()

    captured = capsys.readouterr()
    assert "using realistic fallback for demo" in captured.out.lower()
    assert "Data source: Realistic fallback" in captured.out


def test_train_baseline_delegates_to_real_data_version(monkeypatch) -> None:
    module = load_module("train_baseline_legacy_under_test", "src/train_baseline.py")
    sentinel = object()
    monkeypatch.setattr(module, "train_baseline_with_real_data", lambda: sentinel)

    assert module.train_baseline() is sentinel
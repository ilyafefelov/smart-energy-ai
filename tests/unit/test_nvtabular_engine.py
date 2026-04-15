from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_constructor_and_factory_fail_cleanly_without_gpu(monkeypatch) -> None:
    module = load_module("nvtabular_engine_under_test", "src/engines/nvtabular_engine.py")
    monkeypatch.setattr(module, "HAS_GPU", False)
    monkeypatch.setattr(module, "GPU_IMPORT_ERROR", "missing cuda")

    with pytest.raises(ImportError, match="missing cuda"):
        module.NVTabularEngine()

    assert module.is_nvtabular_available() is False
    assert module.create_nvtabular_engine() is None


def test_non_gpu_engine_info_and_guard_paths_are_stable(monkeypatch) -> None:
    module = load_module("nvtabular_engine_info_under_test", "src/engines/nvtabular_engine.py")
    monkeypatch.setattr(module, "HAS_GPU", False)
    monkeypatch.setattr(module, "GPU_IMPORT_ERROR", "gpu unavailable")

    engine = module.NVTabularEngine.__new__(module.NVTabularEngine)
    engine.engine_name = "nvtabular_gpu"

    frame = pd.DataFrame({"value": [1, 2]})
    assert engine._ensure_cudf(frame) is frame

    info = engine.get_engine_info()
    assert info == {
        "engine_name": "nvtabular_gpu",
        "status": "unavailable",
        "error": "gpu unavailable",
        "backend": "GPU (NVIDIA/NVTabular)",
        "available": False,
    }

    with pytest.raises(RuntimeError, match="GPU processing not available"):
        engine.process_features(frame, frame, frame)

    with pytest.raises(RuntimeError, match="GPU benchmarking not available"):
        engine.benchmark_performance(data_size_mb=1.0)
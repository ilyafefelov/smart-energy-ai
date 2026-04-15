from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_nested_energy_ml_placeholder_packages_are_removed() -> None:
    assert not (ROOT / "energy_ml/energy_ml/jobs").exists()
    assert not (ROOT / "energy_ml/energy_ml/resources").exists()
    assert not (ROOT / "energy_ml/energy_ml/io_managers").exists()


def test_energy_ml_readme_documents_top_level_runtime_surface() -> None:
    readme = (ROOT / "energy_ml/README.md").read_text(encoding="utf-8")

    assert "├── energy_ml/                 # Main package" not in readme
    assert "energy_ml/\n├── control/" in readme
    assert "PipelineOrchestrator" in readme


def test_energy_ml_subproject_pyproject_uses_real_compat_entrypoint() -> None:
    pyproject = (ROOT / "energy_ml/pyproject.toml").read_text(encoding="utf-8")

    assert 'smart_energy_ml.definitions' not in pyproject
    assert 'module_name = "energy_ml.definitions"' in pyproject
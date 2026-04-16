from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_nested_asset_package_is_removed() -> None:
    legacy_files = [
        "energy_ml/energy_ml/__init__.py",
        "energy_ml/energy_ml/config.py",
        "energy_ml/energy_ml/definitions.py",
        "energy_ml/energy_ml/utils.py",
        "energy_ml/energy_ml/utils_support.py",
        "energy_ml/energy_ml/outputs/templates/control_status.seed.json",
        "energy_ml/energy_ml/assets/__init__.py",
        "energy_ml/energy_ml/assets/data_sources.py",
        "energy_ml/energy_ml/assets/data_source_support.py",
        "energy_ml/energy_ml/assets/features.py",
        "energy_ml/energy_ml/assets/feature_support.py",
        "energy_ml/energy_ml/assets/models.py",
        "energy_ml/energy_ml/assets/model_support.py",
        "energy_ml/energy_ml/assets/recommendations.py",
        "energy_ml/energy_ml/assets/recommendation_support.py",
        "energy_ml/energy_ml/assets/training.py",
        "energy_ml/energy_ml/assets/training_support.py",
    ]

    assert all(not (ROOT / relative_path).exists() for relative_path in legacy_files)
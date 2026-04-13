from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_serving_api_surface_is_removed() -> None:
    legacy_files = [
        "energy_ml/mlops/serving_api.py",
        "energy_ml/mlops/serving_api_support.py",
    ]

    assert all(not (ROOT / relative_path).exists() for relative_path in legacy_files)
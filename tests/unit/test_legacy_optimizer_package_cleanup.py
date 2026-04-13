from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_optimizer_package_marker_is_removed() -> None:
    assert not (ROOT / "energy_ml/optimizer/__init__.py").exists()
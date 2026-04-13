from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_ml_star_optimizer_module_is_removed() -> None:
    assert not (ROOT / "energy_ml/optimizer/ml_star_optimizer.py").exists()
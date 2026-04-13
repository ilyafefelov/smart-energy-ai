from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_optimizer_dagster_integration_is_removed() -> None:
    assert not (ROOT / "energy_ml/optimizer/dagster_integration.py").exists()
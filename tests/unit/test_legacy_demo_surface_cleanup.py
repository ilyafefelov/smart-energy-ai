from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_demo_entrypoints_are_removed() -> None:
    assert not (ROOT / "energy_ml/demo_complete_system.py").exists()
    assert not (ROOT / "energy_ml/demo_complete_system_support.py").exists()
    assert not (ROOT / "scripts/demo_complete_mlops_system.py").exists()
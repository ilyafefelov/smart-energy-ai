from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_multi_objective_module_is_removed() -> None:
    assert not (ROOT / "energy_ml/optimizer/multi_objective.py").exists()
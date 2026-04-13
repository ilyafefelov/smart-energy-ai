from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_optimizer_run_optimization_script_is_removed() -> None:
    assert not (ROOT / "energy_ml/optimizer/run_optimization.py").exists()
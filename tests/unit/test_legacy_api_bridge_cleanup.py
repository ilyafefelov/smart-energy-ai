from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_api_bridge_script_is_removed() -> None:
    assert not (ROOT / "energy_ml/api_bridge_test.py").exists()
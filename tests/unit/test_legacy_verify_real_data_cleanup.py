from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_verify_real_data_script_is_removed() -> None:
    assert not (ROOT / "scripts/verify_real_data.py").exists()
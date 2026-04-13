from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_validation_script_is_removed() -> None:
    assert not (ROOT / "scripts/validation_check.py").exists()
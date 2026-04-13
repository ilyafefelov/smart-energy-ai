from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_debug_import_script_is_removed() -> None:
    assert not (ROOT / "scripts/debug_import.py").exists()
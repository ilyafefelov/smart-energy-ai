from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_debug_oree_structure_script_is_removed() -> None:
    assert not (ROOT / "scripts/debug_oree_structure.py").exists()
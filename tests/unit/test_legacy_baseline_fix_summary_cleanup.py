from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_baseline_fix_summary_script_is_removed() -> None:
    assert not (ROOT / "scripts/baseline_fix_summary.py").exists()
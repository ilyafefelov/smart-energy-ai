from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_sample_data_script_is_removed() -> None:
    assert not (ROOT / "scripts/generate_sample_data.py").exists()
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_analyze_hourly_prices_script_is_removed() -> None:
    assert not (ROOT / "scripts/analyze_hourly_prices.py").exists()
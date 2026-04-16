from datetime import datetime

from src.data_pipeline.oree_fetch import _extract_prices_from_data_view_content, _parse_decimal, _parse_hour_value


def test_parse_decimal_handles_localized_numeric_text() -> None:
    assert _parse_decimal("1 234,5 грн") == 1234.5
    assert _parse_decimal("0.5") == 0.5
    assert _parse_decimal("invalid") is None


def test_parse_hour_value_extracts_valid_hours_only() -> None:
    assert _parse_hour_value("00:00-01:00") == 0
    assert _parse_hour_value("23") == 23
    assert _parse_hour_value("25") is None


def test_extract_prices_from_data_view_content_preserves_row_shape() -> None:
    html = "<table><tr><th>Date</th><th>1</th><th>2</th></tr><tr><td>06.03.2026</td><td>1000</td><td>1200</td></tr></table>"

    rows = _extract_prices_from_data_view_content(html, datetime(2026, 3, 6).date())

    assert len(rows) == 2
    assert rows[0]["timestamp"] == datetime(2026, 3, 6, 0, 0)
    assert rows[0]["price_uah_mwh"] == 1000.0
    assert rows[1]["timestamp"] == datetime(2026, 3, 6, 1, 0)
    assert rows[0]["source"] == "OREE_DATA_VIEW"
    assert set(rows[0]) == {"timestamp", "price_eur_mwh", "price_uah_mwh", "volume_mwh", "source"}
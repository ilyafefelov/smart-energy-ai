from datetime import datetime

import pandas as pd

from src.data_pipeline.oree_fetch import (
    _build_prices_frame,
    _extract_prices_from_data_view_content,
    _parse_decimal,
    _parse_hour_value,
    _parse_table_price_row,
    _parse_xls_price_row,
)


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


def test_build_prices_frame_sorts_rows_and_applies_uah_conversion() -> None:
    prices = [{"hour": hour, "price": 10.0 + hour} for hour in range(23, -1, -1)]

    frame = _build_prices_frame(prices, "oree_table", now=datetime(2026, 3, 6, 12, 30))

    assert frame is not None
    assert len(frame) == 24
    assert frame["timestamp"].iloc[0] == datetime(2026, 3, 6, 0, 0)
    assert frame["timestamp"].iloc[-1] == datetime(2026, 3, 6, 23, 0)
    assert frame["price_uah_mwh"].iloc[0] == 350.0
    assert frame["source"].iloc[0] == "oree_table"


def test_playwright_price_row_parsers_extract_expected_values() -> None:
    xls_df = pd.DataFrame({"Hour": ["00:00"], "Price": ["10,5"]})
    xls_row = _parse_xls_price_row(xls_df.iloc[0], list(xls_df.columns))

    assert xls_row == {"hour": 0, "price": 10.5}

    class FakeCell:
        def __init__(self, text: str):
            self._text = text

        def text_content(self):
            return self._text

    table_row = _parse_table_price_row([FakeCell("01:00"), FakeCell("21")])

    assert table_row == {"hour": 1, "price": 21.0}
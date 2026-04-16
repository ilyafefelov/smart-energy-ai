"""Reusable OREE market data fetch and parse helpers.

These helpers intentionally return parsed rows or ``None`` on fetch failures.
Callers decide whether to retry, fail, or synthesize fallback data.
"""

from __future__ import annotations

from datetime import datetime
import logging
import re
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)

UAH_PER_EUR = 40.0
OREE_PRICES_URL = "https://www.oree.com.ua/index.php/pricectr?lang=english"
OREE_DATA_VIEW_URL = "https://www.oree.com.ua/index.php/pricectr/data_view"
HOUR_COLUMN_TOKENS = ("hour", "hod", "година")
PRICE_COLUMN_TOKENS = ("price", "eur", "грн")
PLAYWRIGHT_UAH_PER_EUR = 35.0


def _build_market_row(
    timestamp: datetime,
    price_eur_mwh: float,
    price_uah_mwh: float,
    volume_mwh: float,
    source: str,
) -> Dict[str, Any]:
    return {
        "timestamp": timestamp,
        "price_eur_mwh": float(price_eur_mwh),
        "price_uah_mwh": float(price_uah_mwh),
        "volume_mwh": float(max(0.0, volume_mwh)),
        "source": source,
    }


def _is_missing_value(value: object) -> bool:
    try:
        return bool(pd.isna(value))
    except TypeError:
        return False


def _extract_hour_from_text(text: object) -> Optional[int]:
    if _is_missing_value(text):
        return None

    normalized_text = str(text).strip()
    if not normalized_text:
        return None

    if ":" in normalized_text:
        try:
            hour = int(normalized_text.split(":", 1)[0])
        except ValueError:
            hour = None
        if hour is not None and 0 <= hour <= 23:
            return hour

    for digit in re.findall(r"\d+", normalized_text):
        try:
            hour = int(digit)
        except ValueError:
            continue
        if 0 <= hour <= 23:
            return hour

    return None


def _extract_price_from_value(value: object, *, maximum: float = 1000) -> Optional[float]:
    if _is_missing_value(value):
        return None

    text = str(value).replace(",", ".")
    for number_text in re.findall(r"\d+\.?\d*", text):
        try:
            price = float(number_text)
        except ValueError:
            continue
        if 0.1 < price < maximum:
            return price

    return None


def _column_matches(column: object, tokens: tuple[str, ...]) -> bool:
    normalized = str(column).lower()
    return any(token in normalized for token in tokens)


def _first_matching_value(row, columns, tokens: tuple[str, ...], parser) -> object | None:
    for column in columns:
        if not _column_matches(column, tokens):
            continue
        parsed_value = parser(row[column])
        if parsed_value is not None:
            return parsed_value
    return None


def _parse_xls_price_row(row, columns) -> Optional[dict[str, float]]:
    hour = _first_matching_value(row, columns, HOUR_COLUMN_TOKENS, _extract_hour_from_text)
    price = _first_matching_value(row, columns, PRICE_COLUMN_TOKENS, _extract_price_from_value)

    if hour is None or price is None:
        return None

    return {"hour": hour, "price": price}


def _parse_table_price_row(cells) -> Optional[dict[str, float]]:
    if len(cells) < 2:
        return None

    texts = [((cell.text_content() or "").strip()) for cell in cells[:5]]
    hour = _extract_hour_from_text(texts[0])
    if hour is None:
        return None

    price = None
    for text in texts[1:]:
        price = _extract_price_from_value(text)
        if price is not None:
            break

    if price is None:
        return None

    return {"hour": hour, "price": price}


def _build_prices_frame(
    prices_list: list[dict[str, float]],
    source: str,
    *,
    now: datetime | None = None,
) -> Optional[pd.DataFrame]:
    if len(prices_list) < 20:
        return None

    current_time = now or datetime.now()
    return pd.DataFrame.from_records(
        [
            {
                "timestamp": current_time.replace(
                    hour=price_row["hour"], minute=0, second=0, microsecond=0
                ),
                "price_eur_mwh": price_row["price"],
                "price_uah_mwh": (
                    price_row["price"] * PLAYWRIGHT_UAH_PER_EUR
                    if price_row["price"] < 100
                    else price_row["price"]
                ),
                "source": source,
            }
            for price_row in sorted(prices_list, key=lambda row: row["hour"])[:24]
        ]
    )


def _fetch_oree_prices(target_date: datetime.date) -> Optional[List[Dict[str, Any]]]:
    try:
        data_view_prices = _fetch_oree_data_view_prices(target_date)
        if data_view_prices:
            return data_view_prices

        response = requests.get(OREE_PRICES_URL, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        prices = _extract_oree_price_rows(soup, target_date)
        if not prices:
            logger.warning("No parseable OREE rows found for %s", target_date)
            return None

        return prices
    except Exception as exc:
        logger.error("OREE fetch failed for %s: %s", target_date, exc)
        return None


def _fetch_oree_data_view_prices(target_date: datetime.date) -> Optional[List[Dict[str, Any]]]:
    try:
        response = requests.post(
            OREE_DATA_VIEW_URL,
            data={
                "date": target_date.strftime("%m.%Y"),
                "market": "DAM",
                "zone": "IPS",
            },
            timeout=30,
        )
        response.raise_for_status()

        payload = response.json()
        content = payload.get("content", "") if isinstance(payload, dict) else ""
        if not content:
            return None

        prices = _extract_prices_from_data_view_content(content, target_date)
        if prices:
            logger.info("Parsed %s OREE rows from data_view endpoint for %s", len(prices), target_date)
        return prices or None
    except Exception as exc:
        logger.warning("OREE data_view fetch failed for %s: %s", target_date, exc)
        return None


def _extract_prices_from_data_view_content(content_html: str, target_date: datetime.date) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(content_html, "html.parser")
    table = soup.find("table")
    if table is None:
        return []

    rows = table.find_all("tr")
    if len(rows) < 2:
        return []

    target_date_label = target_date.strftime("%d.%m.%Y")
    for row in rows[1:]:
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
        if not cells:
            continue
        if cells[0] != target_date_label:
            continue

        parsed_rows: List[Dict[str, Any]] = []
        for hour_idx, price_text in enumerate(cells[1:25], start=1):
            price_uah = _parse_decimal(price_text)
            if price_uah is None or price_uah <= 0:
                continue

            timestamp = datetime.combine(target_date, datetime.min.time().replace(hour=hour_idx - 1))
            parsed_rows.append(
                _build_market_row(
                    timestamp=timestamp,
                    price_eur_mwh=price_uah / UAH_PER_EUR,
                    price_uah_mwh=price_uah,
                    volume_mwh=1000.0,
                    source="OREE_DATA_VIEW",
                )
            )

        return parsed_rows

    return []


def _extract_oree_price_rows(soup: BeautifulSoup, target_date: datetime.date) -> List[Dict[str, Any]]:
    preferred_tables = soup.find_all("table", class_="price-table")
    tables = preferred_tables or soup.find_all("table")
    if not tables:
        logger.warning("No tables found on OREE page")
        return []

    best_candidate: List[Dict[str, Any]] = []
    for table in tables:
        parsed = _parse_table_rows(table, target_date)
        if len(parsed) > len(best_candidate):
            best_candidate = parsed

    if best_candidate:
        logger.info("Parsed %s OREE rows from HTML tables", len(best_candidate))
    return best_candidate


def _parse_table_rows(table: Any, target_date: datetime.date) -> List[Dict[str, Any]]:
    rows = table.find_all("tr")
    if not rows:
        return []

    parsed_rows: List[Dict[str, Any]] = []
    seen_hours = set()

    for row in rows:
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue

        cell_text = [cell.get_text(" ", strip=True) for cell in cells]
        hour = _parse_hour_value(cell_text[0])
        if hour is None or hour in seen_hours:
            continue

        price_raw = _parse_decimal(cell_text[1])
        if price_raw is None:
            continue

        volume = _parse_decimal(cell_text[2]) if len(cell_text) > 2 else None
        if volume is None:
            volume = 1000.0

        if price_raw > 500:
            price_uah = price_raw
            price_eur = price_raw / UAH_PER_EUR
        else:
            price_eur = price_raw
            price_uah = price_raw * UAH_PER_EUR

        if not (0 < price_eur < 500):
            continue

        timestamp = datetime.combine(target_date, datetime.min.time().replace(hour=hour))
        parsed_rows.append(
            _build_market_row(
                timestamp=timestamp,
                price_eur_mwh=price_eur,
                price_uah_mwh=price_uah,
                volume_mwh=volume,
                source="OREE",
            )
        )
        seen_hours.add(hour)

    return sorted(parsed_rows, key=lambda row: row["timestamp"])


def _parse_hour_value(text: str) -> Optional[int]:
    if not text:
        return None

    for match in re.findall(r"(\d{1,2})(?::\d{2})?", text):
        hour = int(match)
        if 0 <= hour <= 23:
            return hour
    return None


def _parse_decimal(text: str) -> Optional[float]:
    if not text:
        return None

    cleaned = text.replace("\xa0", " ").replace(" ", "")
    number_match = re.search(r"[-+]?\d+[\d.,]*", cleaned)
    if not number_match:
        return None

    raw = number_match.group(0)
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")

    try:
        return float(raw)
    except ValueError:
        return None


__all__ = [
    "UAH_PER_EUR",
    "_build_market_row",
    "_build_prices_frame",
    "_extract_hour_from_text",
    "_extract_oree_price_rows",
    "_extract_price_from_value",
    "_extract_prices_from_data_view_content",
    "_fetch_oree_data_view_prices",
    "_fetch_oree_prices",
    "_parse_table_price_row",
    "_parse_decimal",
    "_parse_hour_value",
    "_parse_xls_price_row",
    "_parse_table_rows",
]
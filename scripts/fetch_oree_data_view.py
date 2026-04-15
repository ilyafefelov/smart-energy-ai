#!/usr/bin/env python3
"""Fetch OREE day-ahead hourly prices for a specific date and print JSON."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from typing import Dict
from urllib.parse import urlunsplit

import requests
from bs4 import BeautifulSoup

OREE_HOST = os.getenv("SMART_ENERGY_AI_OREE_HOST", "www.oree.com.ua")
OREE_ORIGIN_URL = urlunsplit(("https", OREE_HOST, "", "", ""))
OREE_DATA_VIEW_URL = urlunsplit(("https", OREE_HOST, "/index.php/pricectr/data_view", "", ""))
OREE_ENGLISH_REFERER_URL = urlunsplit(("https", OREE_HOST, "/index.php/pricectr", "lang=english", ""))


def parse_decimal(text: str) -> float | None:
    normalized = text.replace(" ", "").replace("\xa0", "").replace(",", ".")
    try:
        value = float(normalized)
        if value <= 0:
            return None
        return value
    except Exception:
        return None


def fetch_prices_for_date(date_label: str) -> Dict[str, float]:
    target_date = datetime.strptime(date_label, "%d.%m.%Y")
    month_label = target_date.strftime("%m.%Y")

    response = requests.post(
        OREE_DATA_VIEW_URL,
        data={"date": month_label, "market": "DAM", "zone": "IPS"},
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": OREE_ENGLISH_REFERER_URL,
            "Origin": OREE_ORIGIN_URL,
        },
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()
    content_html = payload.get("content", "") if isinstance(payload, dict) else ""
    if not content_html:
        return {}

    soup = BeautifulSoup(content_html, "html.parser")
    table = soup.find("table")
    if table is None:
        return {}

    rows = table.find_all("tr")
    prices: Dict[str, float] = {}

    for row in rows:
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
        if len(cells) < 25:
            continue
        if cells[0] != date_label:
            continue

        for hour in range(24):
            value = parse_decimal(cells[hour + 1])
            if value is None:
                continue
            prices[str(hour)] = round(value / 1000.0, 4)
        break

    return prices


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="Date in dd.mm.yyyy format")
    args = parser.parse_args()

    try:
        prices = fetch_prices_for_date(args.date)
        print(json.dumps({"success": True, "hours": prices}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc), "hours": {}}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

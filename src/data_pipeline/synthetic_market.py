"""Synthetic market fallback generation helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

import numpy as np

from src.data_pipeline.oree_fetch import UAH_PER_EUR, _build_market_row


def _generate_synthetic_prices() -> List[Dict[str, Any]]:
    """Generate synthetic market prices for development and fallback flows."""

    prices = []
    base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    for hour in range(48):
        timestamp = base_date + timedelta(hours=hour)

        if 6 <= timestamp.hour <= 9:
            base_price = 60 + np.random.normal(0, 8)
        elif 17 <= timestamp.hour <= 21:
            base_price = 80 + np.random.normal(0, 10)
        elif 23 <= timestamp.hour or timestamp.hour <= 5:
            base_price = 35 + np.random.normal(0, 5)
        else:
            base_price = 50 + np.random.normal(0, 6)

        price_eur = max(20, base_price)
        price_uah = price_eur * UAH_PER_EUR
        volume = 1000 + np.random.normal(0, 200)

        prices.append(
            _build_market_row(
                timestamp=timestamp,
                price_eur_mwh=price_eur,
                price_uah_mwh=price_uah,
                volume_mwh=max(100.0, volume),
                source="SYNTHETIC",
            )
        )

    return prices


__all__ = ["_generate_synthetic_prices"]
"""Historical OREE price analysis for realistic arbitrage ranges.

This module scrapes and analyzes historical OREE DAM price data to build
realistic arbitrage expectations for battery storage systems.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import polars as pl


def scrape_historical_oree_prices(
    days_back: int = 90,
    target_dir: str = "data/raw",
) -> pd.DataFrame:
    """Scrape historical OREE DAM prices for the past N days.

    Args:
        days_back: Number of days to look back (default 90 days)
        target_dir: Directory to save raw data

    Returns:
        DataFrame with historical price data
    """
    import sys

    # Ensure src/ is in path BEFORE importing
    src_dir = Path(__file__).resolve().parents[1]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from src.data_pipeline.oree_fetch import _fetch_oree_prices

    all_prices: list[dict[str, Any]] = []
    today = datetime.now().date()

    print(f"Scraping {days_back} days of OREE historical data...")

    for days_ago in range(1, days_back + 1):
        target_date = today - timedelta(days=days_ago)
        prices = _fetch_oree_prices(target_date)
        if prices:
            all_prices.extend(prices)
            print(f"  {target_date}: {len(prices)} rows")
        else:
            print(f"  {target_date}: No data")

    if not all_prices:
        print("No historical data collected")
        return pd.DataFrame()

    df = pd.DataFrame(all_prices)
    print(f"Total: {len(df)} price records collected")

    # Save to raw data directory
    raw_dir = Path(target_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_file = raw_dir / "oree_historical_prices.parquet"
    df.to_parquet(output_file, index=False)
    print(f"Saved to {output_file}")

    return df


UAH_PER_EUR = 40.0  # Current exchange rate for display


def compute_arbitrage_statistics(df: pd.DataFrame, use_uah: bool = True) -> dict[str, Any]:
    """Compute arbitrage statistics from historical price data.

    Args:
        df: DataFrame with timestamp and price columns
        use_uah: Use UAH prices (OREE source currency) vs EUR conversion

    Returns:
        Dictionary with arbitrage statistics per day
    """
    if df.empty:
        return {}

    df = df.sort_values("timestamp").copy()
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date

    # Use UAH prices (OREE source) - they are the raw values from the exchange
    price_col = "price_uah_mwh" if use_uah else "price_eur_mwh"

    stats = []
    for date, day_prices in df.groupby("date"):
        if len(day_prices) < 2:
            continue

        prices = day_prices[price_col].values
        buy_idx = np.argmin(prices)
        sell_idx = np.argmax(prices[buy_idx + 1 :]) + buy_idx + 1 if buy_idx < len(prices) - 1 else -1

        if sell_idx > buy_idx:
            daily_spread = float(prices[sell_idx] - prices[buy_idx])
        else:
            daily_spread = 0.0

        stats.append(
            {
                "date": date,
                "min_price": float(np.min(prices)),
                "max_price": float(np.max(prices)),
                "avg_price": float(np.mean(prices)),
                "std_price": float(np.std(prices)),
                "daily_spread": daily_spread,
                "buy_hour": buy_idx,
                "sell_hour": sell_idx,
            }
        )

    stats_df = pd.DataFrame(stats)

    return {
        "avg_daily_spread_uah": float(stats_df["daily_spread"].mean()) if len(stats_df) > 0 else 0.0,
        "median_daily_spread_uah": float(stats_df["daily_spread"].median()) if len(stats_df) > 0 else 0.0,
        "p10_daily_spread_uah": float(stats_df["daily_spread"].quantile(0.1)) if len(stats_df) > 0 else 0.0,
        "p90_daily_spread_uah": float(stats_df["daily_spread"].quantile(0.9)) if len(stats_df) > 0 else 0.0,
        "days_analyzed": len(stats_df),
        "avg_price_uah": float(stats_df["avg_price"].mean()) if len(stats_df) > 0 else 0.0,
        "price_volatility_uah": float(stats_df["std_price"].mean()) if len(stats_df) > 0 else 0.0,
        # EUR equivalents for reference
        "avg_daily_spread_eur": float(stats_df["daily_spread"].mean() / UAH_PER_EUR) if len(stats_df) > 0 else 0.0,
        "median_daily_spread_eur": float(stats_df["daily_spread"].median() / UAH_PER_EUR) if len(stats_df) > 0 else 0.0,
        "p10_daily_spread_eur": float(stats_df["daily_spread"].quantile(0.1) / UAH_PER_EUR) if len(stats_df) > 0 else 0.0,
        "p90_daily_spread_eur": float(stats_df["daily_spread"].quantile(0.9) / UAH_PER_EUR) if len(stats_df) > 0 else 0.0,
        "avg_price_eur": float(stats_df["avg_price"].mean() / UAH_PER_EUR) if len(stats_df) > 0 else 0.0,
    }


def generate_arbitrage_ranges(
    price_stats: dict[str, Any],
    capacity_kwh: float,
    daily_cycles: float,
    roundtrip_efficiency: float = 0.95,
    dod_limit: float = 0.9,
) -> dict[str, float]:
    """Generate realistic arbitrage ranges based on historical data.

    Args:
        price_stats: Statistics from compute_arbitrage_statistics
        capacity_kwh: Battery capacity in kWh
        daily_cycles: Expected daily charge/discharge cycles
        roundtrip_efficiency: Round-trip efficiency (default 0.95)
        dod_limit: Depth of discharge limit (default 0.9)

    Returns:
        Dictionary with conservative, median, and optimistic annual values (UAH)
    """
    usable_capacity = capacity_kwh * dod_limit
    annual_mwh = (usable_capacity / 1000) * daily_cycles * 365

    # Use UAH spreads from the updated price_stats
    conservative_spread_uah = price_stats.get("p10_daily_spread_uah", 0.0)
    median_spread_uah = price_stats.get("median_daily_spread_uah", 0.0)
    optimistic_spread_uah = price_stats.get("p90_daily_spread_uah", 0.0)

    return {
        "conservative_annual_value_uah": annual_mwh * conservative_spread_uah * roundtrip_efficiency,
        "median_annual_value_uah": annual_mwh * median_spread_uah * roundtrip_efficiency,
        "optimistic_annual_value_uah": annual_mwh * optimistic_spread_uah * roundtrip_efficiency,
        "conservative_annual_value_eur": annual_mwh * conservative_spread_uah * roundtrip_efficiency / UAH_PER_EUR,
        "median_annual_value_eur": annual_mwh * median_spread_uah * roundtrip_efficiency / UAH_PER_EUR,
        "optimistic_annual_value_eur": annual_mwh * optimistic_spread_uah * roundtrip_efficiency / UAH_PER_EUR,
        "avg_daily_spread_uah": price_stats.get("avg_daily_spread_uah", 0.0),
        "avg_daily_spread_eur": price_stats.get("avg_daily_spread_eur", 0.0),
        "p10_daily_spread_uah": conservative_spread_uah,
        "p10_daily_spread_eur": conservative_spread_uah / UAH_PER_EUR,
        "p90_daily_spread_uah": optimistic_spread_uah,
        "p90_daily_spread_eur": optimistic_spread_uah / UAH_PER_EUR,
    }


def analyze_and_export_ranges(
    historical_df: pd.DataFrame | None = None,
    output_file: str = "data/results/arbitrage_ranges.yaml",
) -> dict[str, Any]:
    """Analyze historical data and export arbitrage ranges.

    Args:
        historical_df: Pre-loaded historical data (optional)
        output_file: Output file path

    Returns:
        Dictionary with all computed ranges
    """
    from pathlib import Path

    if historical_df is None or historical_df.empty:
        # Try to load from saved file
        parquet_file = Path("data/raw/oree_historical_prices.parquet")
        if parquet_file.exists():
            historical_df = pd.read_parquet(parquet_file)
        else:
            historical_df = scrape_historical_oree_prices(days_back=30)

    price_stats = compute_arbitrage_statistics(historical_df)

    # Generate ranges for different battery configurations
    configs = [
        {"name": "residential_10kwh", "capacity_kwh": 10.0, "daily_cycles": 1.0},
        {"name": "commercial_100kwh", "capacity_kwh": 100.0, "daily_cycles": 1.5},
        {"name": "industrial_500kwh", "capacity_kwh": 500.0, "daily_cycles": 2.0},
    ]

    all_ranges = {"price_statistics": price_stats, "configurations": {}}

    for config in configs:
        ranges = generate_arbitrage_ranges(
            price_stats=price_stats,
            capacity_kwh=config["capacity_kwh"],
            daily_cycles=config["daily_cycles"],
        )
        all_ranges["configurations"][config["name"]] = {
            **config,
            **ranges,
        }

    # Export as JSON with proper float conversion
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    import json

    # Convert numpy types to native Python for JSON serialization
    def convert_to_native(obj):
        if isinstance(obj, dict):
            return {k: convert_to_native(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_native(v) for v in obj]
        elif hasattr(obj, "item"):  # numpy scalar
            return float(obj.item())
        elif isinstance(obj, (float, int)):
            return float(obj)
        return obj

    all_ranges_native = convert_to_native(all_ranges)
    with open(output_path.with_suffix(".json"), "w") as f:
        json.dump(all_ranges_native, f, indent=2)
    print(f"Exported arbitrage ranges to {output_path.with_suffix('.json')}")

    return all_ranges


if __name__ == "__main__":
    print("=== OREE Historical Arbitrage Analysis ===")
    result = analyze_and_export_ranges()
    print("\nResults (OREE DAM prices in UAH/MWh):")
    stats = result['price_statistics']
    print(f"  Days analyzed: {int(stats.get('days_analyzed', 0))}")
    print(f"  Avg daily spread: {stats.get('avg_daily_spread_uah', 0):,.0f} UAH/MWh ({stats.get('avg_daily_spread_eur', 0):.2f} EUR/MWh)")
    print(f"  Median daily spread: {stats.get('median_daily_spread_uah', 0):,.0f} UAH/MWh ({stats.get('median_daily_spread_eur', 0):.2f} EUR/MWh)")
    print(f"  P10 (conservative): {stats.get('p10_daily_spread_uah', 0):,.0f} UAH/MWh ({stats.get('p10_daily_spread_eur', 0):.2f} EUR/MWh)")
    print(f"  P90 (optimistic): {stats.get('p90_daily_spread_uah', 0):,.0f} UAH/MWh ({stats.get('p90_daily_spread_eur', 0):.2f} EUR/MWh)")
    print(f"  Avg price: {stats.get('avg_price_uah', 0):,.0f} UAH/MWh ({stats.get('avg_price_eur', 0):.2f} EUR/MWh)")
    print("\nAnnual Arbitrage Ranges:")
    for name, config in result["configurations"].items():
        print(f"\n  {name}:")
        print(f"    Conservative: {config.get('conservative_annual_value_uah', 0):,.0f} UAH/yr ({config.get('conservative_annual_value_eur', 0):,.0f} €/yr)")
        print(f"    Median:       {config.get('median_annual_value_uah', 0):,.0f} UAH/yr ({config.get('median_annual_value_eur', 0):,.0f} €/yr)")
        print(f"    Optimistic:   {config.get('optimistic_annual_value_uah', 0):,.0f} UAH/yr ({config.get('optimistic_annual_value_eur', 0):,.0f} €/yr)")

"""Optimization schedule asset using baseline dynamic programming."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import polars as pl
import yaml
from dagster import AssetIn, asset

from ...optimization import BaselineDPOptimizer, BaselineOptimizationConfig


def _load_client_capacities() -> Dict[str, float]:
    config_path = Path("customers.yaml")
    if not config_path.exists():
        return {}

    try:
        config_data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

    capacities: Dict[str, float] = {}
    for entry in config_data.get("customers", []):
        client_id = entry.get("id")
        battery_kwh = entry.get("battery_capacity_kwh")
        if client_id and battery_kwh is not None:
            capacities[str(client_id)] = float(battery_kwh)
    return capacities


def _extract_price_horizon(price_forecast: pl.DataFrame) -> List[float]:
    if "predicted_price_eur_mwh" in price_forecast.columns:
        return price_forecast.select("predicted_price_eur_mwh").to_series().to_list()
    if "price_eur_mwh" in price_forecast.columns:
        return price_forecast.select("price_eur_mwh").to_series().to_list()
    return []


def _get_client_series(client_df: pl.DataFrame, column: str, horizon: int, fallback: float) -> List[float]:
    if column not in client_df.columns or len(client_df) == 0:
        return [fallback] * horizon

    values = client_df.select(column).to_series().to_list()
    if not values:
        return [fallback] * horizon

    tail = [float(v) for v in values[-horizon:]]
    if len(tail) < horizon:
        tail = [float(tail[-1])] * (horizon - len(tail)) + tail
    return tail


@asset(
    group_name="optimization",
    description="Baseline DP optimizer schedule from forecast prices and client state",
    ins={
        "price_forecast": AssetIn("price_forecast_asset"),
        "client_state": AssetIn("client_state_asset"),
    },
    metadata={
        "algorithm": "dynamic_programming_baseline",
        "objective": "purchase_cost - export_revenue + degradation_penalty",
    },
)
def optimization_schedule_asset(context, price_forecast: pl.DataFrame, client_state: pl.DataFrame) -> pl.DataFrame:
    prices = _extract_price_horizon(price_forecast)
    if not prices:
        context.log.warning("No forecast price column found; returning empty optimization schedule")
        return pl.DataFrame(
            schema={
                "client_id": pl.Utf8,
                "hour": pl.Int64,
                "action_kw": pl.Float64,
                "soc_before_kwh": pl.Float64,
                "soc_after_kwh": pl.Float64,
                "grid_import_kwh": pl.Float64,
                "grid_export_kwh": pl.Float64,
                "net_cost_eur": pl.Float64,
                "total_net_cost_eur": pl.Float64,
            }
        )

    horizon = min(24, len(prices))
    capacity_by_client = _load_client_capacities()

    output_frames: List[pl.DataFrame] = []
    client_ids = (
        client_state.select("client_id").unique().to_series().to_list()
        if "client_id" in client_state.columns
        else ["client_default"]
    )

    for client_id in client_ids:
        client_df = (
            client_state.filter(pl.col("client_id") == client_id).sort("timestamp")
            if "client_id" in client_state.columns
            else client_state.sort("timestamp")
        )

        if len(client_df) == 0:
            continue

        capacity_kwh = float(capacity_by_client.get(str(client_id), 200.0))
        soc_percent = float(client_df.select("battery_soc").to_series().to_list()[-1]) if "battery_soc" in client_df.columns else 50.0
        load_forecast = _get_client_series(client_df, "load_actual", horizon, fallback=40.0)
        solar_forecast = _get_client_series(client_df, "solar_gen_actual", horizon, fallback=0.0)

        optimizer = BaselineDPOptimizer(
            BaselineOptimizationConfig(
                capacity_kwh=capacity_kwh,
                min_soc_fraction=0.15,
                max_soc_fraction=0.95,
                initial_soc_fraction=max(0.0, min(1.0, soc_percent / 100.0)),
                max_charge_kw=max(25.0, 0.25 * capacity_kwh),
                max_discharge_kw=max(25.0, 0.25 * capacity_kwh),
                throughput_limit_kwh=capacity_kwh * 1.2,
                degradation_cost_per_kwh=0.01,
            )
        )

        result = optimizer.optimize(
            price_eur_mwh=prices[:horizon],
            load_kw=load_forecast,
            solar_kw=solar_forecast,
        )

        schedule_rows = [{
            "client_id": str(client_id),
            "hour": int(row["hour"]),
            "action_kw": float(row["action_kw"]),
            "charge_kwh": float(row["charge_kwh"]),
            "discharge_kwh": float(row["discharge_kwh"]),
            "soc_before_kwh": float(row["soc_before_kwh"]),
            "soc_after_kwh": float(row["soc_after_kwh"]),
            "throughput_total_kwh": float(row["throughput_total_kwh"]),
            "price_eur_mwh": float(row["price_eur_mwh"]),
            "grid_import_kwh": float(row["grid_import_kwh"]),
            "grid_export_kwh": float(row["grid_export_kwh"]),
            "purchase_cost_eur": float(row["purchase_cost_eur"]),
            "export_revenue_eur": float(row["export_revenue_eur"]),
            "degradation_penalty_eur": float(row["degradation_penalty_eur"]),
            "net_cost_eur": float(row["net_cost_eur"]),
            "total_net_cost_eur": float(result["objective"]["net_cost_eur"]),
            "final_soc_kwh": float(result["constraints"]["final_soc_kwh"]),
            "throughput_limit_kwh": float(result["constraints"]["throughput_limit_kwh"]),
            "algorithm": str(result["metadata"]["algorithm"]),
        } for row in result["schedule"]]

        output_frames.append(pl.DataFrame(schedule_rows))

    if not output_frames:
        return pl.DataFrame()

    combined = pl.concat(output_frames, how="vertical").sort(["client_id", "hour"])
    context.log.info(
        "optimization_schedule generated for %d clients horizon=%d total_rows=%d",
        len(output_frames),
        horizon,
        len(combined),
    )
    return combined

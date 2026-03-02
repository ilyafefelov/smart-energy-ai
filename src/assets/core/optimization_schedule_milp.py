"""MILP optimization schedule asset with solver fallback behavior."""

from __future__ import annotations

from typing import List

import polars as pl
from dagster import AssetIn, asset

from ...optimization import MilpBatteryScheduler, MilpSchedulerConfig
from .optimization_schedule import _extract_price_horizon, _get_client_series, _load_client_capacities


@asset(
    group_name="optimization",
    description="MILP/LP battery schedule from forecast prices and client state",
    ins={
        "price_forecast": AssetIn("price_forecast_asset"),
        "client_state": AssetIn("client_state_asset"),
    },
    metadata={
        "algorithm": "mip_scheduler",
        "solver_behavior": "cvxpy_milp_preferred_with_scipy_linprog_fallback",
    },
)
def optimization_schedule_milp_asset(context, price_forecast: pl.DataFrame, client_state: pl.DataFrame) -> pl.DataFrame:
    prices = _extract_price_horizon(price_forecast)
    if not prices:
        context.log.warning("No forecast prices available for MILP schedule")
        return pl.DataFrame()

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

        scheduler = MilpBatteryScheduler(
            MilpSchedulerConfig(
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

        result = scheduler.optimize(prices[:horizon], load_forecast, solar_forecast)

        rows = [{
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
            "solver": str(result["metadata"]["solver"]),
        } for row in result["schedule"]]

        output_frames.append(pl.DataFrame(rows))

    if not output_frames:
        return pl.DataFrame()

    combined = pl.concat(output_frames, how="vertical").sort(["client_id", "hour"])
    context.log.info(f"optimization_schedule_milp generated rows={len(combined)} clients={len(output_frames)}")
    return combined

"""Optimization schedule asset using baseline dynamic programming."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

import polars as pl
from dagster import AssetIn, asset

from src.data_pipeline.optimization_profile_loader import (
    _coerce_float,
    _load_client_capacities,
    _load_client_profiles,
    _normalize_market_regime_override,
)
from src.data_pipeline.optimization_schedule_inputs import _extract_price_horizon, _get_client_series

from ...physics.economics import BatteryTechnology, EconomicModel
from ...optimization.baseline_dp import BaselineDPOptimizer, BaselineOptimizationConfig


OPTIMIZATION_SCHEDULE_SCHEMA: Dict[str, pl.DataType] = {
    "client_id": pl.Utf8,
    "hour": pl.Int64,
    "action_kw": pl.Float64,
    "charge_kwh": pl.Float64,
    "discharge_kwh": pl.Float64,
    "soc_before_kwh": pl.Float64,
    "soc_after_kwh": pl.Float64,
    "throughput_total_kwh": pl.Float64,
    "price_eur_mwh": pl.Float64,
    "load_kwh": pl.Float64,
    "solar_kwh": pl.Float64,
    "grid_import_kwh": pl.Float64,
    "grid_export_kwh": pl.Float64,
    "purchase_cost_eur": pl.Float64,
    "export_revenue_eur": pl.Float64,
    "degradation_penalty_eur": pl.Float64,
    "net_cost_eur": pl.Float64,
    "total_net_cost_eur": pl.Float64,
    "final_soc_kwh": pl.Float64,
    "throughput_limit_kwh": pl.Float64,
    "forecast_model_name": pl.Utf8,
    "forecast_model_family": pl.Utf8,
    "forecast_horizon_mode": pl.Utf8,
    "forecast_uncertainty_source": pl.Utf8,
    "forecast_promotion_active": pl.Boolean,
    "forecast_promotion_source": pl.Utf8,
    "algorithm": pl.Utf8,
    "solver": pl.Utf8,
}

DEFAULT_RESERVE_FLOOR_FRACTION = 0.15
DEFAULT_EXPORT_PRICE_FACTOR = 0.9


def build_empty_optimization_schedule() -> pl.DataFrame:
    """Return the canonical empty optimization schedule frame."""
    return pl.DataFrame(schema=OPTIMIZATION_SCHEDULE_SCHEMA)


def build_optimization_schedule_frame(rows: List[Dict[str, Any]]) -> pl.DataFrame:
    """Materialize optimization schedule rows with the shared contract."""
    if not rows:
        return build_empty_optimization_schedule()

    normalized_rows = [
        {column: row.get(column) for column in OPTIMIZATION_SCHEDULE_SCHEMA}
        for row in rows
    ]
    return pl.DataFrame(normalized_rows, schema=OPTIMIZATION_SCHEDULE_SCHEMA)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def _normalize_fraction_candidate(value: Any, fallback: Optional[float], maximum: float = 1.0) -> Optional[float]:
    numeric = _coerce_float(value)
    if numeric is None:
        return fallback
    if numeric > 1.0:
        numeric /= 100.0
    return _clamp(numeric, 0.0, maximum)
def _resolve_battery_technology(battery_type: Any) -> Optional[BatteryTechnology]:
    normalized = str(battery_type or "").strip().lower().replace("-", "_")
    if "lfp" in normalized:
        return BatteryTechnology.LFP
    if "nmc" in normalized:
        return BatteryTechnology.NMC
    if "lead" in normalized:
        return BatteryTechnology.LEAD_ACID
    if "sodium" in normalized:
        return BatteryTechnology.SODIUM_ION
    return None
def _infer_market_regime(site_power_kw: Optional[float], override: Any = "auto") -> str:
    normalized_override = _normalize_market_regime_override(override)
    if normalized_override != "auto":
        return normalized_override
    if site_power_kw is None or site_power_kw <= 0:
        return "unclassified"
    return "market_premium" if site_power_kw > 50.0 else "net_billing"


def _resolve_client_optimization_inputs(client_profile: Mapping[str, Any], capacity_kwh: float) -> Dict[str, float | str]:
    technology = _resolve_battery_technology(client_profile.get("battery_type"))
    economics = EconomicModel(technology, capacity_kwh) if technology is not None else None

    roundtrip_efficiency = _normalize_fraction_candidate(
        client_profile.get("battery_efficiency"),
        economics.params.roundtrip_efficiency if economics is not None else 0.92,
    )
    usable_fraction = _normalize_fraction_candidate(
        client_profile.get("battery_dod_max"),
        economics.params.dod_limit if economics is not None else 0.9,
    )
    reserve_floor_fraction = _normalize_fraction_candidate(
        client_profile.get("battery_soc_min"),
        DEFAULT_RESERVE_FLOOR_FRACTION,
        maximum=0.95,
    )
    min_soc_fraction = max(float(reserve_floor_fraction or DEFAULT_RESERVE_FLOOR_FRACTION), 1.0 - float(usable_fraction or 0.9))

    site_power_kw = _coerce_float(client_profile.get("site_power_kw"))
    market_regime = _infer_market_regime(site_power_kw, client_profile.get("market_regime_override"))

    max_power_kw = max(25.0, 0.25 * capacity_kwh)
    if site_power_kw is not None and site_power_kw > 0:
        max_power_kw = min(max_power_kw, site_power_kw)

    degradation_cost_per_kwh = 0.01
    if economics is not None:
        degradation_cost_per_kwh = max(
            (economics.params.capex_per_kwh * economics.params.replacement_cost_ratio)
            / max(economics.params.cycle_life * float(usable_fraction or 0.9), 1.0),
            0.001,
        )

    export_price_factor = 1.0 if market_regime == "market_premium" else DEFAULT_EXPORT_PRICE_FACTOR

    return {
        "market_regime": market_regime,
        "min_soc_fraction": min_soc_fraction,
        "roundtrip_efficiency": float(roundtrip_efficiency or 0.92),
        "max_power_kw": float(max_power_kw),
        "degradation_cost_per_kwh": float(degradation_cost_per_kwh),
        "export_price_factor": float(export_price_factor),
    }


def _resolve_forecast_context(
    price_forecast: pl.DataFrame,
    *,
    horizon_mode: str,
) -> Dict[str, Any]:
    rows = price_forecast.sort("forecast_timestamp").to_dicts() if len(price_forecast) else []
    first_row = rows[0] if rows else {}
    promotion_active = first_row.get("promotion_active")

    return {
        "forecast_model_name": str(first_row.get("model_name") or "") or None,
        "forecast_model_family": str(first_row.get("model_family") or "") or None,
        "forecast_horizon_mode": horizon_mode,
        "forecast_uncertainty_source": str(first_row.get("uncertainty_source") or "") or None,
        "forecast_promotion_active": bool(promotion_active) if promotion_active is not None else False,
        "forecast_promotion_source": str(first_row.get("promotion_source") or "") or None,
    }


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
    horizon_mode = "conservative"
    prices = _extract_price_horizon(price_forecast, horizon_mode=horizon_mode)
    if not prices:
        context.log.warning("No forecast price column found; returning empty optimization schedule")
        return build_empty_optimization_schedule()

    horizon = min(24, len(prices))
    client_profiles = _load_client_profiles()
    forecast_context = _resolve_forecast_context(price_forecast, horizon_mode=horizon_mode)

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

        client_profile = client_profiles.get(str(client_id), {})
        capacity_kwh = float(client_profile.get("battery_capacity_kwh") or 200.0)
        soc_percent = float(client_df.select("battery_soc").to_series().to_list()[-1]) if "battery_soc" in client_df.columns else 50.0
        load_forecast = _get_client_series(client_df, "load_actual", horizon, fallback=40.0)
        solar_forecast = _get_client_series(client_df, "solar_gen_actual", horizon, fallback=0.0)
        optimization_inputs = _resolve_client_optimization_inputs(client_profile, capacity_kwh)

        optimizer = BaselineDPOptimizer(
            BaselineOptimizationConfig(
                capacity_kwh=capacity_kwh,
                min_soc_fraction=float(optimization_inputs["min_soc_fraction"]),
                max_soc_fraction=0.95,
                initial_soc_fraction=max(0.0, min(1.0, soc_percent / 100.0)),
                roundtrip_efficiency=float(optimization_inputs["roundtrip_efficiency"]),
                max_charge_kw=float(optimization_inputs["max_power_kw"]),
                max_discharge_kw=float(optimization_inputs["max_power_kw"]),
                throughput_limit_kwh=capacity_kwh * 1.2,
                degradation_cost_per_kwh=float(optimization_inputs["degradation_cost_per_kwh"]),
                export_price_factor=float(optimization_inputs["export_price_factor"]),
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
            "load_kwh": float(row["load_kwh"]),
            "solar_kwh": float(row["solar_kwh"]),
            "grid_import_kwh": float(row["grid_import_kwh"]),
            "grid_export_kwh": float(row["grid_export_kwh"]),
            "purchase_cost_eur": float(row["purchase_cost_eur"]),
            "export_revenue_eur": float(row["export_revenue_eur"]),
            "degradation_penalty_eur": float(row["degradation_penalty_eur"]),
            "net_cost_eur": float(row["net_cost_eur"]),
            "total_net_cost_eur": float(result["objective"]["net_cost_eur"]),
            "final_soc_kwh": float(result["constraints"]["final_soc_kwh"]),
            "throughput_limit_kwh": float(result["constraints"]["throughput_limit_kwh"]),
            "forecast_model_name": forecast_context["forecast_model_name"],
            "forecast_model_family": forecast_context["forecast_model_family"],
            "forecast_horizon_mode": forecast_context["forecast_horizon_mode"],
            "forecast_uncertainty_source": forecast_context["forecast_uncertainty_source"],
            "forecast_promotion_active": forecast_context["forecast_promotion_active"],
            "forecast_promotion_source": forecast_context["forecast_promotion_source"],
            "algorithm": str(result["metadata"]["algorithm"]),
            "solver": None,
        } for row in result["schedule"]]

        output_frames.append(build_optimization_schedule_frame(schedule_rows))

    if not output_frames:
        return build_empty_optimization_schedule()

    combined = pl.concat(output_frames, how="vertical").sort(["client_id", "hour"])
    context.log.info(
        "optimization_schedule generated for %d clients horizon=%d total_rows=%d",
        len(output_frames),
        horizon,
        len(combined),
    )
    return combined

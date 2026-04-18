"""Optimization schedule asset using bounded rolling-horizon dynamic programming."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

import polars as pl
from dagster import AssetIn, asset

from src.data_pipeline.forecast_lineage import build_forecast_lineage, build_optimization_run_id
from src.data_pipeline.optimization_profile_loader import (
    _coerce_float,
    _load_client_capacities,
    _load_client_profiles,
    _normalize_market_regime_override,
)
from src.data_pipeline.optimization_schedule_inputs import (
    DEFAULT_ROLLING_WINDOW_HOURS,
    _get_client_series,
    _resolve_price_horizon,
    _slice_horizon_window,
)

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
    "rolling_horizon_enabled": pl.Boolean,
    "rolling_window_index": pl.Int64,
    "rolling_window_start_hour": pl.Int64,
    "rolling_window_end_hour": pl.Int64,
    "rolling_window_horizon_hours": pl.Int64,
    "rolling_window_commit_hours": pl.Int64,
    "rolling_state_initial_soc_kwh": pl.Float64,
    "rolling_state_initial_throughput_kwh": pl.Float64,
    "rolling_window_purchase_cost_eur": pl.Float64,
    "rolling_window_export_revenue_eur": pl.Float64,
    "rolling_window_degradation_penalty_eur": pl.Float64,
    "rolling_window_net_cost_eur": pl.Float64,
    "forecast_run_id": pl.Utf8,
    "forecast_model_name": pl.Utf8,
    "forecast_model_family": pl.Utf8,
    "forecast_model_version": pl.Utf8,
    "forecast_window_start_utc": pl.Utf8,
    "forecast_window_end_utc": pl.Utf8,
    "forecast_latency_ms": pl.Int64,
    "forecast_freshness_minutes": pl.Float64,
    "forecast_horizon_mode": pl.Utf8,
    "forecast_horizon_source": pl.Utf8,
    "forecast_uncertainty_source": pl.Utf8,
    "forecast_uncertainty_contract_version": pl.Utf8,
    "forecast_promotion_active": pl.Boolean,
    "forecast_promotion_source": pl.Utf8,
    "optimization_run_id": pl.Utf8,
    "algorithm": pl.Utf8,
    "solver": pl.Utf8,
}

DEFAULT_RESERVE_FLOOR_FRACTION = 0.15
DEFAULT_EXPORT_PRICE_FACTOR = 0.9
ROLLING_HORIZON_COMMIT_HOURS = 1


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


def _resolve_objective_breakdown(result: Mapping[str, Any]) -> Dict[str, float]:
    schedule = list(result.get("schedule") or [])
    objective = dict(result.get("objective") or {})

    purchase_cost_eur = _coerce_float(objective.get("purchase_cost_eur"))
    if purchase_cost_eur is None:
        purchase_cost_eur = sum(_coerce_float(row.get("purchase_cost_eur")) or 0.0 for row in schedule)

    export_revenue_eur = _coerce_float(objective.get("export_revenue_eur"))
    if export_revenue_eur is None:
        export_revenue_eur = sum(_coerce_float(row.get("export_revenue_eur")) or 0.0 for row in schedule)

    degradation_penalty_eur = _coerce_float(objective.get("degradation_penalty_eur"))
    if degradation_penalty_eur is None:
        degradation_penalty_eur = sum(
            _coerce_float(row.get("degradation_penalty_eur")) or 0.0 for row in schedule
        )

    net_cost_eur = _coerce_float(objective.get("net_cost_eur"))
    if net_cost_eur is None:
        net_cost_eur = purchase_cost_eur - export_revenue_eur + degradation_penalty_eur

    return {
        "purchase_cost_eur": float(purchase_cost_eur),
        "export_revenue_eur": float(export_revenue_eur),
        "degradation_penalty_eur": float(degradation_penalty_eur),
        "net_cost_eur": float(net_cost_eur),
    }


def _build_baseline_optimizer(
    *,
    capacity_kwh: float,
    throughput_limit_kwh: float,
    optimization_inputs: Mapping[str, float | str],
    initial_soc_kwh: float,
    initial_throughput_kwh: float,
) -> BaselineDPOptimizer:
    initial_soc_fraction = 0.0 if capacity_kwh <= 0 else _clamp(initial_soc_kwh / capacity_kwh, 0.0, 1.0)
    return BaselineDPOptimizer(
        BaselineOptimizationConfig(
            capacity_kwh=capacity_kwh,
            min_soc_fraction=float(optimization_inputs["min_soc_fraction"]),
            max_soc_fraction=0.95,
            initial_soc_fraction=initial_soc_fraction,
            initial_throughput_kwh=max(float(initial_throughput_kwh), 0.0),
            roundtrip_efficiency=float(optimization_inputs["roundtrip_efficiency"]),
            max_charge_kw=float(optimization_inputs["max_power_kw"]),
            max_discharge_kw=float(optimization_inputs["max_power_kw"]),
            throughput_limit_kwh=throughput_limit_kwh,
            degradation_cost_per_kwh=float(optimization_inputs["degradation_cost_per_kwh"]),
            export_price_factor=float(optimization_inputs["export_price_factor"]),
        )
    )


def _run_rolling_horizon_schedule(
    *,
    prices: List[float],
    load_forecast: List[float],
    solar_forecast: List[float],
    capacity_kwh: float,
    throughput_limit_kwh: float,
    optimization_inputs: Mapping[str, float | str],
    initial_soc_fraction: float,
    rolling_window_hours: int = DEFAULT_ROLLING_WINDOW_HOURS,
) -> Dict[str, Any]:
    horizon = min(24, len(prices), len(load_forecast), len(solar_forecast))
    if horizon == 0:
        return {
            "schedule": [],
            "objective": {
                "purchase_cost_eur": 0.0,
                "export_revenue_eur": 0.0,
                "degradation_penalty_eur": 0.0,
                "net_cost_eur": 0.0,
            },
            "constraints": {
                "final_soc_kwh": capacity_kwh * initial_soc_fraction,
                "final_throughput_kwh": 0.0,
                "throughput_limit_kwh": throughput_limit_kwh,
            },
            "metadata": {
                "algorithm": "dynamic_programming_baseline",
                "rolling_horizon_enabled": True,
                "rolling_window_hours": rolling_window_hours,
                "rolling_commit_hours": ROLLING_HORIZON_COMMIT_HOURS,
                "recompute_count": 0,
            },
        }

    state_soc_kwh = capacity_kwh * initial_soc_fraction
    state_throughput_kwh = 0.0
    committed_rows: List[Dict[str, Any]] = []
    algorithm = "dynamic_programming_baseline"

    for start_hour in range(horizon):
        window_prices = _slice_horizon_window(prices, start_hour, rolling_window_hours)
        window_load_forecast = _slice_horizon_window(load_forecast, start_hour, rolling_window_hours)
        window_solar_forecast = _slice_horizon_window(solar_forecast, start_hour, rolling_window_hours)
        if not window_prices or not window_load_forecast:
            break

        result = _build_baseline_optimizer(
            capacity_kwh=capacity_kwh,
            throughput_limit_kwh=throughput_limit_kwh,
            optimization_inputs=optimization_inputs,
            initial_soc_kwh=state_soc_kwh,
            initial_throughput_kwh=state_throughput_kwh,
        ).optimize(
            price_eur_mwh=window_prices,
            load_kw=window_load_forecast,
            solar_kw=window_solar_forecast,
        )
        algorithm = str((result.get("metadata") or {}).get("algorithm") or algorithm)
        objective = _resolve_objective_breakdown(result)
        window_schedule = list(result.get("schedule") or [])
        if not window_schedule:
            break

        committed_row = dict(window_schedule[0])
        window_horizon_hours = len(window_prices)
        committed_row.update(
            {
                "hour": start_hour,
                "rolling_horizon_enabled": True,
                "rolling_window_index": start_hour,
                "rolling_window_start_hour": start_hour,
                "rolling_window_end_hour": start_hour + window_horizon_hours - 1,
                "rolling_window_horizon_hours": window_horizon_hours,
                "rolling_window_commit_hours": ROLLING_HORIZON_COMMIT_HOURS,
                "rolling_state_initial_soc_kwh": float(state_soc_kwh),
                "rolling_state_initial_throughput_kwh": float(state_throughput_kwh),
                "rolling_window_purchase_cost_eur": objective["purchase_cost_eur"],
                "rolling_window_export_revenue_eur": objective["export_revenue_eur"],
                "rolling_window_degradation_penalty_eur": objective["degradation_penalty_eur"],
                "rolling_window_net_cost_eur": objective["net_cost_eur"],
                "throughput_limit_kwh": throughput_limit_kwh,
            }
        )
        committed_rows.append(committed_row)
        state_soc_kwh = float(committed_row["soc_after_kwh"])
        state_throughput_kwh = float(committed_row["throughput_total_kwh"])

    total_objective = {
        "purchase_cost_eur": sum(float(row["purchase_cost_eur"]) for row in committed_rows),
        "export_revenue_eur": sum(float(row["export_revenue_eur"]) for row in committed_rows),
        "degradation_penalty_eur": sum(float(row["degradation_penalty_eur"]) for row in committed_rows),
    }
    total_objective["net_cost_eur"] = (
        total_objective["purchase_cost_eur"]
        - total_objective["export_revenue_eur"]
        + total_objective["degradation_penalty_eur"]
    )

    final_soc_kwh = float(committed_rows[-1]["soc_after_kwh"]) if committed_rows else state_soc_kwh
    final_throughput_kwh = float(committed_rows[-1]["throughput_total_kwh"]) if committed_rows else state_throughput_kwh
    for row in committed_rows:
        row["total_net_cost_eur"] = total_objective["net_cost_eur"]
        row["final_soc_kwh"] = final_soc_kwh

    return {
        "schedule": committed_rows,
        "objective": total_objective,
        "constraints": {
            "final_soc_kwh": final_soc_kwh,
            "final_throughput_kwh": final_throughput_kwh,
            "throughput_limit_kwh": throughput_limit_kwh,
        },
        "metadata": {
            "algorithm": algorithm,
            "rolling_horizon_enabled": True,
            "rolling_window_hours": rolling_window_hours,
            "rolling_commit_hours": ROLLING_HORIZON_COMMIT_HOURS,
            "recompute_count": len(committed_rows),
        },
    }


def _resolve_forecast_context(
    price_forecast: pl.DataFrame,
    *,
    horizon_mode: str,
    horizon_source: str | None = None,
    uncertainty_source: str | None = None,
    uncertainty_contract_version: str | None = None,
) -> Dict[str, Any]:
    rows = price_forecast.sort("forecast_timestamp").to_dicts() if len(price_forecast) else []
    first_row = rows[0] if rows else {}
    promotion_active = first_row.get("promotion_active")
    forecast_lineage = build_forecast_lineage(rows)

    return {
        "forecast_run_id": str(first_row.get("forecast_run_id") or forecast_lineage["forecast_run_id"] or "") or None,
        "forecast_model_name": str(first_row.get("model_name") or forecast_lineage["forecast_model_name"] or "") or None,
        "forecast_model_family": str(first_row.get("model_family") or forecast_lineage["forecast_model_family"] or "") or None,
        "forecast_model_version": str(first_row.get("forecast_model_version") or forecast_lineage["forecast_model_version"] or "") or None,
        "forecast_window_start_utc": str(first_row.get("forecast_window_start_utc") or forecast_lineage["forecast_window_start_utc"] or "") or None,
        "forecast_window_end_utc": str(first_row.get("forecast_window_end_utc") or forecast_lineage["forecast_window_end_utc"] or "") or None,
        "forecast_latency_ms": int(first_row.get("forecast_latency_ms") or forecast_lineage["forecast_latency_ms"] or 0),
        "forecast_freshness_minutes": float(first_row.get("forecast_freshness_minutes") or forecast_lineage["forecast_freshness_minutes"] or 0.0),
        "forecast_horizon_mode": horizon_mode,
        "forecast_horizon_source": str(horizon_source or "") or None,
        "forecast_uncertainty_source": str(uncertainty_source or first_row.get("uncertainty_source") or "") or None,
        "forecast_uncertainty_contract_version": str(
            uncertainty_contract_version or first_row.get("uncertainty_contract_version") or ""
        ) or None,
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
        "lineage_fields": ["forecast_run_id", "optimization_run_id", "forecast_model_version"],
        "objective": "purchase_cost - export_revenue + degradation_penalty",
    },
)
def optimization_schedule_asset(context, price_forecast: pl.DataFrame, client_state: pl.DataFrame) -> pl.DataFrame:
    horizon_mode = "conservative"
    horizon_details = _resolve_price_horizon(price_forecast, horizon_mode=horizon_mode)
    prices = list(horizon_details["prices"])
    if not prices:
        context.log.warning("No forecast price column found; returning empty optimization schedule")
        return build_empty_optimization_schedule()

    horizon = min(24, len(prices))
    client_profiles = _load_client_profiles()
    forecast_context = _resolve_forecast_context(
        price_forecast,
        horizon_mode=horizon_mode,
        horizon_source=horizon_details["source_column"],
        uncertainty_source=horizon_details["uncertainty_source"],
        uncertainty_contract_version=horizon_details["uncertainty_contract_version"],
    )

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
        throughput_limit_kwh = capacity_kwh * 1.2
        initial_soc_fraction = max(0.0, min(1.0, soc_percent / 100.0))

        result = _run_rolling_horizon_schedule(
            prices=prices[:horizon],
            load_forecast=load_forecast,
            solar_forecast=solar_forecast,
            capacity_kwh=capacity_kwh,
            throughput_limit_kwh=throughput_limit_kwh,
            optimization_inputs=optimization_inputs,
            initial_soc_fraction=initial_soc_fraction,
        )
        algorithm = str(result["metadata"]["algorithm"])
        optimization_run_id = build_optimization_run_id(
            forecast_run_id=forecast_context["forecast_run_id"],
            client_id=str(client_id),
            algorithm=algorithm,
            horizon_mode=forecast_context["forecast_horizon_mode"],
            optimization_inputs={
                "capacity_kwh": capacity_kwh,
                "min_soc_fraction": float(optimization_inputs["min_soc_fraction"]),
                "initial_soc_fraction": initial_soc_fraction,
                "roundtrip_efficiency": float(optimization_inputs["roundtrip_efficiency"]),
                "max_charge_kw": float(optimization_inputs["max_power_kw"]),
                "max_discharge_kw": float(optimization_inputs["max_power_kw"]),
                "throughput_limit_kwh": throughput_limit_kwh,
                "degradation_cost_per_kwh": float(optimization_inputs["degradation_cost_per_kwh"]),
                "export_price_factor": float(optimization_inputs["export_price_factor"]),
                "rolling_window_hours": int(result["metadata"]["rolling_window_hours"]),
                "rolling_commit_hours": int(result["metadata"]["rolling_commit_hours"]),
            },
            load_forecast=load_forecast,
            solar_forecast=solar_forecast,
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
            "rolling_horizon_enabled": bool(row["rolling_horizon_enabled"]),
            "rolling_window_index": int(row["rolling_window_index"]),
            "rolling_window_start_hour": int(row["rolling_window_start_hour"]),
            "rolling_window_end_hour": int(row["rolling_window_end_hour"]),
            "rolling_window_horizon_hours": int(row["rolling_window_horizon_hours"]),
            "rolling_window_commit_hours": int(row["rolling_window_commit_hours"]),
            "rolling_state_initial_soc_kwh": float(row["rolling_state_initial_soc_kwh"]),
            "rolling_state_initial_throughput_kwh": float(row["rolling_state_initial_throughput_kwh"]),
            "rolling_window_purchase_cost_eur": float(row["rolling_window_purchase_cost_eur"]),
            "rolling_window_export_revenue_eur": float(row["rolling_window_export_revenue_eur"]),
            "rolling_window_degradation_penalty_eur": float(row["rolling_window_degradation_penalty_eur"]),
            "rolling_window_net_cost_eur": float(row["rolling_window_net_cost_eur"]),
            "forecast_run_id": forecast_context["forecast_run_id"],
            "forecast_model_name": forecast_context["forecast_model_name"],
            "forecast_model_family": forecast_context["forecast_model_family"],
            "forecast_model_version": forecast_context["forecast_model_version"],
            "forecast_window_start_utc": forecast_context["forecast_window_start_utc"],
            "forecast_window_end_utc": forecast_context["forecast_window_end_utc"],
            "forecast_latency_ms": forecast_context["forecast_latency_ms"],
            "forecast_freshness_minutes": forecast_context["forecast_freshness_minutes"],
            "forecast_horizon_mode": forecast_context["forecast_horizon_mode"],
            "forecast_horizon_source": forecast_context["forecast_horizon_source"],
            "forecast_uncertainty_source": forecast_context["forecast_uncertainty_source"],
            "forecast_uncertainty_contract_version": forecast_context[
                "forecast_uncertainty_contract_version"
            ],
            "forecast_promotion_active": forecast_context["forecast_promotion_active"],
            "forecast_promotion_source": forecast_context["forecast_promotion_source"],
            "optimization_run_id": optimization_run_id,
            "algorithm": algorithm,
            "solver": None,
        } for row in result["schedule"]]

        output_frames.append(build_optimization_schedule_frame(schedule_rows))

    if not output_frames:
        return build_empty_optimization_schedule()

    combined = pl.concat(output_frames, how="vertical").sort(["client_id", "hour"])
    context.log.info(
        "optimization_schedule generated for %d clients horizon=%d total_rows=%d rolling_window_hours=%d",
        len(output_frames),
        horizon,
        len(combined),
        DEFAULT_ROLLING_WINDOW_HOURS,
    )
    return combined

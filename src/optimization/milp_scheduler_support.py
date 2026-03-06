"""Support helpers for the MILP battery scheduler."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
from scipy.optimize import linprog


class _VariableIndex:
    def __init__(self, horizon: int):
        self.horizon = horizon
        self.variable_count = 4 * horizon + (horizon + 1)

    def charge(self, timestep: int) -> int:
        return timestep

    def discharge(self, timestep: int) -> int:
        return self.horizon + timestep

    def grid_import(self, timestep: int) -> int:
        return 2 * self.horizon + timestep

    def grid_export(self, timestep: int) -> int:
        return 3 * self.horizon + timestep

    def soc(self, timestep: int) -> int:
        return 4 * self.horizon + timestep


def build_schedule_result(
    config: Any,
    prices: np.ndarray,
    loads: np.ndarray,
    solars: np.ndarray,
    charge: np.ndarray,
    discharge: np.ndarray,
    grid_import: np.ndarray,
    grid_export: np.ndarray,
    soc: np.ndarray,
    solver_name: str,
) -> Dict[str, Any]:
    horizon = len(prices)
    price_eur_kwh = prices / 1000.0

    schedule: List[Dict[str, float]] = []
    for timestep in range(horizon):
        purchase = float(grid_import[timestep] * price_eur_kwh[timestep])
        revenue = float(
            grid_export[timestep] * price_eur_kwh[timestep] * config.export_price_factor
        )
        degradation = float(
            (charge[timestep] + discharge[timestep]) * config.degradation_cost_per_kwh
        )
        schedule.append(
            {
                "hour": float(timestep),
                "action_kw": float(
                    (discharge[timestep] - charge[timestep])
                    / max(config.timestep_hours, 1e-9)
                ),
                "charge_kwh": float(charge[timestep]),
                "discharge_kwh": float(discharge[timestep]),
                "soc_before_kwh": float(soc[timestep]),
                "soc_after_kwh": float(soc[timestep + 1]),
                "throughput_total_kwh": float(
                    np.sum(charge[: timestep + 1] + discharge[: timestep + 1])
                ),
                "price_eur_mwh": float(prices[timestep]),
                "load_kwh": float(max(loads[timestep], 0.0) * config.timestep_hours),
                "solar_kwh": float(max(solars[timestep], 0.0) * config.timestep_hours),
                "grid_import_kwh": float(grid_import[timestep]),
                "grid_export_kwh": float(grid_export[timestep]),
                "purchase_cost_eur": purchase,
                "export_revenue_eur": revenue,
                "degradation_penalty_eur": degradation,
                "net_cost_eur": purchase - revenue + degradation,
            }
        )

    objective = {
        "purchase_cost_eur": sum(row["purchase_cost_eur"] for row in schedule),
        "export_revenue_eur": sum(row["export_revenue_eur"] for row in schedule),
        "degradation_penalty_eur": sum(
            row["degradation_penalty_eur"] for row in schedule
        ),
    }
    objective["net_cost_eur"] = (
        objective["purchase_cost_eur"]
        - objective["export_revenue_eur"]
        + objective["degradation_penalty_eur"]
    )

    return {
        "schedule": schedule,
        "objective": objective,
        "constraints": {
            "soc_min_kwh": config.capacity_kwh * config.min_soc_fraction,
            "soc_max_kwh": config.capacity_kwh * config.max_soc_fraction,
            "throughput_limit_kwh": float(
                config.throughput_limit_kwh or config.capacity_kwh * 1.2
            ),
            "final_soc_kwh": float(soc[-1]),
            "final_throughput_kwh": float(np.sum(charge + discharge)),
        },
        "metadata": {
            "horizon_hours": horizon,
            "algorithm": "mip_scheduler",
            "solver": solver_name,
        },
    }


def solve_with_linprog(
    config: Any,
    eta: float,
    prices: np.ndarray,
    loads: np.ndarray,
    solars: np.ndarray,
) -> Dict[str, Any]:
    horizon = len(prices)
    dt = config.timestep_hours
    max_charge = config.max_charge_kw * dt
    max_discharge = config.max_discharge_kw * dt
    capacity = config.capacity_kwh
    soc_min = config.min_soc_fraction * capacity
    soc_max = config.max_soc_fraction * capacity
    soc_init = min(max(config.initial_soc_fraction * capacity, soc_min), soc_max)
    throughput_limit = float(config.throughput_limit_kwh or capacity * 1.2)

    price_eur_kwh = prices / 1000.0
    net_demand = np.maximum(loads, 0.0) * dt - np.maximum(solars, 0.0) * dt
    index = _VariableIndex(horizon)

    cost_vector = np.zeros(index.variable_count)
    for timestep in range(horizon):
        cost_vector[index.charge(timestep)] = config.degradation_cost_per_kwh
        cost_vector[index.discharge(timestep)] = config.degradation_cost_per_kwh
        cost_vector[index.grid_import(timestep)] = price_eur_kwh[timestep]
        cost_vector[index.grid_export(timestep)] = (
            -price_eur_kwh[timestep] * config.export_price_factor
        )

    bounds = _build_variable_bounds(
        horizon=horizon,
        max_charge=max_charge,
        max_discharge=max_discharge,
        soc_init=soc_init,
        soc_min=soc_min,
        soc_max=soc_max,
    )
    equality_matrix, equality_targets = _build_equality_constraints(
        horizon=horizon,
        index=index,
        eta=eta,
        net_demand=net_demand,
    )
    throughput_matrix = np.zeros((1, index.variable_count))
    for timestep in range(horizon):
        throughput_matrix[0, index.charge(timestep)] = 1.0
        throughput_matrix[0, index.discharge(timestep)] = 1.0

    result = linprog(
        c=cost_vector,
        A_ub=throughput_matrix,
        b_ub=np.array([throughput_limit]),
        A_eq=equality_matrix,
        b_eq=equality_targets,
        bounds=bounds,
        method="highs",
    )
    if not result.success:
        raise RuntimeError(f"linprog fallback failed: {result.message}")

    solution = result.x
    charge = np.array([solution[index.charge(timestep)] for timestep in range(horizon)])
    discharge = np.array(
        [solution[index.discharge(timestep)] for timestep in range(horizon)]
    )
    grid_import = np.array(
        [solution[index.grid_import(timestep)] for timestep in range(horizon)]
    )
    grid_export = np.array(
        [solution[index.grid_export(timestep)] for timestep in range(horizon)]
    )
    soc = np.array([solution[index.soc(timestep)] for timestep in range(horizon + 1)])

    return build_schedule_result(
        config=config,
        prices=prices,
        loads=loads,
        solars=solars,
        charge=charge,
        discharge=discharge,
        grid_import=grid_import,
        grid_export=grid_export,
        soc=soc,
        solver_name="scipy_linprog_fallback",
    )


def _build_variable_bounds(
    horizon: int,
    max_charge: float,
    max_discharge: float,
    soc_init: float,
    soc_min: float,
    soc_max: float,
) -> list[tuple[float, float | None]]:
    bounds: list[tuple[float, float | None]] = []
    bounds.extend((0.0, max_charge) for _ in range(horizon))
    bounds.extend((0.0, max_discharge) for _ in range(horizon))
    bounds.extend((0.0, None) for _ in range(horizon))
    bounds.extend((0.0, None) for _ in range(horizon))
    bounds.append((soc_init, soc_init))
    bounds.extend((soc_min, soc_max) for _ in range(1, horizon + 1))
    return bounds


def _build_equality_constraints(
    horizon: int,
    index: _VariableIndex,
    eta: float,
    net_demand: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    equality_rows = []
    equality_targets = []

    for timestep in range(horizon):
        grid_balance = np.zeros(index.variable_count)
        grid_balance[index.grid_import(timestep)] = 1.0
        grid_balance[index.grid_export(timestep)] = -1.0
        grid_balance[index.charge(timestep)] = -1.0
        grid_balance[index.discharge(timestep)] = 1.0
        equality_rows.append(grid_balance)
        equality_targets.append(net_demand[timestep])

    for timestep in range(horizon):
        soc_balance = np.zeros(index.variable_count)
        soc_balance[index.soc(timestep + 1)] = 1.0
        soc_balance[index.soc(timestep)] = -1.0
        soc_balance[index.charge(timestep)] = -eta
        soc_balance[index.discharge(timestep)] = 1.0 / eta
        equality_rows.append(soc_balance)
        equality_targets.append(0.0)

    return np.asarray(equality_rows), np.asarray(equality_targets)
"""Solver-backed battery scheduler with cvxpy MILP and SciPy fallback."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
from scipy.optimize import linprog


@dataclass
class MilpSchedulerConfig:
    capacity_kwh: float = 200.0
    min_soc_fraction: float = 0.15
    max_soc_fraction: float = 0.95
    initial_soc_fraction: float = 0.5
    roundtrip_efficiency: float = 0.92
    max_charge_kw: float = 50.0
    max_discharge_kw: float = 50.0
    throughput_limit_kwh: Optional[float] = None
    degradation_cost_per_kwh: float = 0.01
    export_price_factor: float = 0.9
    timestep_hours: float = 1.0

    def with_defaults(self) -> "MilpSchedulerConfig":
        if self.throughput_limit_kwh is not None:
            return self
        return MilpSchedulerConfig(
            capacity_kwh=self.capacity_kwh,
            min_soc_fraction=self.min_soc_fraction,
            max_soc_fraction=self.max_soc_fraction,
            initial_soc_fraction=self.initial_soc_fraction,
            roundtrip_efficiency=self.roundtrip_efficiency,
            max_charge_kw=self.max_charge_kw,
            max_discharge_kw=self.max_discharge_kw,
            throughput_limit_kwh=self.capacity_kwh * 1.2,
            degradation_cost_per_kwh=self.degradation_cost_per_kwh,
            export_price_factor=self.export_price_factor,
            timestep_hours=self.timestep_hours,
        )


class MilpBatteryScheduler:
    """Battery scheduler with MILP-first behavior and deterministic fallback."""

    def __init__(self, config: MilpSchedulerConfig):
        self.config = config.with_defaults()
        self._eta = sqrt(max(min(self.config.roundtrip_efficiency, 1.0), 1e-6))

    def optimize(
        self,
        price_eur_mwh: Sequence[float],
        load_kw: Sequence[float],
        solar_kw: Optional[Sequence[float]] = None,
    ) -> Dict[str, Any]:
        if not price_eur_mwh or not load_kw:
            raise ValueError("price_eur_mwh and load_kw must be non-empty")

        horizon = min(len(price_eur_mwh), len(load_kw), len(solar_kw) if solar_kw is not None else len(load_kw))
        prices = np.asarray(price_eur_mwh[:horizon], dtype=float)
        loads = np.asarray(load_kw[:horizon], dtype=float)
        solars = np.zeros(horizon, dtype=float) if solar_kw is None else np.asarray(solar_kw[:horizon], dtype=float)

        try:
            return self._solve_with_cvxpy(prices, loads, solars)
        except Exception:
            return self._solve_with_linprog(prices, loads, solars)

    def _solve_with_cvxpy(self, prices: np.ndarray, loads: np.ndarray, solars: np.ndarray) -> Dict[str, Any]:
        import cvxpy as cp

        horizon = len(prices)
        dt = self.config.timestep_hours
        max_charge = self.config.max_charge_kw * dt
        max_discharge = self.config.max_discharge_kw * dt
        capacity = self.config.capacity_kwh
        soc_min = self.config.min_soc_fraction * capacity
        soc_max = self.config.max_soc_fraction * capacity
        soc_init = min(max(self.config.initial_soc_fraction * capacity, soc_min), soc_max)
        throughput_limit = float(self.config.throughput_limit_kwh or capacity * 1.2)

        price_eur_kwh = prices / 1000.0
        net_demand = np.maximum(loads, 0.0) * dt - np.maximum(solars, 0.0) * dt

        charge = cp.Variable(horizon, nonneg=True)
        discharge = cp.Variable(horizon, nonneg=True)
        grid_import = cp.Variable(horizon, nonneg=True)
        grid_export = cp.Variable(horizon, nonneg=True)
        soc = cp.Variable(horizon + 1)
        mode = cp.Variable(horizon, boolean=True)

        constraints = [soc[0] == soc_init]

        for t in range(horizon):
            constraints.extend(
                [
                    soc[t + 1] == soc[t] + self._eta * charge[t] - discharge[t] / self._eta,
                    soc[t + 1] >= soc_min,
                    soc[t + 1] <= soc_max,
                    grid_import[t] - grid_export[t] - charge[t] + discharge[t] == net_demand[t],
                    charge[t] <= max_charge * mode[t],
                    discharge[t] <= max_discharge * (1 - mode[t]),
                ]
            )

        constraints.append(cp.sum(charge + discharge) <= throughput_limit)

        objective = cp.Minimize(
            cp.sum(
                cp.multiply(price_eur_kwh, grid_import)
                - cp.multiply(price_eur_kwh * self.config.export_price_factor, grid_export)
                + self.config.degradation_cost_per_kwh * (charge + discharge)
            )
        )

        problem = cp.Problem(objective, constraints)
        solver = cp.ECOS_BB if "ECOS_BB" in cp.installed_solvers() else None
        if solver is None:
            raise RuntimeError("No MILP solver available in cvxpy")

        problem.solve(solver=solver, verbose=False)
        if problem.status not in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE}:
            raise RuntimeError(f"MILP solve failed: {problem.status}")

        return self._build_result(
            prices=prices,
            loads=loads,
            solars=solars,
            charge=np.asarray(charge.value).flatten(),
            discharge=np.asarray(discharge.value).flatten(),
            grid_import=np.asarray(grid_import.value).flatten(),
            grid_export=np.asarray(grid_export.value).flatten(),
            soc=np.asarray(soc.value).flatten(),
            solver_name="cvxpy_milp",
        )

    def _solve_with_linprog(self, prices: np.ndarray, loads: np.ndarray, solars: np.ndarray) -> Dict[str, Any]:
        horizon = len(prices)
        dt = self.config.timestep_hours
        max_charge = self.config.max_charge_kw * dt
        max_discharge = self.config.max_discharge_kw * dt
        capacity = self.config.capacity_kwh
        soc_min = self.config.min_soc_fraction * capacity
        soc_max = self.config.max_soc_fraction * capacity
        soc_init = min(max(self.config.initial_soc_fraction * capacity, soc_min), soc_max)
        throughput_limit = float(self.config.throughput_limit_kwh or capacity * 1.2)

        price_eur_kwh = prices / 1000.0
        net_demand = np.maximum(loads, 0.0) * dt - np.maximum(solars, 0.0) * dt

        n = horizon
        # Variable ordering: charge[n], discharge[n], grid_import[n], grid_export[n], soc[n+1]
        n_vars = 4 * n + (n + 1)

        def idx_charge(t: int) -> int:
            return t

        def idx_discharge(t: int) -> int:
            return n + t

        def idx_import(t: int) -> int:
            return 2 * n + t

        def idx_export(t: int) -> int:
            return 3 * n + t

        def idx_soc(t: int) -> int:
            return 4 * n + t

        c = np.zeros(n_vars)
        for t in range(n):
            c[idx_charge(t)] = self.config.degradation_cost_per_kwh
            c[idx_discharge(t)] = self.config.degradation_cost_per_kwh
            c[idx_import(t)] = price_eur_kwh[t]
            c[idx_export(t)] = -price_eur_kwh[t] * self.config.export_price_factor

        bounds = []
        for _ in range(n):
            bounds.append((0.0, max_charge))
        for _ in range(n):
            bounds.append((0.0, max_discharge))
        for _ in range(n):
            bounds.append((0.0, None))
        for _ in range(n):
            bounds.append((0.0, None))
        bounds.append((soc_init, soc_init))
        for _ in range(1, n + 1):
            bounds.append((soc_min, soc_max))

        a_eq = []
        b_eq = []

        # Grid balance per hour.
        for t in range(n):
            row = np.zeros(n_vars)
            row[idx_import(t)] = 1.0
            row[idx_export(t)] = -1.0
            row[idx_charge(t)] = -1.0
            row[idx_discharge(t)] = 1.0
            a_eq.append(row)
            b_eq.append(net_demand[t])

        # SoC dynamics.
        for t in range(n):
            row = np.zeros(n_vars)
            row[idx_soc(t + 1)] = 1.0
            row[idx_soc(t)] = -1.0
            row[idx_charge(t)] = -self._eta
            row[idx_discharge(t)] = 1.0 / self._eta
            a_eq.append(row)
            b_eq.append(0.0)

        a_ub = np.zeros((1, n_vars))
        for t in range(n):
            a_ub[0, idx_charge(t)] = 1.0
            a_ub[0, idx_discharge(t)] = 1.0
        b_ub = np.array([throughput_limit])

        result = linprog(
            c=c,
            A_ub=a_ub,
            b_ub=b_ub,
            A_eq=np.asarray(a_eq),
            b_eq=np.asarray(b_eq),
            bounds=bounds,
            method="highs",
        )
        if not result.success:
            raise RuntimeError(f"linprog fallback failed: {result.message}")

        solution = result.x
        charge = np.array([solution[idx_charge(t)] for t in range(n)])
        discharge = np.array([solution[idx_discharge(t)] for t in range(n)])
        grid_import = np.array([solution[idx_import(t)] for t in range(n)])
        grid_export = np.array([solution[idx_export(t)] for t in range(n)])
        soc = np.array([solution[idx_soc(t)] for t in range(n + 1)])

        return self._build_result(
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

    def _build_result(
        self,
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
        for t in range(horizon):
            purchase = float(grid_import[t] * price_eur_kwh[t])
            revenue = float(grid_export[t] * price_eur_kwh[t] * self.config.export_price_factor)
            degradation = float((charge[t] + discharge[t]) * self.config.degradation_cost_per_kwh)
            schedule.append(
                {
                    "hour": float(t),
                    "action_kw": float((discharge[t] - charge[t]) / max(self.config.timestep_hours, 1e-9)),
                    "charge_kwh": float(charge[t]),
                    "discharge_kwh": float(discharge[t]),
                    "soc_before_kwh": float(soc[t]),
                    "soc_after_kwh": float(soc[t + 1]),
                    "throughput_total_kwh": float(np.sum(charge[: t + 1] + discharge[: t + 1])),
                    "price_eur_mwh": float(prices[t]),
                    "load_kwh": float(max(loads[t], 0.0) * self.config.timestep_hours),
                    "solar_kwh": float(max(solars[t], 0.0) * self.config.timestep_hours),
                    "grid_import_kwh": float(grid_import[t]),
                    "grid_export_kwh": float(grid_export[t]),
                    "purchase_cost_eur": purchase,
                    "export_revenue_eur": revenue,
                    "degradation_penalty_eur": degradation,
                    "net_cost_eur": purchase - revenue + degradation,
                }
            )

        objective = {
            "purchase_cost_eur": sum(row["purchase_cost_eur"] for row in schedule),
            "export_revenue_eur": sum(row["export_revenue_eur"] for row in schedule),
            "degradation_penalty_eur": sum(row["degradation_penalty_eur"] for row in schedule),
        }
        objective["net_cost_eur"] = objective["purchase_cost_eur"] - objective["export_revenue_eur"] + objective["degradation_penalty_eur"]

        return {
            "schedule": schedule,
            "objective": objective,
            "constraints": {
                "soc_min_kwh": self.config.capacity_kwh * self.config.min_soc_fraction,
                "soc_max_kwh": self.config.capacity_kwh * self.config.max_soc_fraction,
                "throughput_limit_kwh": float(self.config.throughput_limit_kwh or self.config.capacity_kwh * 1.2),
                "final_soc_kwh": float(soc[-1]),
                "final_throughput_kwh": float(np.sum(charge + discharge)),
            },
            "metadata": {
                "horizon_hours": horizon,
                "algorithm": "mip_scheduler",
                "solver": solver_name,
            },
        }

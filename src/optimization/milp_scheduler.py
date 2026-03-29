"""Solver-backed battery scheduler with cvxpy MILP and SciPy fallback."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from .milp_scheduler_support import build_schedule_result, solve_with_linprog


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

        return build_schedule_result(
            config=self.config,
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
        return solve_with_linprog(
            config=self.config,
            eta=self._eta,
            prices=prices,
            loads=loads,
            solars=solars,
        )

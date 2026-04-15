"""Baseline dynamic-programming optimizer for battery scheduling."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple


@dataclass
class BaselineOptimizationConfig:
    """Configuration for baseline DP optimization."""

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
    soc_step_kwh: float = 5.0
    throughput_step_kwh: float = 5.0

    def with_defaults(self) -> "BaselineOptimizationConfig":
        if self.throughput_limit_kwh is not None:
            return self
        return BaselineOptimizationConfig(
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
            soc_step_kwh=self.soc_step_kwh,
            throughput_step_kwh=self.throughput_step_kwh,
        )


class BaselineDPOptimizer:
    """Dynamic-programming baseline optimizer with explicit battery constraints."""

    def __init__(self, config: BaselineOptimizationConfig):
        self.config = config.with_defaults()
        self._eta = sqrt(max(min(self.config.roundtrip_efficiency, 1.0), 1e-6))

    def _advance_hour_states(
        self,
        *,
        hour: int,
        states: Mapping[Tuple[int, int], Dict[str, float]],
        actions_kw: Sequence[float],
        price_eur_mwh: float,
        load_kw: float,
        solar_kw: float,
        soc_min_kwh: float,
        soc_max_kwh: float,
        throughput_limit_kwh: float,
    ) -> tuple[
        MutableMapping[Tuple[int, int], Dict[str, float]],
        Dict[Tuple[int, int], Tuple[Tuple[int, int], Dict[str, float]]],
    ]:
        next_states: MutableMapping[Tuple[int, int], Dict[str, float]] = {}
        step_backpointer: Dict[Tuple[int, int], Tuple[Tuple[int, int], Dict[str, float]]] = {}

        for state_key, node in states.items():
            for action_kw in actions_kw:
                transition = self._transition(
                    hour=hour,
                    action_kw=action_kw,
                    soc_kwh=node["soc"],
                    throughput_so_far_kwh=node["throughput"],
                    price_eur_mwh=price_eur_mwh,
                    load_kw=load_kw,
                    solar_kw=solar_kw,
                    soc_min_kwh=soc_min_kwh,
                    soc_max_kwh=soc_max_kwh,
                    throughput_limit_kwh=throughput_limit_kwh,
                )
                if transition is None:
                    continue

                cumulative_cost = node["cost"] + transition["net_cost_eur"]
                next_key = (
                    self._quantize(transition["soc_after_kwh"], self.config.soc_step_kwh),
                    self._quantize(transition["throughput_total_kwh"], self.config.throughput_step_kwh),
                )
                existing = next_states.get(next_key)
                if existing is not None and cumulative_cost >= existing["cost"]:
                    continue

                next_states[next_key] = {
                    "cost": cumulative_cost,
                    "soc": transition["soc_after_kwh"],
                    "throughput": transition["throughput_total_kwh"],
                }
                step_backpointer[next_key] = (state_key, transition)

        if not next_states:
            raise RuntimeError(f"No feasible states remaining at hour {hour}")

        return next_states, step_backpointer

    @staticmethod
    def _reconstruct_schedule(
        backpointers: Sequence[Dict[Tuple[int, int], Tuple[Tuple[int, int], Dict[str, float]]]],
        final_key: Tuple[int, int],
    ) -> List[Dict[str, float]]:
        schedule_reversed: List[Dict[str, float]] = []

        for hour in range(len(backpointers) - 1, -1, -1):
            prev_key, transition = backpointers[hour][final_key]
            schedule_reversed.append(transition)
            final_key = prev_key

        return list(reversed(schedule_reversed))

    @staticmethod
    def _build_result(
        schedule: Sequence[Dict[str, float]],
        *,
        soc_min: float,
        soc_max: float,
        throughput_limit: float,
        final_soc: float,
        final_throughput: float,
        horizon: int,
        state_bins: int,
    ) -> Dict[str, Any]:
        objective = {
            "purchase_cost_eur": sum(row["purchase_cost_eur"] for row in schedule),
            "export_revenue_eur": sum(row["export_revenue_eur"] for row in schedule),
            "degradation_penalty_eur": sum(row["degradation_penalty_eur"] for row in schedule),
        }
        objective["net_cost_eur"] = objective["purchase_cost_eur"] - objective["export_revenue_eur"] + objective["degradation_penalty_eur"]

        return {
            "schedule": list(schedule),
            "objective": objective,
            "constraints": {
                "soc_min_kwh": soc_min,
                "soc_max_kwh": soc_max,
                "throughput_limit_kwh": throughput_limit,
                "final_soc_kwh": final_soc,
                "final_throughput_kwh": final_throughput,
            },
            "metadata": {
                "horizon_hours": horizon,
                "algorithm": "dynamic_programming_baseline",
                "state_bins": state_bins,
            },
        }

    def optimize(
        self,
        price_eur_mwh: Sequence[float],
        load_kw: Sequence[float],
        solar_kw: Optional[Sequence[float]] = None,
    ) -> Dict[str, Any]:
        if not price_eur_mwh or not load_kw:
            raise ValueError("price_eur_mwh and load_kw must be non-empty")

        horizon = min(len(price_eur_mwh), len(load_kw), len(solar_kw) if solar_kw is not None else len(load_kw))
        prices = [float(v) for v in price_eur_mwh[:horizon]]
        loads = [float(v) for v in load_kw[:horizon]]
        solars = [0.0] * horizon if solar_kw is None else [float(v) for v in solar_kw[:horizon]]

        soc_min = self.config.capacity_kwh * self.config.min_soc_fraction
        soc_max = self.config.capacity_kwh * self.config.max_soc_fraction
        soc_init = min(max(self.config.capacity_kwh * self.config.initial_soc_fraction, soc_min), soc_max)
        throughput_limit = float(self.config.throughput_limit_kwh or self.config.capacity_kwh * 1.2)

        states: MutableMapping[Tuple[int, int], Dict[str, float]] = {
            (self._quantize(soc_init, self.config.soc_step_kwh), 0): {
                "cost": 0.0,
                "soc": soc_init,
                "throughput": 0.0,
            }
        }
        backpointers: List[Dict[Tuple[int, int], Tuple[Tuple[int, int], Dict[str, float]]]] = []

        actions_kw = [
            -self.config.max_charge_kw,
            -self.config.max_charge_kw / 2.0,
            0.0,
            self.config.max_discharge_kw / 2.0,
            self.config.max_discharge_kw,
        ]

        for hour in range(horizon):
            next_states, step_backpointer = self._advance_hour_states(
                hour=hour,
                states=states,
                actions_kw=actions_kw,
                price_eur_mwh=prices[hour],
                load_kw=loads[hour],
                solar_kw=solars[hour],
                soc_min_kwh=soc_min,
                soc_max_kwh=soc_max,
                throughput_limit_kwh=throughput_limit,
            )

            backpointers.append(step_backpointer)
            states = next_states

        final_key, final_node = min(states.items(), key=lambda item: item[1]["cost"])
        schedule = self._reconstruct_schedule(backpointers, final_key)
        return self._build_result(
            schedule,
            soc_min=soc_min,
            soc_max=soc_max,
            throughput_limit=throughput_limit,
            final_soc=final_node["soc"],
            final_throughput=final_node["throughput"],
            horizon=horizon,
            state_bins=len(states),
        )

    def _transition(
        self,
        hour: int,
        action_kw: float,
        soc_kwh: float,
        throughput_so_far_kwh: float,
        price_eur_mwh: float,
        load_kw: float,
        solar_kw: float,
        soc_min_kwh: float,
        soc_max_kwh: float,
        throughput_limit_kwh: float,
    ) -> Optional[Dict[str, float]]:
        dt = self.config.timestep_hours
        charge_input_kwh = 0.0
        discharge_output_kwh = 0.0

        if action_kw < 0:
            requested_charge = min(abs(action_kw) * dt, self.config.max_charge_kw * dt)
            max_charge_allowed = max(0.0, (soc_max_kwh - soc_kwh) / self._eta)
            charge_input_kwh = min(requested_charge, max_charge_allowed)
            soc_after_kwh = soc_kwh + charge_input_kwh * self._eta
        elif action_kw > 0:
            requested_discharge = min(action_kw * dt, self.config.max_discharge_kw * dt)
            max_discharge_allowed = max(0.0, (soc_kwh - soc_min_kwh) * self._eta)
            discharge_output_kwh = min(requested_discharge, max_discharge_allowed)
            soc_after_kwh = soc_kwh - discharge_output_kwh / self._eta
        else:
            soc_after_kwh = soc_kwh

        if soc_after_kwh < soc_min_kwh - 1e-9 or soc_after_kwh > soc_max_kwh + 1e-9:
            return None

        throughput_total_kwh = throughput_so_far_kwh + charge_input_kwh + discharge_output_kwh
        if throughput_total_kwh > throughput_limit_kwh + 1e-9:
            return None

        price_eur_kwh = price_eur_mwh / 1000.0
        net_demand_kwh = max(load_kw, 0.0) * dt - max(solar_kw, 0.0) * dt

        grid_import_kwh = max(0.0, net_demand_kwh + charge_input_kwh - discharge_output_kwh)
        grid_export_kwh = max(0.0, discharge_output_kwh - (net_demand_kwh + charge_input_kwh))

        purchase_cost_eur = grid_import_kwh * price_eur_kwh
        export_revenue_eur = grid_export_kwh * price_eur_kwh * self.config.export_price_factor
        degradation_penalty_eur = (charge_input_kwh + discharge_output_kwh) * self.config.degradation_cost_per_kwh
        net_cost_eur = purchase_cost_eur - export_revenue_eur + degradation_penalty_eur
        realized_action_kw = (discharge_output_kwh - charge_input_kwh) / max(dt, 1e-9)

        return {
            "hour": float(hour),
            "action_kw": realized_action_kw,
            "charge_kwh": charge_input_kwh,
            "discharge_kwh": discharge_output_kwh,
            "soc_before_kwh": soc_kwh,
            "soc_after_kwh": soc_after_kwh,
            "throughput_total_kwh": throughput_total_kwh,
            "price_eur_mwh": price_eur_mwh,
            "load_kwh": max(load_kw, 0.0) * dt,
            "solar_kwh": max(solar_kw, 0.0) * dt,
            "grid_import_kwh": grid_import_kwh,
            "grid_export_kwh": grid_export_kwh,
            "purchase_cost_eur": purchase_cost_eur,
            "export_revenue_eur": export_revenue_eur,
            "degradation_penalty_eur": degradation_penalty_eur,
            "net_cost_eur": net_cost_eur,
        }

    @staticmethod
    def _quantize(value: float, step: float) -> int:
        return int(round(max(value, 0.0) / max(step, 1e-9)))

"""Advanced battery degradation models for Phase 4B.

Provides BatteryModel base class and chemistry-specific implementations:
- LFP
- Lead-Acid
- VRFB

Implements degradation cost calculation, SOC segmentation, knee-point prediction,
and C-rate stress factor. Uses pydantic BatteryConfig from config_models.py.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import List, Tuple
from energy_ml.config_models import BatteryConfig

@dataclass
class DegradationResult:
    cycles: float
    soh: float
    degradation_cost: float
    curve: List[Tuple[float,float]]  # list of (cycle, soh)


class BatteryModel:
    def __init__(self, config: BatteryConfig):
        self.config = config
        self.capacity_kwh = config.capacity_kwh
        self.base_cost_per_cycle = config.degradation_cost_per_cycle
        self.cycles_to_eol = config.cycles_to_eol

    def soc_segments(self, segments: int = 10):
        # return SOC segment midpoints 0-1
        step = 1.0 / segments
        return [step*(i+0.5) for i in range(segments)]

    def c_rate_stress(self, c_rate: float) -> float:
        # Simple exponential penalty for high C-rate
        # below 0.5C negligible, above 1C significant
        return 1.0 + 0.5 * max(0.0, (c_rate - 0.5))**1.5

    def doD_effect(self, dod: float) -> float:
        # nonlinear DoD effect: deeper cycles cause more wear
        # approximate using power law (papers reference)
        return (dod**1.2)

    def knee_point(self) -> float:
        # Predict knee point (fraction of cycles_to_eol) where degradation accelerates
        # Use simple heuristic: high-cycle chemistries have later knees
        base = self.cycles_to_eol
        if base >= 10000:
            return 0.6  # knee at 60% of life
        if base >= 2000:
            return 0.5
        return 0.4

    def mc_deg(self, dod: float, soh_remaining: float, c_rate: float) -> float:
        """Marginal cost of degradation per cycle (USD).
        MC_deg = (C_battery * DoD_effect) / (cycles_to_eol * SoH_remaining)
        apply c-rate stress multiplier
        """
        C_battery = self.capacity_kwh * self.base_cost_per_cycle
        dod_eff = self.doD_effect(dod)
        stress = self.c_rate_stress(c_rate)
        mc = (C_battery * dod_eff) / (self.cycles_to_eol * soh_remaining)
        return mc * stress

    def simulate_cycles(self, cycles: int = 1000, dod: float = 1.0, c_rate: float = 0.5, segments: int =10) -> DegradationResult:
        """Run multi-cycle simulation returning SOH curve and aggregated cost."""
        curve = []
        soh = 1.0
        total_cost = 0.0
        knee = self.knee_point()
        for cycle in range(1, cycles+1):
            # adapt degradation acceleration after knee
            frac = cycle / self.cycles_to_eol
            accel = 1.0
            if frac > knee:
                accel = 1.0 + (frac - knee)*3.0  # accelerates faster
            # per-cycle soh drop (simple model)
            delta = (1.0 / self.cycles_to_eol) * (dod**1.1) * accel * (c_rate/0.5)
            soh = max(0.0, soh - delta)
            mc = self.mc_deg(dod, max(0.2, soh), c_rate)
            total_cost += mc
            curve.append((cycle, soh))
        return DegradationResult(cycles=cycles, soh=soh, degradation_cost=total_cost, curve=curve)


class LFPModel(BatteryModel):
    def __init__(self, config: BatteryConfig):
        super().__init__(config)
        # LFP-specific tuning

    def knee_point(self) -> float:
        return 0.6


class LeadAcidModel(BatteryModel):
    def __init__(self, config: BatteryConfig):
        super().__init__(config)

    def doD_effect(self, dod: float) -> float:
        # lead-acid more sensitive to DoD
        return (dod**1.4)

    def knee_point(self) -> float:
        return 0.35


class VRFBModel(BatteryModel):
    def __init__(self, config: BatteryConfig):
        super().__init__(config)

    def c_rate_stress(self, c_rate: float) -> float:
        # VRFB largely insensitive to C-rate
        return 1.0 + 0.1 * max(0.0, (c_rate - 1.0))

    def knee_point(self) -> float:
        return 0.7
    
    def simulate_cycles(self, cycles: int = 1000, dod: float = 1.0, c_rate: float = 0.5, segments: int = 10) -> DegradationResult:
        """VRFB has minimal degradation - override parent to reflect reality."""
        curve = []
        soh = 1.0
        total_cost = 0.0
        
        for cycle in range(1, cycles + 1):
            # VRFB degradation is dramatically lower (maybe 0.005% per cycle vs 0.1% for LFP)
            # This reflects the 20,000+ cycle lifetime
            delta = (1.0 / self.cycles_to_eol) * 0.1 * (dod ** 1.05)  # Much gentler slope
            soh = max(0.0, soh - delta)
            mc = self.mc_deg(dod, max(0.2, soh), c_rate)
            total_cost += mc
            curve.append((cycle, soh))
        
        return DegradationResult(cycles=cycles, soh=soh, degradation_cost=total_cost, curve=curve)

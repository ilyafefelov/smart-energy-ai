"""Ukraine 2026 tariff models for Phase 4D.

Implements NKREKU tariff structure with on/off-peak pricing,
time-of-use optimization, and cost calculation for UserProfile.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple
import math


@dataclass
class TariffResult:
    """Result of tariff cost calculation."""
    total_cost_uah: float
    on_peak_hours: int
    off_peak_hours: int
    on_peak_cost: float
    off_peak_cost: float
    daily_costs: List[float]  # 365-day breakdown
    hourly_breakdown: List[Tuple[int, float]]  # (hour, cost)


class UkraineTariffModel:
    """NKREKU 2026 tariff model for Group A (commercial) customers.
    
    Pricing structure:
    - On-peak (6-23): 742.91 UAH/MWh (after April 1, 2026)
    - Off-peak (0-6, 23-24): 713.68 UAH/MWh
    - Dispatch tariff: 110.03 UAH/MWh (added to both)
    """
    
    # Transmission tariff rates (UAH/MWh)
    ON_PEAK_RATE = 742.91      # 6:00-23:00
    OFF_PEAK_RATE = 713.68     # 0:00-6:00, 23:00-24:00
    DISPATCH_TARIFF = 110.03   # Fixed on all hours
    
    # Peak hours: 6 AM to 11 PM (17 hours)
    PEAK_START = 6
    PEAK_END = 23
    
    def __init__(self):
        """Initialize tariff model."""
        self.on_peak_rate = self.ON_PEAK_RATE + self.DISPATCH_TARIFF
        self.off_peak_rate = self.OFF_PEAK_RATE + self.DISPATCH_TARIFF
    
    def get_hourly_rate(self, hour: int) -> float:
        """Get tariff rate for a given hour (0-23).
        
        Args:
            hour: Hour of day (0-23)
            
        Returns:
            Rate in UAH/MWh
        """
        if self.PEAK_START <= hour < self.PEAK_END:
            return self.on_peak_rate
        return self.off_peak_rate
    
    def calculate_daily_cost(self, hourly_loads: List[float]) -> Tuple[float, List[float]]:
        """Calculate daily cost from hourly loads (kWh).
        
        Args:
            hourly_loads: List of 24 hourly loads in kWh
            
        Returns:
            (total_cost_uah, hourly_costs_list)
        """
        total = 0.0
        costs = []
        for hour, load_kwh in enumerate(hourly_loads):
            rate = self.get_hourly_rate(hour)
            # Convert kWh to MWh: load_kwh / 1000
            # Cost = (kWh / 1000) * (UAH/MWh)
            cost = (load_kwh / 1000.0) * rate
            costs.append(cost)
            total += cost
        return total, costs
    
    def calculate_365day_cost(self, hourly_loads_8760: List[float]) -> TariffResult:
        """Calculate annual cost from 8760 hourly loads.
        
        Args:
            hourly_loads_8760: List of 8760 hourly loads (kWh)
            
        Returns:
            TariffResult with breakdown
        """
        if len(hourly_loads_8760) != 8760:
            raise ValueError(f"Expected 8760 hours, got {len(hourly_loads_8760)}")
        
        total_cost = 0.0
        on_peak_cost = 0.0
        off_peak_cost = 0.0
        on_peak_hours = 0
        off_peak_hours = 0
        daily_costs = []
        hourly_breakdown = []
        
        for hour_idx, load_kwh in enumerate(hourly_loads_8760):
            day_of_year = hour_idx // 24
            hour_of_day = hour_idx % 24
            
            rate = self.get_hourly_rate(hour_of_day)
            cost = (load_kwh / 1000.0) * rate
            
            total_cost += cost
            hourly_breakdown.append((hour_idx, cost))
            
            # Track peak vs off-peak
            if self.PEAK_START <= hour_of_day < self.PEAK_END:
                on_peak_cost += cost
                on_peak_hours += 1
            else:
                off_peak_cost += cost
                off_peak_hours += 1
            
            # Accumulate daily costs
            if (hour_idx + 1) % 24 == 0:
                daily_costs.append(sum(c for _, c in hourly_breakdown[-24:]))
        
        return TariffResult(
            total_cost_uah=total_cost,
            on_peak_hours=on_peak_hours,
            off_peak_hours=off_peak_hours,
            on_peak_cost=on_peak_cost,
            off_peak_cost=off_peak_cost,
            daily_costs=daily_costs,
            hourly_breakdown=hourly_breakdown
        )
    
    def estimate_savings_with_battery(self,
                                      hourly_loads_8760: List[float],
                                      battery_capacity_kwh: float,
                                      charge_efficiency: float = 0.92,
                                      discharge_efficiency: float = 0.92) -> Dict[str, float]:
        """Estimate cost savings from battery optimization.
        
        Simple strategy: charge during off-peak, discharge during on-peak.
        
        Args:
            hourly_loads_8760: Annual load profile
            battery_capacity_kwh: Battery size in kWh
            charge_efficiency: Round-trip efficiency (0.92 = 92%)
            discharge_efficiency: Discharge efficiency
            
        Returns:
            Dict with savings breakdown
        """
        # Calculate original cost (no battery)
        original = self.calculate_365day_cost(hourly_loads_8760)
        
        # Simulate battery charging/discharging
        battery_soc = battery_capacity_kwh * 0.5  # Start at 50% SoC
        on_peak_discharge = 0.0
        off_peak_charge = 0.0
        new_cost = 0.0
        
        for hour_idx, load_kwh in enumerate(hourly_loads_8760):
            hour_of_day = hour_idx % 24
            
            # Simple greedy strategy
            is_peak = self.PEAK_START <= hour_of_day < self.PEAK_END
            
            if is_peak and battery_soc > 0:
                # Try to discharge during peak
                discharge_available = min(battery_soc, load_kwh)
                discharge_real = discharge_available * discharge_efficiency
                load_from_grid = max(0, load_kwh - discharge_real)
                battery_soc -= discharge_available
                on_peak_discharge += discharge_available
            else:
                load_from_grid = load_kwh
                
                # Try to charge during off-peak
                if not is_peak and battery_soc < battery_capacity_kwh:
                    charge_available = battery_capacity_kwh - battery_soc
                    charge_used = min(charge_available, load_kwh * 0.2)  # Charge up to 20% of load
                    battery_soc += charge_used / charge_efficiency
                    off_peak_charge += charge_used
            
            rate = self.get_hourly_rate(hour_of_day)
            new_cost += (load_from_grid / 1000.0) * rate
        
        savings_uah = original.total_cost_uah - new_cost
        savings_percent = (savings_uah / original.total_cost_uah) * 100 if original.total_cost_uah > 0 else 0
        
        return {
            'original_cost_uah': original.total_cost_uah,
            'optimized_cost_uah': new_cost,
            'savings_uah': savings_uah,
            'savings_percent': savings_percent,
            'on_peak_discharge_kwh': on_peak_discharge,
            'off_peak_charge_kwh': off_peak_charge,
        }

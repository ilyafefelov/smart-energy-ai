"""
Battery LFP Physics & Degradation Modeling

Advanced battery degradation model for Lithium Iron Phosphate (LFP) batteries.
Implements economic cost calculations and SEI layer growth prediction.

Thesis Relevance: Provides the economic foundation for optimization decisions,
modeling real battery physics rather than simplified linear degradation.
"""

import numpy as np
import math
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class BatterySpecs:
    """Battery specification parameters"""
    capacity_kwh: float = 280.0  # kWh capacity
    nominal_voltage: float = 3.2  # V per cell
    max_cycles: int = 6000  # Rated cycle life
    capex_per_kwh: float = 150.0  # $/kWh capital cost
    roundtrip_efficiency: float = 0.95  # 95% round-trip efficiency
    max_c_rate: float = 1.0  # Maximum C-rate for charging/discharging


@dataclass
class OperatingConditions:
    """Current operating conditions"""
    soc: float  # State of charge (0-1)
    temperature: float  # °C
    cycle_depth: float  # Depth of discharge (0-1)
    c_rate: float  # Current C-rate


class DegradationModel:
    """
    Advanced degradation model for LFP batteries incorporating:
    - Stress factor modeling (temperature + SoC dependence)
    - SEI layer growth (calendar aging)
    - Marginal cost of degradation calculation
    - "Knee Point" prediction (80% SoH threshold)
    """
    
    def __init__(self, battery_specs: BatterySpecs):
        self.specs = battery_specs
        
        # SEI growth model parameters (Arrhenius equation)
        self.sei_activation_energy = 35000  # J/mol (typical for LFP)
        self.sei_pre_factor = 1e-6  # Pre-exponential factor
        self.gas_constant = 8.314  # J/(mol·K)
        
        # Stress factor coefficients
        self.temp_coefficient = 0.02  # %/°C above 25°C
        self.soc_threshold = 0.9  # SoC threshold for accelerated aging
        self.soc_penalty = 2.0  # Penalty multiplier above threshold
        
    def get_stress_factor(self, conditions: OperatingConditions) -> float:
        """
        Calculate stress factor based on operating conditions.
        
        For LFP batteries:
        - Temperature stress increases exponentially above 35°C
        - SoC stress increases sharply above 90%
        - C-rate stress affects cycle life
        
        Returns:
            Stress multiplier (1.0 = nominal conditions)
        """
        # Temperature stress (Arrhenius relationship)
        temp_stress = 1.0
        if conditions.temperature > 25.0:
            temp_excess = conditions.temperature - 25.0
            temp_stress = 1.0 + (temp_excess * self.temp_coefficient)
        
        # SoC stress (sharp increase above 90%)
        soc_stress = 1.0
        if conditions.soc > self.soc_threshold:
            soc_excess = conditions.soc - self.soc_threshold
            soc_stress = 1.0 + (soc_excess * self.soc_penalty * 10)  # 10x multiplier
        
        # C-rate stress (affects cycle life)
        c_rate_stress = 1.0 + (conditions.c_rate - 0.5) * 0.1  # Penalty for high C-rates
        
        # Combined stress factor
        total_stress = temp_stress * soc_stress * c_rate_stress
        return max(1.0, total_stress)  # Never below baseline
        
    def calculate_marginal_cost(self, conditions: OperatingConditions) -> float:
        """
        Calculate marginal cost of degradation per cycle.
        
        Formula: MC_deg = (Capex / TotalCycles) * StressFactor * EfficiencyLoss
        
        Args:
            conditions: Current operating conditions
            
        Returns:
            Cost in $/kWh per cycle
        """
        stress_factor = self.get_stress_factor(conditions)
        
        # Base cost per cycle
        base_cost_per_cycle = (
            self.specs.capex_per_kwh / self.specs.max_cycles
        )
        
        # Account for round-trip efficiency loss
        efficiency_factor = 1.0 / self.specs.roundtrip_efficiency
        
        # Depth of discharge factor (deeper cycles = more wear)
        dod_factor = 0.5 + (conditions.cycle_depth * 0.5)  # 0.5-1.0 range
        
        marginal_cost = (
            base_cost_per_cycle * stress_factor * 
            efficiency_factor * dod_factor
        )
        
        return marginal_cost
        
    def predict_sei_growth(self, time_hours: float, temperature: float) -> float:
        """
        Predict SEI (Solid Electrolyte Interphase) layer growth.
        
        Uses Arrhenius equation: Q_loss(t) = A * exp(-Ea/RT) * t^0.5
        
        This models calendar aging independent of cycling.
        
        Args:
            time_hours: Operating time in hours
            temperature: Average temperature in °C
            
        Returns:
            Capacity loss fraction (0-1)
        """
        # Convert temperature to Kelvin
        temp_kelvin = temperature + 273.15
        
        # Arrhenius factor
        arrhenius_factor = math.exp(
            -self.sei_activation_energy / (self.gas_constant * temp_kelvin)
        )
        
        # Square root time dependence (typical for SEI growth)
        time_factor = math.sqrt(time_hours)
        
        # Total capacity loss
        capacity_loss = (
            self.sei_pre_factor * arrhenius_factor * time_factor
        )
        
        return min(0.2, capacity_loss)  # Cap at 20% loss
        
    def predict_knee_point(self, 
                          current_soh: float,
                          avg_temperature: float,
                          cycles_per_day: float) -> Tuple[int, float]:
        """
        Predict when battery will reach "Knee Point" (80% SoH).
        
        The knee point is when capacity degradation accelerates rapidly.
        
        Args:
            current_soh: Current state of health (0-1)
            avg_temperature: Average operating temperature °C
            cycles_per_day: Average daily cycles
            
        Returns:
            Tuple of (days_to_knee_point, final_soh_prediction)
        """
        if current_soh <= 0.8:
            return 0, current_soh  # Already at knee point
            
        # Accelerated aging model
        base_degradation_per_cycle = 1.0 / self.specs.max_cycles
        
        # Temperature acceleration
        temp_acceleration = self.get_stress_factor(
            OperatingConditions(soc=0.5, temperature=avg_temperature, 
                              cycle_depth=0.8, c_rate=0.5)
        )
        
        # Daily degradation rate
        daily_degradation = (
            base_degradation_per_cycle * cycles_per_day * temp_acceleration
        )
        
        # Days to reach 80% SoH
        soh_loss_needed = current_soh - 0.8
        days_to_knee = int(soh_loss_needed / daily_degradation)
        
        # Predict final SoH (with some safety margin)
        final_soh = current_soh - (daily_degradation * days_to_knee * 1.1)
        
        return days_to_knee, max(0.6, final_soh)
        
    def get_optimal_operating_window(self) -> Dict[str, Tuple[float, float]]:
        """
        Get optimal operating windows to minimize degradation.
        
        Returns:
            Dictionary with parameter ranges for optimal operation
        """
        return {
            "soc_range": (0.2, 0.9),  # 20-90% SoC
            "temperature_range": (15.0, 35.0),  # 15-35°C
            "c_rate_range": (0.1, 0.8),  # 0.1C to 0.8C
            "max_dod": 0.8  # Maximum 80% depth of discharge
        }
        
    def calculate_cycle_cost_matrix(self, 
                                   soc_points: np.ndarray,
                                   temp_points: np.ndarray) -> np.ndarray:
        """
        Generate a cost matrix for different SoC and temperature combinations.
        
        Useful for optimization algorithms to avoid expensive operating regions.
        
        Args:
            soc_points: Array of SoC values (0-1)
            temp_points: Array of temperature values (°C)
            
        Returns:
            2D cost matrix [temp x soc]
        """
        cost_matrix = np.zeros((len(temp_points), len(soc_points)))
        
        for i, temp in enumerate(temp_points):
            for j, soc in enumerate(soc_points):
                conditions = OperatingConditions(
                    soc=soc, temperature=temp, 
                    cycle_depth=0.8, c_rate=0.5  # Standard conditions
                )
                cost_matrix[i, j] = self.calculate_marginal_cost(conditions)
                
        return cost_matrix


# Example usage and validation
if __name__ == "__main__":
    # Example battery specifications (280Ah LFP pack)
    battery = BatterySpecs(
        capacity_kwh=280.0,
        max_cycles=6000,
        capex_per_kwh=150.0
    )
    
    # Create degradation model
    model = DegradationModel(battery)
    
    # Test different operating conditions
    test_conditions = [
        OperatingConditions(soc=0.5, temperature=25, cycle_depth=0.8, c_rate=0.5),
        OperatingConditions(soc=0.95, temperature=25, cycle_depth=0.8, c_rate=0.5),
        OperatingConditions(soc=0.5, temperature=45, cycle_depth=0.8, c_rate=0.5),
        OperatingConditions(soc=0.95, temperature=45, cycle_depth=0.8, c_rate=1.0),
    ]
    
    print("Battery Degradation Analysis")
    print("=" * 40)
    
    for i, conditions in enumerate(test_conditions):
        stress = model.get_stress_factor(conditions)
        cost = model.calculate_marginal_cost(conditions)
        
        print(f"\nCondition {i+1}:")
        print(f"  SoC: {conditions.soc:.1%}")
        print(f"  Temperature: {conditions.temperature}°C") 
        print(f"  Stress Factor: {stress:.2f}x")
        print(f"  Marginal Cost: ${cost:.3f}/kWh per cycle")
        
    # Knee point prediction
    days_to_knee, final_soh = model.predict_knee_point(
        current_soh=0.95, avg_temperature=30.0, cycles_per_day=1.5
    )
    
    print(f"\nKnee Point Analysis:")
    print(f"  Days to 80% SoH: {days_to_knee}")
    print(f"  Predicted final SoH: {final_soh:.1%}")
    
    # Optimal operating windows
    optimal = model.get_optimal_operating_window()
    print(f"\nOptimal Operating Windows:")
    for param, (min_val, max_val) in optimal.items():
        print(f"  {param}: {min_val} - {max_val}")
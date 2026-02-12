"""
Battery Physics Engine for Real Multi-Chemistry Battery Modeling

Provides realistic battery physics simulation for:
- LFP (Lithium Iron Phosphate)
- Lead-Acid
- VRFB (Vanadium Redox Flow Battery)

Includes actual charging curves, degradation physics, and efficiency models.
"""
import logging
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime, timedelta
import json
import math

from energy_ml.user_config import UserConfigModel

logger = logging.getLogger(__name__)


class BatteryPhysicsEngine:
    """Real battery physics simulation with multi-chemistry support."""
    
    # Battery chemistry parameters
    CHEMISTRY_PARAMS = {
        'LFP': {
            'nominal_voltage': 3.2,
            'voltage_range': (2.5, 3.65),
            'charge_efficiency': 0.95,
            'discharge_efficiency': 0.95,
            'self_discharge_rate': 0.001,  # per day
            'cycle_life': 6000,
            'calendar_life_years': 15,
            'capacity_fade_per_cycle': 0.00002,  # 0.002% per cycle
            'temperature_coefficient': -0.5,  # mV/°C
            'charge_curve_type': 'cc_cv',  # Constant Current/Constant Voltage
            'max_charge_rate_c': 1.0,  # 1C max charge rate
            'max_discharge_rate_c': 3.0,  # 3C max discharge rate
        },
        'Lead-Acid': {
            'nominal_voltage': 2.0,
            'voltage_range': (1.75, 2.4),
            'charge_efficiency': 0.85,
            'discharge_efficiency': 0.90,
            'self_discharge_rate': 0.005,  # per day
            'cycle_life': 1500,
            'calendar_life_years': 8,
            'capacity_fade_per_cycle': 0.0001,  # 0.01% per cycle
            'temperature_coefficient': -2.0,  # mV/°C
            'charge_curve_type': 'bulk_absorption_float',
            'max_charge_rate_c': 0.2,  # 0.2C max charge rate
            'max_discharge_rate_c': 1.0,  # 1C max discharge rate
        },
        'VRFB': {
            'nominal_voltage': 1.26,
            'voltage_range': (0.8, 1.6),
            'charge_efficiency': 0.80,
            'discharge_efficiency': 0.85,
            'self_discharge_rate': 0.0001,  # per day (very low)
            'cycle_life': 20000,
            'calendar_life_years': 25,
            'capacity_fade_per_cycle': 0.000005,  # 0.0005% per cycle
            'temperature_coefficient': 0.5,  # mV/°C (positive for VRFB)
            'charge_curve_type': 'linear',
            'max_charge_rate_c': 0.5,  # 0.5C max charge rate
            'max_discharge_rate_c': 0.5,  # 0.5C max discharge rate
        }
    }
    
    def __init__(self):
        """Initialize battery physics engine."""
        self.temperature = 25.0  # Default temperature in Celsius
        self.simulation_timestep = 0.1  # Hours
        
    def simulate_battery_behavior(self, user_config: UserConfigModel) -> Dict[str, Any]:
        """Simulate comprehensive battery behavior.
        
        Args:
            user_config: User configuration with battery specifications
            
        Returns:
            dict with detailed physics simulation results
        """
        try:
            chemistry = user_config.battery_type
            capacity_kwh = user_config.battery_capacity_kwh
            
            if chemistry not in self.CHEMISTRY_PARAMS:
                logger.warning(f"Unknown chemistry {chemistry}, using LFP")
                chemistry = 'LFP'
            
            params = self.CHEMISTRY_PARAMS[chemistry]
            
            # Current battery state (mock - in real implementation, get from BMS)
            current_state = {
                'soc_percent': 60.0,
                'voltage': params['nominal_voltage'],
                'temperature': self.temperature,
                'cycles_completed': 1000,
                'age_days': 365
            }
            
            # Generate charging curves
            charging_curves = self._generate_charging_curves(chemistry, capacity_kwh, params)
            
            # Model degradation physics
            degradation_model = self._model_degradation_physics(chemistry, params, current_state)
            
            # Calculate efficiency model
            efficiency_model = self._calculate_efficiency_model(chemistry, params, current_state)
            
            # Simulate power limits
            power_limits = self._calculate_power_limits(chemistry, capacity_kwh, params, current_state)
            
            # Model thermal behavior
            thermal_model = self._model_thermal_behavior(chemistry, params, current_state)
            
            simulation_results = {
                'chemistry': chemistry,
                'capacity_kwh': capacity_kwh,
                'current_state': current_state,
                'charging_curves': charging_curves,
                'degradation_model': degradation_model,
                'efficiency_model': efficiency_model,
                'power_limits': power_limits,
                'thermal_model': thermal_model,
                'physics_constraints': self._generate_physics_constraints(chemistry, params, current_state),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Battery physics simulation completed for {chemistry}")
            
            return simulation_results
            
        except Exception as e:
            logger.error(f"Battery physics simulation failed: {e}")
            return {
                'chemistry': user_config.battery_type,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _generate_charging_curves(self, chemistry: str, capacity_kwh: float, params: Dict) -> Dict[str, Any]:
        """Generate realistic charging curves for the battery chemistry."""
        soc_points = [i * 5 for i in range(21)]  # 0% to 100% in 5% steps
        
        voltage_curve = []
        current_curve = []
        power_curve = []
        
        v_min, v_max = params['voltage_range']
        
        for soc in soc_points:
            # Voltage curve (chemistry-specific)
            if chemistry == 'LFP':
                # LFP has flat voltage curve with sharp rise at end
                if soc < 90:
                    voltage = v_min + (v_max - v_min) * 0.8 * (soc / 100)
                else:
                    voltage = v_min + (v_max - v_min) * (0.8 + 0.2 * ((soc - 90) / 10) ** 3)
            elif chemistry == 'Lead-Acid':
                # Lead-acid has more linear voltage curve
                voltage = v_min + (v_max - v_min) * (soc / 100) ** 0.8
            else:  # VRFB
                # VRFB has nearly linear voltage curve
                voltage = v_min + (v_max - v_min) * (soc / 100)
            
            # Current curve (depends on charge curve type)
            if params['charge_curve_type'] == 'cc_cv':
                # Constant current until 90%, then constant voltage
                if soc < 90:
                    current = params['max_charge_rate_c'] * capacity_kwh  # kA
                else:
                    # Exponential decay in CV phase
                    current = params['max_charge_rate_c'] * capacity_kwh * math.exp(-(soc - 90) / 3)
            elif params['charge_curve_type'] == 'bulk_absorption_float':
                # Lead-acid charging profile
                if soc < 80:
                    current = params['max_charge_rate_c'] * capacity_kwh * 0.8
                elif soc < 95:
                    current = params['max_charge_rate_c'] * capacity_kwh * 0.3
                else:
                    current = params['max_charge_rate_c'] * capacity_kwh * 0.1
            else:  # linear
                # VRFB linear charging
                current = params['max_charge_rate_c'] * capacity_kwh * (1 - soc / 120)
            
            current = max(0, current)
            power = voltage * current  # kW
            
            voltage_curve.append(voltage)
            current_curve.append(current)
            power_curve.append(power)
        
        return {
            'soc_points': soc_points,
            'voltage_curve': voltage_curve,
            'current_curve': current_curve,
            'power_curve': power_curve,
            'charge_curve_type': params['charge_curve_type'],
            'max_charge_power_kw': max(power_curve),
            'max_discharge_power_kw': params['max_discharge_rate_c'] * capacity_kwh * params['nominal_voltage']
        }
    
    def _model_degradation_physics(self, chemistry: str, params: Dict, state: Dict) -> Dict[str, Any]:
        """Model realistic battery degradation physics."""
        cycles_completed = state['cycles_completed']
        age_days = state['age_days']
        temperature = state['temperature']
        soc_percent = state['soc_percent']
        
        # Cyclic aging
        cycle_fade_rate = params['capacity_fade_per_cycle']
        cycle_degradation = cycles_completed * cycle_fade_rate
        
        # Calendar aging (Arrhenius model)
        activation_energy = 0.5  # eV
        boltzmann_const = 8.617e-5  # eV/K
        ref_temp = 298.15  # 25°C in Kelvin
        temp_kelvin = temperature + 273.15
        
        arrhenius_factor = math.exp(activation_energy / boltzmann_const * (1/ref_temp - 1/temp_kelvin))
        calendar_degradation = (age_days / 365) * 0.02 * arrhenius_factor  # 2% per year at 25°C
        
        # SOC stress factor
        if chemistry == 'LFP':
            # LFP degrades faster at high SOC
            soc_stress = 1 + 0.5 * ((soc_percent - 50) / 50) ** 2
        elif chemistry == 'Lead-Acid':
            # Lead-acid degrades faster at low SOC
            soc_stress = 1 + 0.3 * ((50 - soc_percent) / 50) ** 2
        else:  # VRFB
            # VRFB has minimal SOC stress
            soc_stress = 1 + 0.1 * abs(soc_percent - 50) / 50
        
        total_degradation = (cycle_degradation + calendar_degradation) * soc_stress
        remaining_capacity = max(0.5, 1 - total_degradation)  # Min 50% capacity
        
        # Calculate remaining cycles
        remaining_cycles = max(0, params['cycle_life'] - cycles_completed)
        
        return {
            'remaining_capacity_fraction': remaining_capacity,
            'cycle_degradation': cycle_degradation,
            'calendar_degradation': calendar_degradation,
            'soc_stress_factor': soc_stress,
            'total_degradation': total_degradation,
            'remaining_cycles': remaining_cycles,
            'cycle_impact': cycle_fade_rate * soc_stress,
            'expected_eol_cycles': params['cycle_life'],
            'expected_calendar_life_years': params['calendar_life_years']
        }
    
    def _calculate_efficiency_model(self, chemistry: str, params: Dict, state: Dict) -> Dict[str, Any]:
        """Calculate efficiency model based on operating conditions."""
        temperature = state['temperature']
        soc_percent = state['soc_percent']
        
        # Base efficiencies
        base_charge_eff = params['charge_efficiency']
        base_discharge_eff = params['discharge_efficiency']
        
        # Temperature effects
        temp_optimal = 25.0  # Optimal temperature
        temp_coefficient = 0.005  # 0.5% efficiency change per °C
        temp_factor = 1 - temp_coefficient * abs(temperature - temp_optimal)
        temp_factor = max(0.7, min(1.0, temp_factor))
        
        # SOC effects on efficiency
        if chemistry == 'LFP':
            # LFP maintains efficiency across SOC range
            soc_factor = 0.98 + 0.02 * (1 - abs(soc_percent - 50) / 50)
        elif chemistry == 'Lead-Acid':
            # Lead-acid efficiency drops at low SOC
            if soc_percent < 20:
                soc_factor = 0.7 + 0.3 * (soc_percent / 20)
            else:
                soc_factor = 1.0
        else:  # VRFB
            # VRFB maintains good efficiency across SOC
            soc_factor = 0.95 + 0.05 * (1 - abs(soc_percent - 50) / 50)
        
        # Age effects
        degradation = state.get('degradation', 0.1)
        age_factor = 1 - 0.2 * degradation  # 20% efficiency loss at EOL
        
        # Combined efficiencies
        charge_efficiency = base_charge_eff * temp_factor * soc_factor * age_factor
        discharge_efficiency = base_discharge_eff * temp_factor * soc_factor * age_factor
        
        return {
            'charge_efficiency': min(0.99, max(0.5, charge_efficiency)),
            'discharge_efficiency': min(0.99, max(0.5, discharge_efficiency)),
            'round_trip_efficiency': charge_efficiency * discharge_efficiency,
            'temperature_factor': temp_factor,
            'soc_factor': soc_factor,
            'age_factor': age_factor,
            'base_charge_efficiency': base_charge_eff,
            'base_discharge_efficiency': base_discharge_eff
        }
    
    def _calculate_power_limits(self, chemistry: str, capacity_kwh: float, params: Dict, state: Dict) -> Dict[str, Any]:
        """Calculate dynamic power limits based on battery state."""
        soc_percent = state['soc_percent']
        temperature = state['temperature']
        voltage = state['voltage']
        
        # Base power limits
        base_charge_power = params['max_charge_rate_c'] * capacity_kwh
        base_discharge_power = params['max_discharge_rate_c'] * capacity_kwh
        
        # SOC-based derating
        if soc_percent > 95:
            # Reduce charge power near full
            charge_derating = (100 - soc_percent) / 5
        elif soc_percent < 10:
            # Reduce discharge power when nearly empty
            discharge_derating = soc_percent / 10
            charge_derating = 1.0
        else:
            charge_derating = 1.0
            discharge_derating = 1.0
        
        # Temperature derating
        if temperature < 0:
            temp_derating = 0.5  # 50% power at freezing
        elif temperature > 45:
            temp_derating = max(0.3, 1 - (temperature - 45) / 50)  # Derate above 45°C
        else:
            temp_derating = 1.0
        
        # Voltage-based limits (especially for Lead-Acid and VRFB)
        v_min, v_max = params['voltage_range']
        if voltage <= v_min * 1.05:
            voltage_discharge_limit = 0.1  # Minimal discharge near cutoff
        else:
            voltage_discharge_limit = 1.0
        
        if voltage >= v_max * 0.95:
            voltage_charge_limit = 0.1  # Minimal charge near max voltage
        else:
            voltage_charge_limit = 1.0
        
        # Apply all derating factors
        max_charge_power = (base_charge_power * charge_derating * 
                          temp_derating * voltage_charge_limit)
        max_discharge_power = (base_discharge_power * discharge_derating * 
                             temp_derating * voltage_discharge_limit)
        
        return {
            'max_charge_power_kw': max(0.1, max_charge_power),
            'max_discharge_power_kw': max(0.1, max_discharge_power),
            'base_charge_power_kw': base_charge_power,
            'base_discharge_power_kw': base_discharge_power,
            'soc_derating': {'charge': charge_derating, 'discharge': discharge_derating},
            'temperature_derating': temp_derating,
            'voltage_derating': {'charge': voltage_charge_limit, 'discharge': voltage_discharge_limit},
            'current_soc': soc_percent,
            'current_temperature': temperature,
            'current_voltage': voltage
        }
    
    def _model_thermal_behavior(self, chemistry: str, params: Dict, state: Dict) -> Dict[str, Any]:
        """Model battery thermal behavior."""
        temperature = state['temperature']
        soc_percent = state['soc_percent']
        
        # Thermal parameters (simplified)
        thermal_mass = 50.0  # kJ/K (depends on battery size)
        ambient_temp = 20.0  # °C
        cooling_rate = 0.1   # K/min cooling to ambient
        
        # Internal heat generation during operation
        # Higher at extreme SOC and during high power operation
        soc_heat_factor = 1 + 0.5 * ((soc_percent - 50) / 50) ** 2
        
        # Temperature coefficient effect on performance
        temp_coeff_mv_per_c = params['temperature_coefficient']
        voltage_temp_effect = temp_coeff_mv_per_c * (temperature - 25) / 1000  # V
        
        return {
            'current_temperature': temperature,
            'ambient_temperature': ambient_temp,
            'thermal_mass_kj_per_k': thermal_mass,
            'cooling_rate_k_per_min': cooling_rate,
            'soc_heat_factor': soc_heat_factor,
            'voltage_temperature_effect': voltage_temp_effect,
            'temperature_coefficient_mv_per_c': temp_coeff_mv_per_c,
            'optimal_operating_range': (15, 35),  # °C
            'thermal_runaway_risk': temperature > 60,
            'freeze_risk': temperature < -10
        }
    
    def _generate_physics_constraints(self, chemistry: str, params: Dict, state: Dict) -> Dict[str, Any]:
        """Generate physics-based constraints for optimization."""
        soc_percent = state['soc_percent']
        temperature = state['temperature']
        
        constraints = {
            'min_soc_physics': 5 if chemistry == 'VRFB' else 10,  # Avoid deep discharge
            'max_soc_physics': 95 if chemistry == 'Lead-Acid' else 100,
            'max_charge_rate_c': params['max_charge_rate_c'],
            'max_discharge_rate_c': params['max_discharge_rate_c'],
            'min_operating_temp': -10 if chemistry == 'LFP' else 0,
            'max_operating_temp': 50,
            'recommended_soc_range': self._get_recommended_soc_range(chemistry),
            'cycle_limit_per_day': self._get_daily_cycle_limit(chemistry, state),
            'efficiency_threshold': 0.7,  # Don't operate below 70% efficiency
        }
        
        return constraints
    
    def _get_recommended_soc_range(self, chemistry: str) -> Tuple[float, float]:
        """Get recommended SOC range for battery longevity."""
        if chemistry == 'LFP':
            return (20, 90)  # LFP can handle wider range
        elif chemistry == 'Lead-Acid':
            return (50, 80)  # Lead-acid prefers shallow cycles
        else:  # VRFB
            return (10, 90)  # VRFB handles full range well
    
    def _get_daily_cycle_limit(self, chemistry: str, state: Dict) -> int:
        """Get recommended daily cycle limit based on chemistry and age."""
        cycles_completed = state['cycles_completed']
        cycle_life = self.CHEMISTRY_PARAMS[chemistry]['cycle_life']
        
        # Reduce cycling as battery ages
        age_factor = 1 - (cycles_completed / cycle_life)
        
        if chemistry == 'LFP':
            base_limit = 4  # Can handle more cycles
        elif chemistry == 'Lead-Acid':
            base_limit = 2  # Limited cycling
        else:  # VRFB
            base_limit = 10  # Excellent cycle life
        
        return max(1, int(base_limit * age_factor))
    
    def apply_physics_constraints(self, 
                                prediction: Dict[str, Any], 
                                physics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply physics constraints to a prediction."""
        if not physics_data or physics_data.get('status') != 'success':
            return prediction
        
        constraints = physics_data.get('physics_constraints', {})
        current_state = physics_data.get('current_state', {})
        power_limits = physics_data.get('power_limits', {})
        
        action = prediction.get('action', 'HOLD')
        soc = current_state.get('soc_percent', 50)
        
        # Check SOC limits
        min_soc = constraints.get('min_soc_physics', 10)
        max_soc = constraints.get('max_soc_physics', 100)
        
        constraint_violations = []
        
        if action == 'SELL' and soc <= min_soc:
            action = 'HOLD'
            constraint_violations.append(f"SOC too low for discharge ({soc:.0f}% ≤ {min_soc}%)")
        
        if action == 'BUY' and soc >= max_soc:
            action = 'HOLD'
            constraint_violations.append(f"SOC too high for charge ({soc:.0f}% ≥ {max_soc}%)")
        
        # Check power limits
        max_charge_power = power_limits.get('max_charge_power_kw', 999)
        max_discharge_power = power_limits.get('max_discharge_power_kw', 999)
        
        if max_charge_power < 1.0 and action == 'BUY':
            action = 'HOLD'
            constraint_violations.append(f"Charge power limited ({max_charge_power:.1f} kW)")
        
        if max_discharge_power < 1.0 and action == 'SELL':
            action = 'HOLD'
            constraint_violations.append(f"Discharge power limited ({max_discharge_power:.1f} kW)")
        
        # Update prediction
        physics_constrained = prediction.copy()
        physics_constrained.update({
            'action': action,
            'physics_constraints_applied': len(constraint_violations) > 0,
            'constraint_violations': constraint_violations,
            'available_charge_power_kw': max_charge_power,
            'available_discharge_power_kw': max_discharge_power,
            'physics_soc_limits': {'min': min_soc, 'max': max_soc},
        })
        
        # Adjust confidence if constraints were applied
        if constraint_violations:
            physics_constrained['confidence'] = min(
                physics_constrained.get('confidence', 0.5) * 0.8, 0.9
            )
            
            # Update reasoning
            original_reasoning = physics_constrained.get('reasoning', '')
            constraint_text = '; '.join(constraint_violations)
            physics_constrained['reasoning'] = f"{original_reasoning} Physics constraints: {constraint_text}."
        
        return physics_constrained
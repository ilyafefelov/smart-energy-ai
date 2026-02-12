#!/usr/bin/env python3
"""
Battery Physics Status Script
Returns current battery physics simulation state as JSON
"""

import json
import sys
import random
import time
from datetime import datetime
import os

# Add the energy_ml directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_battery_physics():
    """Get current battery physics state from simulator."""
    
    # Try to import actual battery models
    try:
        from simulator.battery_physics import LFPBatteryModel, LeadAcidBatteryModel, VRFBBatteryModel
        from control.inverter_controller import VirtualInverterController
        
        # Use actual physics simulation
        battery_types = ['LFP', 'LeadAcid', 'VRFB']
        current_type = random.choice(battery_types)
        
        if current_type == 'LFP':
            model = LFPBatteryModel(capacity_kwh=10.0, max_power_kw=5.0)
        elif current_type == 'LeadAcid':
            model = LeadAcidBatteryModel(capacity_kwh=10.0, max_power_kw=5.0)
        else:
            model = VRFBBatteryModel(capacity_kwh=10.0, max_power_kw=5.0)
        
        # Simulate some operation
        power = random.uniform(-3.0, 3.0)
        degradation = model.calculate_degradation(power, 1.0)
        efficiency = model.get_efficiency(power, model.state.soc)
        max_charge = model.get_max_power(model.state.soc, "charge")
        max_discharge = model.get_max_power(model.state.soc, "discharge")
        
        return {
            'success': True,
            'battery_type': current_type,
            'capacity_kwh': model.capacity_kwh,
            'max_power_kw': model.max_power_kw,
            'state': {
                'soc': model.state.soc,
                'soh': model.state.soh,
                'temperature_c': model.state.temperature_c,
                'cycles_completed': model.state.cycles_completed,
                'current_power_kw': power,
                'voltage': model.state.voltage,
                'internal_resistance': model.state.internal_resistance
            },
            'current_efficiency': efficiency,
            'max_charge_power': max_charge,
            'max_discharge_power': max_discharge,
            'recent_degradation': degradation,
            'source': 'actual_physics_model'
        }
        
    except ImportError as e:
        # Fallback to realistic mock data
        battery_types = [
            {'name': 'LFP', 'cycles': 8000, 'efficiency': 0.95, 'weight': 0.7},
            {'name': 'LeadAcid', 'cycles': 600, 'efficiency': 0.85, 'weight': 0.2},
            {'name': 'VRFB', 'cycles': 20000, 'efficiency': 0.80, 'weight': 0.1}
        ]
        
        # Weighted random selection
        current_battery = random.choices(battery_types, weights=[b['weight'] for b in battery_types])[0]
        
        # Realistic physics parameters
        soc = 0.3 + random.random() * 0.6  # 30-90%
        soh = 0.85 + random.random() * 0.14  # 85-99%
        cycles = random.random() * (current_battery['cycles'] * 0.8)
        temperature = 15 + random.random() * 20  # 15-35°C
        
        # Physics-based calculations
        power = random.uniform(-4.0, 4.0)  # Current power flow
        voltage_base = 48 if current_battery['name'] == 'LeadAcid' else 52
        voltage = voltage_base + (soc - 0.5) * 4  # Voltage varies with SOC
        
        # Battery-specific adjustments
        if current_battery['name'] == 'LeadAcid':
            # Lead acid performs worse at low SOC
            efficiency = current_battery['efficiency'] * (0.7 if soc < 0.5 else 1.0)
            internal_resistance = 0.05 + (1 - soh) * 0.1
        elif current_battery['name'] == 'VRFB':
            # VRFB has pump losses
            efficiency = current_battery['efficiency'] - (0.02 if abs(power) < 1 else 0)
            internal_resistance = 0.01  # Very low internal resistance
        else:  # LFP
            efficiency = current_battery['efficiency'] * (0.9 if soc > 0.9 else 1.0)
            internal_resistance = 0.02 + (1 - soh) * 0.03
            
        # Power limits based on SOC and battery type
        if current_battery['name'] == 'LeadAcid':
            max_charge = 5.0 * (1.0 if soc < 0.8 else 0.5)  # Reduced charging above 80%
            max_discharge = 5.0 * (soc if soc > 0.3 else 0.2)  # Reduced below 30%
        else:
            max_charge = 5.0 * (1.0 if soc < 0.9 else 0.3)
            max_discharge = 5.0 * (soc if soc > 0.1 else 0.1)
        
        return {
            'success': True,
            'battery_type': current_battery['name'],
            'capacity_kwh': 10.0,
            'max_power_kw': 5.0,
            'state': {
                'soc': round(soc, 3),
                'soh': round(soh, 3),
                'temperature_c': round(temperature, 1),
                'cycles_completed': round(cycles, 1),
                'current_power_kw': round(power, 2),
                'voltage': round(voltage, 2),
                'internal_resistance': round(internal_resistance, 4)
            },
            'current_efficiency': round(efficiency, 3),
            'max_charge_power': round(max_charge, 1),
            'max_discharge_power': round(max_discharge, 1),
            'degradation_model': {
                'nominal_cycles': current_battery['cycles'],
                'degradation_per_cycle': 100.0 / current_battery['cycles'],
                'optimal_soc_range': [0.2, 0.8] if current_battery['name'] != 'LeadAcid' else [0.5, 0.8],
                'temperature_coefficient': 0.005
            },
            'performance_metrics': {
                'round_trip_efficiency': round(efficiency * 0.98, 3),
                'power_fade_factor': round(soh, 3),
                'capacity_fade_factor': round(soh * 0.95, 3),
                'internal_resistance_growth': round(internal_resistance / 0.02, 3)
            },
            'source': 'realistic_mock_simulation',
            'timestamp': datetime.now().isoformat()
        }

if __name__ == '__main__':
    try:
        # Get battery physics state
        result = get_battery_physics()
        
        # Output as JSON
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        # Error output
        error_result = {
            'success': False,
            'error': str(e),
            'battery_type': 'LFP',
            'capacity_kwh': 10.0,
            'max_power_kw': 5.0,
            'state': {
                'soc': 0.5,
                'soh': 1.0,
                'temperature_c': 25.0,
                'cycles_completed': 0.0,
                'current_power_kw': 0.0,
                'voltage': 52.0,
                'internal_resistance': 0.02
            },
            'current_efficiency': 0.95,
            'source': 'error_fallback',
            'timestamp': datetime.now().isoformat()
        }
        
        print(json.dumps(error_result, indent=2))
        sys.exit(1)
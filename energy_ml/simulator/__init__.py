"""
Smart Energy AI Physics-Based Battery Simulator

This module provides realistic battery physics simulation:
- Abstract BatteryModel base class
- LFPBatteryModel: Lithium Iron Phosphate with degradation modeling
- LeadAcidBatteryModel: Lead-Acid with deep discharge sensitivity  
- VRFBBatteryModel: Vanadium Redox Flow Battery with pump losses
- Real degradation, efficiency, and power limit calculations
"""

from .battery_physics import (
    BatteryState,
    BatteryModel,
    LFPBatteryModel,
    LeadAcidBatteryModel,
    VRFBBatteryModel
)

__all__ = [
    'BatteryState',
    'BatteryModel', 
    'LFPBatteryModel',
    'LeadAcidBatteryModel',
    'VRFBBatteryModel'
]
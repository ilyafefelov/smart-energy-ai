"""Pydantic configuration models for Smart Energy AI Phase 4 SaaS upgrade.

This module defines user configuration models for battery types, load profiles,
and business operation parameters that replace hard-coded values.
"""

from typing import Dict, List, Literal, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator


class BatteryConfig(BaseModel):
    """Battery configuration for different battery technologies."""
    
    type: Literal['LFP', 'Lead-Acid', 'VRFB'] = Field(
        description="Battery chemistry type"
    )
    capacity_kwh: float = Field(
        gt=0, 
        description="Battery capacity in kWh"
    )
    efficiency: float = Field(
        default=0.95, 
        ge=0.7, 
        le=1.0,
        description="Round-trip efficiency (0.7-1.0)"
    )
    max_charge_rate_kw: float = Field(
        gt=0,
        description="Maximum charge rate in kW"
    )
    max_discharge_rate_kw: float = Field(
        gt=0, 
        description="Maximum discharge rate in kW"
    )
    # SOC constraints
    min_soc_percent: float = Field(
        default=20.0,
        ge=0, 
        le=50,
        description="Minimum safe SOC percentage"
    )
    max_soc_percent: float = Field(
        default=90.0,
        ge=50, 
        le=100,
        description="Maximum safe SOC percentage"  
    )
    
    # Degradation parameters (Phase 4B)
    degradation_cost_per_cycle: Optional[float] = Field(
        default=None,
        description="Cost per full cycle in USD"
    )
    cycles_to_eol: Optional[int] = Field(
        default=None,
        gt=100,
        description="Cycles to End of Life (80% capacity)"
    )
    
    @validator('degradation_cost_per_cycle', pre=True, always=True)
    def set_degradation_cost(cls, v, values):
        """Set default degradation cost based on battery type."""
        if v is not None:
            return v
        
        battery_type = values.get('type')
        defaults = {
            'LFP': 1.35,          # $1.35/cycle, 8000 cycles
            'Lead-Acid': 4.59,    # $4.59/cycle, 600 cycles  
            'VRFB': 0.1           # Minimal degradation
        }
        return defaults.get(battery_type, 1.0)
    
    @validator('cycles_to_eol', pre=True, always=True)
    def set_cycles_to_eol(cls, v, values):
        """Set default cycles to EOL based on battery type."""
        if v is not None:
            return v
            
        battery_type = values.get('type')
        defaults = {
            'LFP': 8000,
            'Lead-Acid': 600,
            'VRFB': 20000
        }
        return defaults.get(battery_type, 5000)


class LoadProfileConfig(BaseModel):
    """Load profile configuration for business operation simulation."""
    
    profile_type: Literal['standard', 'multi-shift', '24/7', 'custom'] = Field(
        description="Type of load profile"
    )
    name: str = Field(
        description="Human-readable profile name"
    )
    description: Optional[str] = Field(
        description="Profile description"
    )
    
    # Hourly load coefficients (0-24 hours)
    hourly_coefficients: Dict[int, float] = Field(
        description="Hourly load coefficients (0.0-2.0), hour 0-23"
    )
    
    # Peak load in kW
    peak_load_kw: float = Field(
        gt=0,
        description="Peak load during operating hours"
    )
    
    @validator('hourly_coefficients')
    def validate_hourly_coefficients(cls, v):
        """Validate hourly coefficients."""
        if not isinstance(v, dict):
            raise ValueError("hourly_coefficients must be a dictionary")
        
        # Check all hours 0-23 are present
        required_hours = set(range(24))
        provided_hours = set(v.keys())
        
        if required_hours != provided_hours:
            raise ValueError("Must provide coefficients for all 24 hours (0-23)")
        
        # Check coefficient ranges
        for hour, coeff in v.items():
            if not (0.0 <= coeff <= 2.0):
                raise ValueError(f"Coefficient for hour {hour} must be between 0.0-2.0")
        
        return v
    
    @classmethod
    def create_standard_work_profile(cls, peak_load_kw: float) -> 'LoadProfileConfig':
        """Create standard 9-18 work hours profile."""
        coefficients = {hour: 0.1 for hour in range(24)}  # Base load
        for hour in range(9, 19):  # 9 AM to 6 PM
            coefficients[hour] = 1.0  # Full load during work hours
        
        return cls(
            profile_type='standard',
            name='Standard Work Hours (9-18)',
            description='Office hours with peak load 9 AM - 6 PM',
            hourly_coefficients=coefficients,
            peak_load_kw=peak_load_kw
        )
    
    @classmethod  
    def create_two_shift_profile(cls, peak_load_kw: float) -> 'LoadProfileConfig':
        """Create 2-shift operation profile."""
        coefficients = {hour: 0.2 for hour in range(24)}  # Base load
        # First shift: 6 AM - 2 PM
        for hour in range(6, 15):
            coefficients[hour] = 1.0
        # Second shift: 10 PM - 6 AM  
        for hour in list(range(22, 24)) + list(range(0, 7)):
            coefficients[hour] = 1.0
            
        return cls(
            profile_type='multi-shift',
            name='Two Shift Operation',
            description='6AM-2PM and 10PM-6AM shifts',
            hourly_coefficients=coefficients,
            peak_load_kw=peak_load_kw
        )
    
    @classmethod
    def create_24_7_profile(cls, peak_load_kw: float) -> 'LoadProfileConfig':
        """Create 24/7 continuous operation profile."""
        coefficients = {hour: 0.8 for hour in range(24)}  # Steady load
        # Slight variation for maintenance/shift changes
        coefficients[2] = 0.6   # 2 AM maintenance
        coefficients[14] = 0.6  # 2 PM shift change
        
        return cls(
            profile_type='24/7',
            name='Continuous Operation (24/7)',
            description='Round-the-clock operation with minor variations',
            hourly_coefficients=coefficients,
            peak_load_kw=peak_load_kw
        )


class GenerationConfig(BaseModel):
    """Solar and wind generation configuration."""
    
    solar_capacity_kw: float = Field(
        default=0.0,
        ge=0,
        description="Solar panel capacity in kW"
    )
    wind_capacity_kw: float = Field(
        default=0.0, 
        ge=0,
        description="Wind turbine capacity in kW"
    )
    solar_efficiency: float = Field(
        default=0.2,
        ge=0.1,
        le=0.3,
        description="Solar panel efficiency"
    )
    wind_efficiency: float = Field(
        default=0.35,
        ge=0.2, 
        le=0.5,
        description="Wind turbine efficiency"
    )


class UkraineTariffConfig(BaseModel):
    """Ukraine 2026 tariff configuration (Phase 4D)."""
    
    # Transmission tariffs (UAH/MWh)
    transmission_tariff_q1: float = Field(
        default=713.68,
        description="Transmission tariff Jan-Mar 2026 (UAH/MWh)"
    )
    transmission_tariff_q2_q4: float = Field(
        default=742.91,
        description="Transmission tariff Apr-Dec 2026 (UAH/MWh)"
    )
    dispatch_tariff: float = Field(
        default=110.03,
        description="Dispatch tariff 2026 (UAH/MWh)"
    )
    
    # Price caps
    dam_price_cap: float = Field(
        default=15000.0,
        description="Day-ahead market price cap (UAH/MWh)"
    )
    balancing_price_cap: float = Field(
        default=16000.0,
        description="Balancing market price cap (UAH/MWh)"
    )
    
    # Consumer group
    consumer_group: Literal['A', 'B', 'C'] = Field(
        default='A',
        description="Consumer group for tariff calculation"
    )


class UserProfile(BaseModel):
    """Complete user profile for SaaS multi-tenancy."""
    
    # User identification
    user_id: str = Field(description="Unique user identifier")
    profile_name: str = Field(description="Profile name")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Configuration components
    battery: BatteryConfig = Field(description="Battery configuration")
    load_profile: LoadProfileConfig = Field(description="Load profile")
    generation: GenerationConfig = Field(description="Generation configuration")
    tariff: UkraineTariffConfig = Field(description="Ukraine tariff configuration")
    
    # Location and timezone
    location: str = Field(
        default="Kyiv, Ukraine",
        description="Location for weather data"
    )
    timezone: str = Field(
        default="Europe/Kiev",
        description="Timezone for calculations"
    )
    
    # Economic parameters
    electricity_price_uah_kwh: Optional[float] = Field(
        default=None,
        description="Override electricity price if not using OREE"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Profile templates for quick setup
PROFILE_TEMPLATES = {
    'small_office': {
        'profile_name': 'Small Office',
        'battery': {
            'type': 'LFP',
            'capacity_kwh': 20.0,
            'max_charge_rate_kw': 5.0,
            'max_discharge_rate_kw': 5.0
        },
        'generation': {
            'solar_capacity_kw': 10.0,
            'wind_capacity_kw': 0.0
        }
    },
    'retail_store': {
        'profile_name': 'Retail Store',
        'battery': {
            'type': 'LFP',
            'capacity_kwh': 50.0,
            'max_charge_rate_kw': 15.0,
            'max_discharge_rate_kw': 15.0
        },
        'generation': {
            'solar_capacity_kw': 25.0,
            'wind_capacity_kw': 0.0
        }
    },
    'manufacturing': {
        'profile_name': 'Manufacturing Plant',
        'battery': {
            'type': 'LFP',
            'capacity_kwh': 200.0,
            'max_charge_rate_kw': 50.0,
            'max_discharge_rate_kw': 50.0
        },
        'generation': {
            'solar_capacity_kw': 100.0,
            'wind_capacity_kw': 50.0
        }
    }
}
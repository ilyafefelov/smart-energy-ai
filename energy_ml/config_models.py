"""Pydantic configuration models for Smart Energy AI Phase 4 SaaS upgrade.

This module defines user configuration models for battery types, load profiles,
and business operation parameters that replace hard-coded values.
"""

from datetime import datetime
import importlib.util
import sys
from pathlib import Path
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


def _load_profiles_module():
    try:
        from energy_ml import config_model_profiles as profiles_module

        return profiles_module
    except Exception:
        support_path = Path(__file__).with_name("config_model_profiles.py")
        module_name = "energy_ml.config_model_profiles"
        existing_module = sys.modules.get(module_name)
        if existing_module is not None:
            return existing_module

        spec = importlib.util.spec_from_file_location(module_name, support_path)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module


_PROFILES_MODULE = _load_profiles_module()
PROFILE_TEMPLATES = _PROFILES_MODULE.PROFILE_TEMPLATES
build_continuous_profile_payload = _PROFILES_MODULE.build_continuous_profile_payload
build_standard_work_profile_payload = _PROFILES_MODULE.build_standard_work_profile_payload
build_two_shift_profile_payload = _PROFILES_MODULE.build_two_shift_profile_payload
resolve_cycles_to_eol_default = _PROFILES_MODULE.resolve_cycles_to_eol_default
resolve_degradation_cost_default = _PROFILES_MODULE.resolve_degradation_cost_default


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
    
    @model_validator(mode='before')
    @classmethod
    def set_battery_defaults(cls, values):
        """Set defaults based on battery type for degradation and cycles."""
        if isinstance(values, dict):
            battery_type = values.get('type')

            if values.get('degradation_cost_per_cycle') is None:
                values['degradation_cost_per_cycle'] = resolve_degradation_cost_default(battery_type)

            if values.get('cycles_to_eol') is None:
                values['cycles_to_eol'] = resolve_cycles_to_eol_default(battery_type)

        return values


class LoadProfileConfig(BaseModel):
    """Load profile configuration for business operation simulation."""
    
    profile_type: Literal['standard', 'multi-shift', '24_7', 'custom'] = Field(
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
    
    @field_validator('profile_type', mode='before')
    @classmethod
    def normalize_profile_type(cls, value: str) -> str:
        """Normalize legacy profile tokens to a canonical machine value."""
        if value == '24/7':
            return '24_7'
        return value

    @field_validator('hourly_coefficients')
    @classmethod
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
        return cls(**build_standard_work_profile_payload(peak_load_kw))
    
    @classmethod  
    def create_two_shift_profile(cls, peak_load_kw: float) -> 'LoadProfileConfig':
        """Create 2-shift operation profile."""
        return cls(**build_two_shift_profile_payload(peak_load_kw))
    
    @classmethod
    def create_24_7_profile(cls, peak_load_kw: float) -> 'LoadProfileConfig':
        """Create 24/7 continuous operation profile."""
        return cls(**build_continuous_profile_payload(peak_load_kw))


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

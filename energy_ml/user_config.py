"""User configuration management for Phase 4A-4F.

Handles battery, load profile, and tariff settings persistence with complete ML integration.
"""
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Literal, List, TypedDict
import json
import os
import sys
from pydantic import BaseModel, ConfigDict, ValidationError, Field, field_validator


class UserConfigModel(BaseModel):
    """Complete user configuration data model for Phase 4A-4F."""
    
    # Phase 4B Battery Configuration - Extended
    battery_type: Literal["LFP", "Lead-Acid", "VRFB"] = "LFP"
    battery_capacity_kwh: float = Field(default=10.0, ge=1.0, le=1000.0)
    battery_efficiency: float = Field(default=0.95, ge=0.7, le=0.98)
    battery_c_rate_charge: float = Field(default=0.5, ge=0.1, le=2.0)
    battery_c_rate_discharge: float = Field(default=1.0, ge=0.1, le=3.0)
    battery_dod_max: float = Field(default=0.9, ge=0.1, le=1.0)
    battery_soc_min: float = Field(default=0.1, ge=0.05, le=0.3)
    battery_soc_max: float = Field(default=1.0, ge=0.8, le=1.0)
    battery_cycles_max: int = Field(default=8000, ge=500, le=25000)  # Based on battery type
    battery_degradation_per_cycle: float = Field(default=0.00001, ge=0.000005, le=0.001)
    
    # Phase 4C Load Profile Configuration - Extended
    load_profile_type: Literal["standard", "multi-shift", "24_7", "custom"] = "standard"
    load_peak_kw: float = Field(default=10.0, ge=1.0, le=100.0)
    load_base_kw: float = Field(default=2.0, ge=0.5, le=20.0)
    load_custom_hourly: Optional[List[float]] = Field(default=None, min_length=24, max_length=24)
    load_seasonal_variation: float = Field(default=0.2, ge=0.0, le=0.5)
    load_weekend_factor: float = Field(default=0.6, ge=0.3, le=1.0)
    load_night_factor: float = Field(default=0.3, ge=0.1, le=0.8)
    
    # Phase 4D Tariff Configuration
    tariff_region: Literal["ukraine"] = "ukraine"
    tariff_peak_hours_start: int = Field(default=6, ge=0, le=23)
    tariff_peak_hours_end: int = Field(default=23, ge=1, le=23)
    tariff_peak_rate_uah_kwh: float = Field(default=12.5, ge=5.0, le=25.0)
    tariff_off_peak_rate_uah_kwh: float = Field(default=8.0, ge=3.0, le=15.0)
    
    # Phase 4E ML Configuration
    ml_retrain_frequency_days: int = Field(default=7, ge=1, le=30)
    ml_confidence_threshold: float = Field(default=0.7, ge=0.5, le=0.95)
    ml_model_type: Literal["xgboost", "lightgbm", "catboost", "ensemble"] = "ensemble"
    ml_lookback_hours: int = Field(default=168, ge=24, le=720)  # 1 week default
    ml_forecast_horizon_hours: int = Field(default=24, ge=1, le=72)
    
    # Phase 4F Dashboard Preferences
    dashboard_refresh_seconds: int = Field(default=30, ge=5, le=300)
    dashboard_show_degradation_cost: bool = True
    dashboard_show_arbitrage_opportunities: bool = True
    dashboard_currency_symbol: str = "₴"
    dashboard_language: Literal["en", "uk"] = "en"
    
    # New Optimization Engine Configuration
    optimization_strategy: Literal["max_earn", "max_battery_health", "max_charge", "balanced"] = "balanced"
    custom_optimization_weights: Optional[Dict[str, float]] = None
    
    # New Renewable Energy Configuration
    has_solar: bool = False
    has_wind: bool = False
    solar_capacity_kw: float = Field(default=0.0, ge=0.0, le=1000.0)
    wind_capacity_kw: float = Field(default=0.0, ge=0.0, le=1000.0)
    solar_efficiency: float = Field(default=0.2, ge=0.1, le=0.35)
    wind_efficiency: float = Field(default=0.35, ge=0.2, le=0.6)
    solar_tilt_deg: float = Field(default=30.0, ge=0.0, le=90.0)
    wind_cut_in_speed_mps: float = Field(default=3.0, ge=1.0, le=10.0)
    wind_rated_speed_mps: float = Field(default=12.0, ge=4.0, le=30.0)
    latitude: float = Field(default=50.45, ge=-90.0, le=90.0)  # Default: Kyiv
    longitude: float = Field(default=30.52, ge=-180.0, le=180.0)  # Default: Kyiv
    timezone: str = "Europe/Kiev"
    
    # New Battery Physics Configuration
    enable_physics_simulation: bool = True
    battery_temperature_c: float = Field(default=25.0, ge=-20.0, le=60.0)
    battery_aging_model: Literal["calendar", "cycle", "combined"] = "combined"

    @field_validator("load_profile_type", mode="before")
    @classmethod
    def normalize_load_profile_type(cls, value: str) -> str:
        """Normalize legacy public tokens to one canonical machine token."""
        if value == "24/7":
            return "24_7"
        return value
    
    model_config = ConfigDict(extra='allow')


class UserConfigPayload(TypedDict, total=False):
    """Typed payload accepted when config is provided as a plain mapping."""

    battery_type: Literal["LFP", "Lead-Acid", "VRFB"]
    battery_capacity_kwh: float
    battery_efficiency: float
    battery_c_rate_charge: float
    battery_c_rate_discharge: float
    battery_dod_max: float
    battery_soc_min: float
    battery_soc_max: float
    battery_cycles_max: int
    battery_degradation_per_cycle: float
    load_profile_type: Literal["standard", "multi-shift", "24_7", "custom"]
    load_peak_kw: float
    load_base_kw: float
    load_custom_hourly: List[float]
    load_seasonal_variation: float
    load_weekend_factor: float
    load_night_factor: float
    tariff_region: Literal["ukraine"]
    tariff_peak_hours_start: int
    tariff_peak_hours_end: int
    tariff_peak_rate_uah_kwh: float
    tariff_off_peak_rate_uah_kwh: float
    ml_retrain_frequency_days: int
    ml_confidence_threshold: float
    ml_model_type: Literal["xgboost", "lightgbm", "catboost", "ensemble"]
    ml_lookback_hours: int
    ml_forecast_horizon_hours: int
    dashboard_refresh_seconds: int
    dashboard_show_degradation_cost: bool
    dashboard_show_arbitrage_opportunities: bool
    dashboard_currency_symbol: str
    dashboard_language: Literal["en", "uk"]
    optimization_strategy: Literal["max_earn", "max_battery_health", "max_charge", "balanced"]
    custom_optimization_weights: Dict[str, float]
    has_solar: bool
    has_wind: bool
    solar_capacity_kw: float
    wind_capacity_kw: float
    solar_efficiency: float
    wind_efficiency: float
    solar_tilt_deg: float
    wind_cut_in_speed_mps: float
    wind_rated_speed_mps: float
    latitude: float
    longitude: float
    timezone: str
    enable_physics_simulation: bool
    battery_temperature_c: float
    battery_aging_model: Literal["calendar", "cycle", "combined"]


class ConfigurationManagerError(RuntimeError):
    """Raised when configuration persistence or loading cannot complete."""


class ConfigurationOperationResult(BaseModel):
    """Shared result envelope for configuration operations."""

    success: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.success and not self.errors

    @property
    def status(self) -> str:
        return "success" if self.success else "error"

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


class ConfigLoadResult(ConfigurationOperationResult):
    """Result returned when loading persisted user configuration."""

    config: Optional[UserConfigModel] = None
    source: Literal["file", "defaults", "invalid", "input"] = "defaults"


class ConfigSaveResult(ConfigurationOperationResult):
    """Result returned when saving user configuration."""

    config: Optional[UserConfigModel] = None
    data: Optional[Dict[str, Any]] = None


class ConfigValidationResult(ConfigurationOperationResult):
    """Result returned when validating configuration inputs."""

    config: Optional[UserConfigModel] = None


class ConfigTriggerResult(ConfigurationOperationResult):
    """Result returned when triggering recalculation."""

    trigger_id: Optional[str] = None
    trigger_state: Literal["triggered", "failed"] = "failed"


def _load_user_config_support():
    from user_config_support import (
        BATTERY_TEMPLATE_CAPACITY_KWH,
        build_battery_templates,
        build_profile_templates,
        get_battery_specifications,
        get_load_profile_templates,
    )

    class _SupportModule:
        pass

    support_module = _SupportModule()
    support_module.BATTERY_TEMPLATE_CAPACITY_KWH = BATTERY_TEMPLATE_CAPACITY_KWH
    support_module.build_battery_templates = build_battery_templates
    support_module.build_profile_templates = build_profile_templates
    support_module.get_battery_specifications = get_battery_specifications
    support_module.get_load_profile_templates = get_load_profile_templates
    return support_module


try:
    _SUPPORT_MODULE = _load_user_config_support()
except ImportError:
    _SUPPORT_MODULE_NAME = "energy_ml_user_config_support"
    _SUPPORT_PATH = Path(__file__).with_name("user_config_support.py")
    _SUPPORT_SPEC = importlib.util.spec_from_file_location(_SUPPORT_MODULE_NAME, _SUPPORT_PATH)
    if _SUPPORT_SPEC is None or _SUPPORT_SPEC.loader is None:
        raise ImportError(f"Unable to load user config support module from {_SUPPORT_PATH}")
    _SUPPORT_MODULE = sys.modules.get(_SUPPORT_MODULE_NAME)
    if _SUPPORT_MODULE is None:
        _SUPPORT_MODULE = importlib.util.module_from_spec(_SUPPORT_SPEC)
        sys.modules[_SUPPORT_MODULE_NAME] = _SUPPORT_MODULE
        _SUPPORT_SPEC.loader.exec_module(_SUPPORT_MODULE)


BATTERY_TEMPLATE_CAPACITY_KWH = _SUPPORT_MODULE.BATTERY_TEMPLATE_CAPACITY_KWH


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConfigurationManager:
    """Manages user configuration persistence and validation with ML integration."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            config_dir: Directory to store configs (defaults to energy_ml/configs/)
        """
        if config_dir is None:
            env_config_dir = os.getenv('ENERGY_ML_CONFIG_DIR')
            config_dir = Path(env_config_dir) if env_config_dir else Path(__file__).resolve().parent / "configs"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "user_config.json"
        self.config_history_file = self.config_dir / "config_history.jsonl"
    
    def load_config(self) -> ConfigLoadResult:
        """Load user configuration from disk.
        
        Returns:
            ConfigLoadResult describing the source and parsed config
        """
        if not self.config_file.exists():
            return ConfigLoadResult(
                success=True,
                config=UserConfigModel(),
                source='defaults',
                warnings=["Configuration file not found; using defaults."],
            )

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return ConfigLoadResult(
                success=True,
                config=UserConfigModel(**data),
                source='file',
            )
        except json.JSONDecodeError as exc:
            return ConfigLoadResult(
                success=False,
                config=None,
                source='invalid',
                errors=[f"Configuration file contains invalid JSON: {exc}"],
            )
        except ValidationError as exc:
            return ConfigLoadResult(
                success=False,
                config=None,
                source='invalid',
                errors=[f"Configuration file failed validation: {exc}"],
            )
        except OSError as exc:
            return ConfigLoadResult(
                success=False,
                config=None,
                source='invalid',
                errors=[f"Configuration file could not be read: {exc}"],
            )

    def load_config_or_raise(self) -> UserConfigModel:
        """Return the resolved config or raise a typed error on failure."""
        result = self.load_config()
        if result.success and result.config is not None:
            return result.config

        error_text = "; ".join(result.errors) if result.errors else "Configuration could not be loaded"
        raise ConfigurationManagerError(error_text)

    def resolve_config(self, config_data: Optional[UserConfigPayload] = None) -> ConfigLoadResult:
        """Resolve config from an explicit payload or persisted storage without raising.

        Args:
            config_data: Optional mapping of user config values supplied by a caller.

        Returns:
            ConfigLoadResult containing either a parsed config or validation errors.
        """
        if config_data is None:
            return self.load_config()

        try:
            return ConfigLoadResult(
                success=True,
                config=UserConfigModel(**config_data),
                source='input',
            )
        except ValidationError as exc:
            return ConfigLoadResult(
                success=False,
                config=None,
                source='invalid',
                errors=[f"Provided configuration failed validation: {exc}"],
            )
    
    def save_config(self, config: UserConfigModel) -> ConfigSaveResult:
        """Save user configuration to disk with history tracking.
        
        Args:
            config: UserConfigModel to save
            
        Returns:
            ConfigSaveResult with the shared operation envelope
        """
        try:
            config_dict = config.model_dump()
            
            # Save current config
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2)
            
            # Save to history
            history_entry = {
                'timestamp': _utc_timestamp(),
                'config': config_dict
            }
            with open(self.config_history_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(history_entry) + '\n')
            
            return ConfigSaveResult(
                success=True,
                config=config,
                data=config_dict,
            )
        except Exception as exc:
            return ConfigSaveResult(
                success=False,
                config=None,
                data=None,
                errors=[str(exc)],
            )
    
    def validate_complete_config(self, config: UserConfigModel) -> ConfigValidationResult:
        """Comprehensive validation of all configuration parameters.
        
        Args:
            config: UserConfigModel to validate
            
        Returns:
            ConfigValidationResult with shared success, error, and warning fields
        """
        errors = []
        warnings = []
        
        # Battery validation
        battery_validation = self.validate_battery_config(
            config.battery_type, 
            config.battery_capacity_kwh, 
            config.battery_efficiency
        )
        errors.extend(battery_validation.errors)
        warnings.extend(battery_validation.warnings)
        
        # Load profile validation
        load_validation = self.validate_load_profile(
            config.load_profile_type,
            config.load_peak_kw
        )
        errors.extend(load_validation.errors)
        warnings.extend(load_validation.warnings)
        
        # Tariff validation
        if config.tariff_peak_hours_start >= config.tariff_peak_hours_end:
            errors.append("Peak hours start must be before peak hours end")
            
        if config.tariff_peak_rate_uah_kwh <= config.tariff_off_peak_rate_uah_kwh:
            warnings.append("Peak rate should be higher than off-peak rate for arbitrage opportunities")
        
        # Battery-Load compatibility check
        max_discharge_power = config.battery_capacity_kwh * config.battery_c_rate_discharge
        if max_discharge_power < config.load_peak_kw:
            warnings.append(f"Battery max discharge ({max_discharge_power:.1f}kW) < peak load ({config.load_peak_kw}kW)")
        
        # ML configuration validation
        if config.ml_lookback_hours < config.ml_forecast_horizon_hours:
            warnings.append("ML lookback hours should be much larger than forecast horizon")
        
        return ConfigValidationResult(
            success=len(errors) == 0,
            config=config,
            errors=errors,
            warnings=warnings,
        )
    
    def get_battery_specifications(self, battery_type: str, capacity_kwh: Optional[float] = None) -> Dict[str, Any]:
        """Get detailed battery specifications including degradation costs.
        
        Args:
            battery_type: One of 'LFP', 'Lead-Acid', 'VRFB'
            capacity_kwh: Optional installed capacity used to materialize cycle cost
            
        Returns:
            Dict with battery specs, degradation info, cost analysis
        """
        return _SUPPORT_MODULE.get_battery_specifications(battery_type, capacity_kwh)
    
    def get_load_profile_templates(self) -> Dict[str, Dict]:
        """Get enhanced load profile templates with hourly coefficients.
        
        Returns:
            Dict mapping profile type to detailed template with hourly data
        """
        return _SUPPORT_MODULE.get_load_profile_templates()
    
    def calculate_arbitrage_potential(self, config: UserConfigModel) -> Dict[str, float]:
        """Calculate arbitrage potential based on current configuration.
        
        Args:
            config: User configuration
            
        Returns:
            Dict with arbitrage metrics
        """
        battery_specs = self.get_battery_specifications(config.battery_type, config.battery_capacity_kwh)
        
        # Daily energy arbitrage calculation
        max_charge_power = config.battery_capacity_kwh * config.battery_c_rate_charge
        max_discharge_power = config.battery_capacity_kwh * config.battery_c_rate_discharge
        
        # Effective usable capacity (considering DoD limits)
        usable_capacity = config.battery_capacity_kwh * config.battery_dod_max
        
        # Price spread
        price_spread = config.tariff_peak_rate_uah_kwh - config.tariff_off_peak_rate_uah_kwh
        
        # Daily arbitrage revenue (gross)
        daily_arbitrage_gross = usable_capacity * price_spread * config.battery_efficiency
        
        # Degradation cost per cycle
        degradation_cost = battery_specs.get('degradation_cost_uah_per_cycle', 0) if battery_specs else 0
        
        # Net daily profit
        daily_profit_net = daily_arbitrage_gross - degradation_cost
        
        # Annual projections
        annual_cycles = 365
        annual_profit = daily_profit_net * annual_cycles
        
        # Payback period (assuming battery cost)
        battery_cost = config.battery_capacity_kwh * battery_specs.get('cost_uah_per_kwh', 13000) if battery_specs else 0
        payback_years = battery_cost / annual_profit if annual_profit > 0 else float('inf')
        
        return {
            'daily_arbitrage_gross': round(daily_arbitrage_gross, 2),
            'daily_degradation_cost': round(degradation_cost, 2),
            'daily_profit_net': round(daily_profit_net, 2),
            'annual_profit': round(annual_profit, 2),
            'battery_investment_cost': round(battery_cost, 2),
            'payback_period_years': round(payback_years, 1) if payback_years != float('inf') else None,
            'roi_percent': round((annual_profit / battery_cost * 100), 1) if battery_cost > 0 else 0,
            'usable_capacity_kwh': round(usable_capacity, 2),
            'max_charge_power_kw': round(max_charge_power, 2),
            'max_discharge_power_kw': round(max_discharge_power, 2)
        }
    
    def validate_battery_config(self, 
                               battery_type: str,
                               capacity_kwh: float,
                               efficiency: float = 0.95) -> ConfigValidationResult:
        """Validate battery configuration with enhanced checks.
        
        Args:
            battery_type: One of 'LFP', 'Lead-Acid', 'VRFB'
            capacity_kwh: Battery capacity in kWh (> 0)
            efficiency: Round-trip efficiency (0.7-1.0)
            
        Returns:
            ConfigValidationResult with shared success, error, and warning fields
        """
        errors = []
        warnings = []
        
        if battery_type not in ['LFP', 'Lead-Acid', 'VRFB']:
            errors.append(f"Invalid battery type: {battery_type}")
        
        if capacity_kwh <= 0:
            errors.append("Battery capacity must be > 0 kWh")
        elif capacity_kwh > 1000:
            errors.append("Battery capacity > 1000 kWh not supported")
        elif capacity_kwh < 5:
            warnings.append("Small battery capacity may limit arbitrage opportunities")
        
        if not (0.7 <= efficiency <= 1.0):
            errors.append("Battery efficiency must be between 0.7 and 1.0")
        elif efficiency < 0.8:
            warnings.append("Low efficiency reduces arbitrage profitability")
        
        # Battery type specific warnings
        if battery_type == 'Lead-Acid' and capacity_kwh > 20:
            warnings.append("Lead-acid batteries >20kWh have high maintenance requirements")
        elif battery_type == 'VRFB' and capacity_kwh < 50:
            warnings.append("VRFB systems are typically more cost-effective at >50kWh")
        
        return ConfigValidationResult(
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    def validate_load_profile(self,
                             profile_type: str,
                             peak_load_kw: float) -> ConfigValidationResult:
        """Validate load profile configuration with enhanced checks.
        
        Args:
            profile_type: One of 'standard', 'multi-shift', '24_7', 'custom'
            peak_load_kw: Peak load in kW (> 0)
            
        Returns:
            ConfigValidationResult with shared success, error, and warning fields
        """
        errors = []
        warnings = []
        
        if profile_type == '24/7':
            profile_type = '24_7'

        if profile_type not in ['standard', 'multi-shift', '24_7', 'custom']:
            errors.append(f"Invalid profile type: {profile_type}")
        
        if peak_load_kw <= 0:
            errors.append("Peak load must be > 0 kW")
        elif peak_load_kw > 500:
            errors.append("Peak load > 500 kW not supported")
        elif peak_load_kw < 2:
            warnings.append("Very low peak load may not justify battery investment")
        
        return ConfigValidationResult(
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    def get_battery_templates(self) -> Dict[str, Dict]:
        """Get battery configuration templates (deprecated - use get_battery_specifications).
        
        Returns:
            Dict mapping battery type to basic template
        """
        return _SUPPORT_MODULE.build_battery_templates()
    
    def get_profile_templates(self) -> Dict[str, Dict]:
        """Get load profile templates (deprecated - use get_load_profile_templates).
        
        Returns:
            Dict mapping profile type to description
        """
        return _SUPPORT_MODULE.build_profile_templates()
    
    def trigger_ml_recalculation(self, config: UserConfigModel) -> ConfigTriggerResult:
        """Trigger ML pipeline recalculation after config changes.
        
        Args:
            config: New configuration
            
        Returns:
            ConfigTriggerResult with shared success, error, and warning fields
        """
        try:
            # Save recalculation trigger file
            trigger_file = self.config_dir / "recalculation_trigger.json"
            config_payload = config.model_dump()
            trigger_data = {
                'timestamp': _utc_timestamp(),
                'config_hash': str(hash(str(config_payload))),
                'trigger_reason': 'configuration_update',
                'status': 'pending'
            }
            
            with open(trigger_file, 'w', encoding='utf-8') as f:
                json.dump(trigger_data, f, indent=2)
            
            return ConfigTriggerResult(
                success=True,
                trigger_id=trigger_data['config_hash'],
                trigger_state='triggered',
            )
            
        except Exception as exc:
            return ConfigTriggerResult(
                success=False,
                errors=[str(exc)],
                trigger_state='failed',
            )

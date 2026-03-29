"""Core load simulation engine for Phase 4C: Load Profile System.

Provides functions to generate hourly load time series for 365 days
using LoadProfileConfig from config_models.py. Includes:
- Base load simulation (always-on consumption)
- Seasonal adjustments (±20% summer/winter)
- Weekly patterns (weekends 15-25% lower)
- Random daily variations (±5% stochasticity)
- Self-consumption estimation
- Generation correlation with solar daylight pattern
"""
import importlib.util
from datetime import datetime
from pathlib import Path
import sys
from typing import Any, Dict, List

from energy_ml.config_models import LoadProfileConfig, UserProfile

try:
    from energy_ml.load_simulation_support import (
        apply_daily_noise as apply_daily_noise_value,
        apply_seasonal_factor as apply_seasonal_factor_value,
        apply_weekend_reduction as apply_weekend_reduction_value,
        build_yearly_load_report,
        estimate_self_consumption_metrics,
        simple_generation_series,
        simulate_year_hours,
    )
except ImportError:
    _SUPPORT_MODULE_NAME = "energy_ml.load_simulation_support"
    _SUPPORT_PATH = Path(__file__).with_name("load_simulation_support.py")
    _SUPPORT_SPEC = importlib.util.spec_from_file_location(_SUPPORT_MODULE_NAME, _SUPPORT_PATH)
    if _SUPPORT_SPEC is None or _SUPPORT_SPEC.loader is None:
        raise ImportError(f"Unable to load load simulation support module from {_SUPPORT_PATH}")
    _SUPPORT_MODULE = sys.modules.get(_SUPPORT_MODULE_NAME)
    if _SUPPORT_MODULE is None:
        _SUPPORT_MODULE = importlib.util.module_from_spec(_SUPPORT_SPEC)
        sys.modules[_SUPPORT_MODULE_NAME] = _SUPPORT_MODULE
        _SUPPORT_SPEC.loader.exec_module(_SUPPORT_MODULE)
    apply_daily_noise_value = _SUPPORT_MODULE.apply_daily_noise
    apply_seasonal_factor_value = _SUPPORT_MODULE.apply_seasonal_factor
    apply_weekend_reduction_value = _SUPPORT_MODULE.apply_weekend_reduction
    build_yearly_load_report = _SUPPORT_MODULE.build_yearly_load_report
    estimate_self_consumption_metrics = _SUPPORT_MODULE.estimate_self_consumption_metrics
    simple_generation_series = _SUPPORT_MODULE.simple_generation_series
    simulate_year_hours = _SUPPORT_MODULE.simulate_year_hours


class BaseLoadSimulator:
    """Abstract base class for load simulators.
    
    All simulators must implement:
    - get_hourly_coefficient(hour: int, day: int) -> float
    - simulate_year() -> List[float]
    """
    
    def __init__(self, profile: LoadProfileConfig, base_load_pct: float = 0.15):
        """Initialize simulator.
        
        Args:
            profile: LoadProfileConfig with hourly_coefficients and peak_load_kw
            base_load_pct: Base load as percentage of peak (default 15%)
        """
        self.profile = profile
        self.peak_load_kw = profile.peak_load_kw
        self.base_load_kw = base_load_pct * self.peak_load_kw
        self.hourly_coefficients = profile.hourly_coefficients
    
    def get_hourly_coefficient(self, hour: int, day: int) -> float:
        """Get hourly load coefficient (0-2.0 range).
        
        Override in subclasses for profile-specific logic.
        """
        return self.hourly_coefficients.get(hour, 0.1)
    
    def apply_seasonal_factor(self, day: int, factor: float = 0.2) -> float:
        """Apply seasonal variation (±20% by default).
        
        Uses sine curve: peak mid-year (day 182), valley at start/end.
        """
        return apply_seasonal_factor_value(day, factor)
    
    def apply_weekend_reduction(self, dow: int, coefficient: float, 
                               reduction: float = 0.6) -> float:
        """Apply weekend reduction to operational load.
        
        Args:
            dow: Day of week (0=Mon, 6=Sun)
            coefficient: Current hourly coefficient
            reduction: Multiplier for weekend loads (default 60% = -40%)
        """
        return apply_weekend_reduction_value(dow, coefficient, reduction)
    
    def apply_daily_noise(self, base_value: float, noise_pct: float = 0.05, 
                         seed: int = None) -> float:
        """Apply random daily variation (±5% by default).
        
        Args:
            base_value: Base load value in kW
            noise_pct: Noise as percentage of base (default ±5%)
            seed: Optional random seed for reproducibility
        """
        return apply_daily_noise_value(base_value, noise_pct, seed)
    
    def simulate_year(self, seasonal_factor: float = 0.2, 
                     weekend_reduction: float = 0.6,
                     random_seed: int = 42) -> List[float]:
        """Simulate 365 days of hourly loads.
        
        Returns:
            List of 8760 hourly load values in kWh
        """
        return simulate_year_hours(
            self.get_hourly_coefficient,
            self.peak_load_kw,
            self.base_load_kw,
            seasonal_factor,
            weekend_reduction,
            random_seed,
        )


class StandardWorkSimulator(BaseLoadSimulator):
    """Simulator for standard 9-18 office/retail operations."""
    
    def __init__(self, profile: LoadProfileConfig):
        super().__init__(profile, base_load_pct=0.15)
    
    def get_hourly_coefficient(self, hour: int, day: int) -> float:
        """9 AM - 6 PM peak load, low off-peak."""
        return self.hourly_coefficients.get(hour, 0.1)


class MultiShiftSimulator(BaseLoadSimulator):
    """Simulator for 2-shift manufacturing (6AM-2PM + 10PM-6AM)."""
    
    def __init__(self, profile: LoadProfileConfig):
        super().__init__(profile, base_load_pct=0.20)  # Slightly higher base load
    
    def get_hourly_coefficient(self, hour: int, day: int) -> float:
        """Two distinct shift periods."""
        return self.hourly_coefficients.get(hour, 0.2)


class ContinuousSimulator(BaseLoadSimulator):
    """Simulator for 24/7 continuous operations with minimal variation."""
    
    def __init__(self, profile: LoadProfileConfig):
        super().__init__(profile, base_load_pct=0.25)  # Higher base for continuous ops
    
    def get_hourly_coefficient(self, hour: int, day: int) -> float:
        """Steady 24/7 operation with slight maintenance dips."""
        return self.hourly_coefficients.get(hour, 0.8)


class CustomSimulator(BaseLoadSimulator):
    """Simulator for user-defined custom hourly profiles."""
    
    def __init__(self, profile: LoadProfileConfig, base_load_pct: float = 0.15):
        super().__init__(profile, base_load_pct)
    
    def get_hourly_coefficient(self, hour: int, day: int) -> float:
        """Use exactly the user-defined coefficients."""
        return self.hourly_coefficients.get(hour, 0.1)


def create_simulator(profile: LoadProfileConfig) -> BaseLoadSimulator:
    """Factory function to create appropriate simulator for profile type.
    
    Args:
        profile: LoadProfileConfig instance
    
    Returns:
        Appropriate simulator instance
    
    Raises:
        ValueError: If profile type is not recognized
    """
    if profile.profile_type == 'standard':
        return StandardWorkSimulator(profile)
    elif profile.profile_type == 'multi-shift':
        return MultiShiftSimulator(profile)
    elif profile.profile_type == '24_7':
        return ContinuousSimulator(profile)
    elif profile.profile_type == 'custom':
        return CustomSimulator(profile)
    else:
        raise ValueError(f"Unknown profile type: {profile.profile_type}")


def generate_yearly_load(profile: LoadProfileConfig,
                         start_date: datetime = None,
                         seasonal_factor: float = 0.2,
                         weekend_reduction: float = 0.6,
                         random_seed: int = 42) -> Dict[str, Any]:
    """Generate 8760 hourly load values for one non-leap year (365 days).

    Returns a dict with:
    - hourly: list of 8760 floats (kWh per hour)
    - daily_stats: list of 365 dicts with average, peak, min
    - overall: dict with annual statistics

    Args:
        profile: LoadProfileConfig instance
        start_date: Starting date (default: Jan 1 of current year)
        seasonal_factor: Seasonal variation amplitude (default 0.2 = ±20%)
        weekend_reduction: Weekend load reduction factor (default 0.6 = 60% of weekday)
        random_seed: Random seed for reproducibility

    Returns:
        Dict with keys: hourly, daily_stats, overall
    """
    simulator = create_simulator(profile)
    hours = simulator.simulate_year(seasonal_factor, weekend_reduction, random_seed)
    return build_yearly_load_report(hours, profile.peak_load_kw, start_date)


def estimate_self_consumption(load_hours: list, generation_hours: list) -> Dict[str, float]:
    """Estimate self-consumption percentage and peak shaving potential.

    Calculates what percentage of load can be met by on-site generation.
    Also estimates potential peak shaving from battery use with generation.

    Args:
        load_hours: List of 8760 hourly load values (kWh)
        generation_hours: List of 8760 hourly generation values (kWh)

    Returns:
        Dict with:
        - self_consumption_pct: % of load met by generation (0-100)
        - estimated_peak_shave_kW: Potential peak reduction with battery

    Raises:
        ValueError: If input lists have different lengths
    """
    return estimate_self_consumption_metrics(load_hours, generation_hours)


def simple_generation_hourly(profile: UserProfile, seed: int = 42) -> list:
    """Create a simple solar generation profile (hourly) for 365 days.

    Solar generation is approximated by a bell curve during daylight hours
    (6 AM - 6 PM) scaled by solar_capacity_kw and solar_efficiency.

    The curve uses a Gaussian approximation centered at noon with realistic
    daily variation to model weather effects.

    Args:
        profile: UserProfile with generation configuration
        seed: Random seed for reproducibility

    Returns:
        List of 8760 hourly generation values (kWh)
    """
    return simple_generation_series(profile, seed)


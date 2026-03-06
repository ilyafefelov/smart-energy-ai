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
from typing import Dict, Tuple, Any, List
import math
import random
from datetime import datetime, timedelta
import json

from energy_ml.config_models import LoadProfileConfig, UserProfile


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
        angle = 2 * math.pi * ((day - 91) / 365.0)
        return 1.0 + factor * math.sin(angle)
    
    def apply_weekend_reduction(self, dow: int, coefficient: float, 
                               reduction: float = 0.6) -> float:
        """Apply weekend reduction to operational load.
        
        Args:
            dow: Day of week (0=Mon, 6=Sun)
            coefficient: Current hourly coefficient
            reduction: Multiplier for weekend loads (default 60% = -40%)
        """
        if dow >= 5:  # Saturday=5, Sunday=6
            return coefficient * reduction
        return coefficient
    
    def apply_daily_noise(self, base_value: float, noise_pct: float = 0.05, 
                         seed: int = None) -> float:
        """Apply random daily variation (±5% by default).
        
        Args:
            base_value: Base load value in kW
            noise_pct: Noise as percentage of base (default ±5%)
            seed: Optional random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)
        noise = random.uniform(-noise_pct, noise_pct) * base_value
        return base_value + noise
    
    def simulate_year(self, seasonal_factor: float = 0.2, 
                     weekend_reduction: float = 0.6,
                     random_seed: int = 42) -> List[float]:
        """Simulate 365 days of hourly loads.
        
        Returns:
            List of 8760 hourly load values in kWh
        """
        random.seed(random_seed)
        hours = []
        start_date = datetime(datetime.now().year, 1, 1)
        current = start_date
        
        for day in range(365):
            day_multiplier = self.apply_seasonal_factor(day, seasonal_factor)
            dow = current.weekday()
            
            for hour in range(24):
                coeff = self.get_hourly_coefficient(hour, day)
                coeff = self.apply_weekend_reduction(dow, coeff, weekend_reduction)
                
                # Operational component
                operational = coeff * self.peak_load_kw * day_multiplier
                
                # Total load = base + operational + noise
                load = self.base_load_kw + operational
                load = self.apply_daily_noise(load, 0.05, random_seed + day * 24 + hour)
                
                # Constraints
                load = max(0.01, load)  # Always positive
                load = min(load, 1.05 * self.peak_load_kw)  # Cap at 1.05x peak
                
                hours.append(round(load, 3))
            
            current += timedelta(days=1)
        
        return hours


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
    # Create appropriate simulator
    simulator = create_simulator(profile)
    
    # Generate hourly loads
    hours = simulator.simulate_year(seasonal_factor, weekend_reduction, random_seed)
    
    # Calculate daily statistics
    daily_stats = []
    if start_date is None:
        start_date = datetime(datetime.now().year, 1, 1)
    
    current = start_date
    for day in range(365):
        day_start = day * 24
        day_end = day_start + 24
        day_vals = hours[day_start:day_end]
        
        daily_avg = sum(day_vals) / 24.0
        daily_peak = max(day_vals)
        daily_min = min(day_vals)
        
        daily_stats.append({
            "date": current.date().isoformat(),
            "average_kW": round(daily_avg, 3),
            "peak_kW": round(daily_peak, 3),
            "min_kW": round(daily_min, 3)
        })
        
        current += timedelta(days=1)
    
    # Calculate overall statistics
    overall = {
        "annual_energy_kwh": round(sum(hours), 3),
        "annual_peak_kW": round(max(hours), 3),
        "annual_min_kW": round(min(hours), 3),
        "daily_average_kwh": round(sum(hours) / 365.0, 3),
        "peak_load_configured_kw": round(profile.peak_load_kw, 3),
        "base_load_estimated_kw": round(min(hours), 3)
    }
    
    return {
        "hourly": hours,
        "daily_stats": daily_stats,
        "overall": overall
    }


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
    if len(load_hours) != len(generation_hours):
        raise ValueError("load_hours and generation_hours must be same length")

    total_load = sum(load_hours)
    used_generation = 0.0
    
    # Calculate actual self-consumption
    for l, g in zip(load_hours, generation_hours):
        used_generation += min(l, g)

    pct = 0.0
    if total_load > 0:
        pct = used_generation / total_load * 100.0

    # Estimate peak shaving potential
    # Calculate deficit hours (when load > generation)
    paired = [(l, g) for l, g in zip(load_hours, generation_hours)]
    deficits = [l - g for l, g in paired if l > g]
    
    if deficits:
        # Peak shaving estimate: average of top 5% deficit hours
        deficits_sorted = sorted(deficits, reverse=True)
        top_n = max(1, int(0.05 * len(deficits_sorted)))
        peak_shave = sum(deficits_sorted[:top_n]) / top_n
    else:
        peak_shave = 0.0

    return {
        "self_consumption_pct": round(pct, 2),
        "estimated_peak_shave_kW": round(peak_shave, 3)
    }


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
    random.seed(seed)
    hours = []
    solar_cap = profile.generation.solar_capacity_kw
    eff = profile.generation.solar_efficiency

    for day in range(365):
        for hour in range(24):
            if 6 <= hour <= 18 and solar_cap > 0:
                # Gaussian curve centered at 12 (noon)
                dist = (hour - 12) / 4.0
                value = solar_cap * eff * max(0.0, math.exp(-dist * dist))
                # Daily variability to model weather (clouds, etc.)
                value *= random.uniform(0.8, 1.1)
            else:
                value = 0.0
            
            hours.append(round(value, 3))
    
    return hours


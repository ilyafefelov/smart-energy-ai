"""Phase 4F: Pipeline Orchestrator - Full Integration of Phase 4 Components.

Orchestrates battery models, load profiles, tariffs, and user configuration
into a unified decision-making pipeline.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, TypedDict
import json
from pathlib import Path

import polars as pl
from pydantic import ValidationError

from energy_ml.user_config import UserConfigModel, ConfigurationManager
from energy_ml.config_models import BatteryConfig, LoadProfileConfig
from energy_ml.battery_degradation import BatteryModel
from energy_ml.load_simulation import StandardWorkSimulator
from energy_ml.tariff_models import UkraineTariffModel
from energy_ml.mlops.optimization_engine import OptimizationEngine
from energy_ml.mlops.battery_physics import BatteryPhysicsEngine
from energy_ml.mlops.renewable_forecasting import RenewableForecaster


logger = logging.getLogger(__name__)


class LivePriceForecastRow(TypedDict, total=False):
    hour: int
    price: float


class LivePriceSignal(TypedDict, total=False):
    current_uah_kwh: float
    forecast_next24h: List[LivePriceForecastRow]


class LiveBatterySignal(TypedDict, total=False):
    soc_percent: float
    soc: float
    health_percent: float
    health: float
    cycles_remaining: float


class LiveContextPayload(TypedDict, total=False):
    price_signal: LivePriceSignal
    battery_signal: LiveBatterySignal
    weather_signal: Dict[str, Any]


class RecommendationDetails(TypedDict):
    hour: int
    load_kw: float
    tariff_rate_uah_mwh: float
    battery_soc_percent: float
    battery_health_percent: float
    battery_cycles_remaining: float
    price_source: str
    is_peak_hour: bool
    charge_cost_uah_kwh: float
    discharge_revenue_uah_kwh: float
    degradation_cost_uah_kwh: float


class RecommendationPayload(TypedDict):
    action: str
    reasoning: str
    confidence: float
    estimated_savings: float
    battery_impact: float
    timestamp: str
    details: RecommendationDetails


class PipelineBatteryState(TypedDict):
    soc_percent: float
    health_percent: float
    cycles_remaining: float


class PipelineLoadStatus(TypedDict):
    type: str
    peak_kw: float
    current_hour: int
    current_load_kw: float


class PipelineTariffStatus(TypedDict):
    region: str
    current_rate_uah_mwh: float
    is_peak_hour: bool


class PipelineStatusPayload(TypedDict):
    config: Dict[str, Any]
    battery_state: PipelineBatteryState
    load_profile: PipelineLoadStatus
    tariff: PipelineTariffStatus
    last_recommendation: Optional[RecommendationPayload]
    timestamp: str


class DecisionThresholds(TypedDict):
    critical_health_floor: float
    buy_rate_divisor: float
    peak_sell_soc_floor: float
    peak_buy_soc_ceiling: float
    peak_sell_profit_ratio: float
    peak_sell_confidence: float
    peak_buy_confidence: float
    peak_hold_confidence: float
    off_peak_buy_soc_ceiling: float
    off_peak_sell_soc_floor: float
    off_peak_buy_discount_ratio: float
    off_peak_buy_confidence: float
    off_peak_sell_confidence: float
    off_peak_hold_confidence: float
    critical_health_confidence: float


DECISION_THRESHOLDS: DecisionThresholds = {
    'critical_health_floor': 20.0,
    'buy_rate_divisor': 1500.0,
    'peak_sell_soc_floor': 30.0,
    'peak_buy_soc_ceiling': 50.0,
    'peak_sell_profit_ratio': 1.3,
    'peak_sell_confidence': 0.85,
    'peak_buy_confidence': 0.75,
    'peak_hold_confidence': 0.80,
    'off_peak_buy_soc_ceiling': 80.0,
    'off_peak_sell_soc_floor': 70.0,
    'off_peak_buy_discount_ratio': 0.9,
    'off_peak_buy_confidence': 0.80,
    'off_peak_sell_confidence': 0.70,
    'off_peak_hold_confidence': 0.75,
    'critical_health_confidence': 0.9,
}


class PipelineOrchestrator:
    """Orchestrates all Phase 4 components into integrated pipeline.
    
    Integrates:
    - Battery models (Phase 4B): degradation, efficiency, health tracking
    - Load profiles (Phase 4C): realistic business operation simulation
    - Tariff models (Phase 4D): Ukraine 2026 NKREKU pricing
    - User configuration (Phase 4E): customizable system settings
    
    Produces recommendations: BUY, SELL, or HOLD energy from grid.
    """
    
    def __init__(self, user_config: Optional[UserConfigModel] = None):
        """Initialize orchestrator with user configuration.
        
        Args:
            user_config: UserConfigModel with battery, load, tariff settings.
                        If None, loads from disk or uses defaults.
        """
        self.config_manager = ConfigurationManager()
        resolved_config = user_config if user_config is not None else self.config_manager.load_config_or_raise()
        self._apply_user_config(resolved_config)
        self.tariff = UkraineTariffModel()
        
        # Initialize new MLOps components
        self.optimization_engine = OptimizationEngine()
        self.physics_engine = BatteryPhysicsEngine()
        self.renewable_forecaster = RenewableForecaster()
        
        # State tracking
        self._last_recommendation: Optional[RecommendationPayload] = None
        self._last_recommendation_time = None
        self._live_context: LiveContextPayload = {}
        self._live_price_map_kwh: Dict[int, float] = {}
        self._live_current_price_kwh: Optional[float] = None
        self._live_soc_percent: Optional[float] = None
        self._live_health_percent: Optional[float] = None
        self._live_cycles_remaining: Optional[float] = None

    def _apply_user_config(self, user_config: UserConfigModel) -> None:
        self.config = user_config
        self.battery_config = self._create_battery_config(user_config)
        self.load_config = self._create_load_config(user_config)
        self.battery = BatteryModel(self.battery_config)
        self.load_profile = StandardWorkSimulator(self.load_config)

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            numeric = float(value)
            if numeric != numeric:
                return default
            return numeric
        except Exception:
            return default

    def _parse_live_battery_state(
        self, battery_signal: Any
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        signal: LiveBatterySignal = battery_signal if isinstance(battery_signal, dict) else {}
        soc = self._safe_float(signal.get('soc_percent', signal.get('soc')), default=-1)
        health = self._safe_float(signal.get('health_percent', signal.get('health')), default=-1)
        cycles = self._safe_float(signal.get('cycles_remaining'), default=-1)

        return (
            soc if soc >= 0 else None,
            health if health >= 0 else None,
            cycles if cycles >= 0 else None,
        )

    def set_live_context(self, live_context: Optional[LiveContextPayload]) -> None:
        """Attach live signals and refresh the derived inference-time caches.

        This method replaces the stored live context and recomputes the cached
        price and battery signal snapshots consumed by recommendation logic.
        Invalid or missing fields clear the corresponding cached values instead
        of preserving stale state from previous calls.
        """
        context: LiveContextPayload = live_context if isinstance(live_context, dict) else {}
        self._live_context = context

        price_signal = context.get('price_signal') if isinstance(context.get('price_signal'), dict) else {}
        self._live_current_price_kwh = None
        self._live_price_map_kwh = {}

        current_price = self._safe_float(price_signal.get('current_uah_kwh'), default=-1)
        if current_price > 0:
            self._live_current_price_kwh = current_price

        forecast_rows = price_signal.get('forecast_next24h') if isinstance(price_signal.get('forecast_next24h'), list) else []
        for row in forecast_rows:
            if not isinstance(row, dict):
                continue
            try:
                hour = int(row.get('hour'))
            except Exception:
                logger.debug('Skipping live price row with invalid hour: %r', row.get('hour'))
                continue
            if hour < 0 or hour > 23:
                continue
            price = self._safe_float(row.get('price'), default=-1)
            if price <= 0:
                continue
            self._live_price_map_kwh[hour] = price

        (
            self._live_soc_percent,
            self._live_health_percent,
            self._live_cycles_remaining,
        ) = self._parse_live_battery_state(context.get('battery_signal'))

    def _resolve_tariff_rate_uah_mwh(self, hour: int) -> float:
        if hour in self._live_price_map_kwh:
            return self._live_price_map_kwh[hour] * 1000

        current_hour = datetime.now().hour
        if self._live_current_price_kwh is not None and current_hour == hour:
            return self._live_current_price_kwh * 1000

        return self.tariff.get_hourly_rate(hour)

    def _resolve_battery_state(self) -> Tuple[float, float, float]:
        default_soc = max(0.0, min(100.0, (self.config.battery_soc_min + self.config.battery_soc_max) * 50.0))
        default_health = 95.0
        default_cycles_remaining = float(max(self.config.battery_cycles_max * 0.8, 1))

        soc_percent = (
            self._live_soc_percent
            if self._live_soc_percent is not None
            else default_soc
        )
        health_percent = (
            self._live_health_percent
            if self._live_health_percent is not None
            else default_health
        )
        cycles_remaining = (
            self._live_cycles_remaining
            if self._live_cycles_remaining is not None
            else default_cycles_remaining
        )

        return (
            max(0.0, min(100.0, soc_percent)),
            max(0.0, min(100.0, health_percent)),
            max(1.0, cycles_remaining),
        )

    def _make_peak_hour_decision(
        self,
        current_hour: int,
        battery_soc: float,
        charge_cost: float,
        discharge_revenue: float,
        tariff_rate: float,
    ) -> Tuple[str, float, str]:
        thresholds = DECISION_THRESHOLDS
        if (
            battery_soc > thresholds['peak_sell_soc_floor']
            and discharge_revenue > charge_cost * thresholds['peak_sell_profit_ratio']
        ):
            return (
                'SELL',
                thresholds['peak_sell_confidence'],
                f"Peak hour ({current_hour}h) and profitable discharge opportunity.",
            )
        if (
            battery_soc < thresholds['peak_buy_soc_ceiling']
            and charge_cost < tariff_rate / thresholds['buy_rate_divisor']
        ):
            return (
                'BUY',
                thresholds['peak_buy_confidence'],
                'Charge battery during peak for off-peak discharge revenue.',
            )
        return (
            'HOLD',
            thresholds['peak_hold_confidence'],
            'Peak hour but conditions not favorable for action.',
        )

    def _make_off_peak_decision(
        self,
        tariff_rate: float,
        battery_soc: float,
        charge_cost: float,
        discharge_revenue: float,
    ) -> Tuple[str, float, str]:
        thresholds = DECISION_THRESHOLDS
        if (
            battery_soc < thresholds['off_peak_buy_soc_ceiling']
            and charge_cost
            < (tariff_rate / thresholds['buy_rate_divisor'])
            * thresholds['off_peak_buy_discount_ratio']
        ):
            return (
                'BUY',
                thresholds['off_peak_buy_confidence'],
                f"Off-peak charging opportunity at {tariff_rate:.0f} UAH/MWh.",
            )
        if (
            battery_soc > thresholds['off_peak_sell_soc_floor']
            and discharge_revenue > charge_cost
        ):
            return (
                'SELL',
                thresholds['off_peak_sell_confidence'],
                'Discharge battery during low-demand off-peak period.',
            )
        return (
            'HOLD',
            thresholds['off_peak_hold_confidence'],
            'Off-peak but insufficient incentive for action.',
        )
    
    def _create_battery_config(self, user_config: UserConfigModel) -> BatteryConfig:
        """Convert UserConfigModel to BatteryConfig."""
        return BatteryConfig(
            type=user_config.battery_type,
            capacity_kwh=user_config.battery_capacity_kwh,
            efficiency=user_config.battery_efficiency,
            max_charge_rate_kw=user_config.battery_capacity_kwh * 0.5,  # 30min charge time
            max_discharge_rate_kw=user_config.battery_capacity_kwh * 0.5,  # 30min discharge time
        )
    
    def _create_load_config(self, user_config: UserConfigModel) -> LoadProfileConfig:
        """Convert UserConfigModel to LoadProfileConfig."""
        # Define standard hourly coefficients
        standard_coefficients = {
            0: 0.1, 1: 0.1, 2: 0.1, 3: 0.1, 4: 0.1, 5: 0.1,  # Night
            6: 0.3, 7: 0.6, 8: 0.9, 9: 1.0, 10: 1.0, 11: 1.0,  # Morning ramp
            12: 0.9, 13: 0.8, 14: 0.9, 15: 1.0, 16: 1.0, 17: 1.0,  # Afternoon
            18: 0.7, 19: 0.6, 20: 0.4, 21: 0.3, 22: 0.2, 23: 0.1,  # Evening ramp down
        }
        
        return LoadProfileConfig(
            profile_type=user_config.load_profile_type,
            name=f"User {user_config.load_profile_type}",
            description=f"User-configured {user_config.load_profile_type} load profile",
            peak_load_kw=user_config.load_peak_kw,
            hourly_coefficients=standard_coefficients,
        )
    
    def calculate_recommendation(self, 
                               user_config: Optional[UserConfigModel] = None,
                               current_hour: Optional[int] = None) -> RecommendationPayload:
        """Calculate optimal energy action for current hour.
        
        Main pipeline entry point that integrates:
        1. Load profile for current hour (business operation load)
        2. Tariff pricing for current hour (on-peak vs off-peak)
        3. Battery state (SOC, health, remaining cycles)
        4. Economic decision logic (savings potential)
        
        Args:
            user_config: Optional UserConfigModel to override loaded config
            current_hour: Optional hour (0-23) for testing. Defaults to now.
        
        Returns:
            dict with keys:
            - action: str ('BUY', 'SELL', or 'HOLD')
            - reasoning: str (explanation of decision)
            - confidence: float (0.0-1.0, decision certainty)
            - estimated_savings: float (estimated UAH savings from this action)
            - battery_impact: float (% battery health impact)
            - timestamp: str (ISO 8601)
            - details: dict (additional metrics for analysis)
        """
        # Use provided config or existing
        if user_config is not None:
            self._apply_user_config(user_config)
        
        # Determine current hour
        if current_hour is None:
            current_hour = datetime.now().hour
        
        current_hour = int(current_hour) % 24
        
        # Get current state
        load_kw = self.load_profile.get_hourly_coefficient(current_hour, 0) * self.config.load_peak_kw
        tariff_rate = self._resolve_tariff_rate_uah_mwh(current_hour)
        battery_soc, battery_health, cycles_remaining = self._resolve_battery_state()
        
        # Validation
        is_valid, errors = self.validate_all_inputs()
        if not is_valid:
            logger.warning(f"Configuration validation warnings: {errors}")
        
        # Determine peak/off-peak
        is_peak_hour = 6 <= current_hour < 23
        
        # Calculate economic metrics
        battery_degradation_cost = self._calculate_degradation_cost()
        charge_cost = tariff_rate * self.config.battery_efficiency / 1000  # UAH/kWh
        discharge_revenue = tariff_rate * 0.9 / 1000  # 90% of tariff (losses)
        
        # Decision logic
        action, confidence, reasoning = self._make_decision(
            load_kw=load_kw,
            tariff_rate=tariff_rate,
            battery_soc=battery_soc,
            battery_health=battery_health,
            charge_cost=charge_cost,
            discharge_revenue=discharge_revenue,
            degradation_cost=battery_degradation_cost,
            is_peak_hour=is_peak_hour,
            current_hour=current_hour
        )
        
        # Calculate estimated savings
        estimated_savings = self._calculate_savings(
            action=action,
            charge_cost=charge_cost,
            discharge_revenue=discharge_revenue,
            load_kw=load_kw
        )
        
        # Battery impact
        battery_impact = self._calculate_battery_impact(action)
        
        timestamp = datetime.now().isoformat()
        
        recommendation: RecommendationPayload = {
            'action': action,
            'reasoning': reasoning,
            'confidence': confidence,
            'estimated_savings': estimated_savings,
            'battery_impact': battery_impact,
            'timestamp': timestamp,
            'details': {
                'hour': current_hour,
                'load_kw': load_kw,
                'tariff_rate_uah_mwh': tariff_rate,
                'battery_soc_percent': battery_soc,
                'battery_health_percent': battery_health,
                'battery_cycles_remaining': cycles_remaining,
                'price_source': 'live_market' if current_hour in self._live_price_map_kwh else 'tariff_model',
                'is_peak_hour': is_peak_hour,
                'charge_cost_uah_kwh': charge_cost,
                'discharge_revenue_uah_kwh': discharge_revenue,
                'degradation_cost_uah_kwh': battery_degradation_cost,
            }
        }
        
        self._last_recommendation = recommendation
        self._last_recommendation_time = datetime.now()
        
        return recommendation
    
    def _make_decision(self, 
                       load_kw: float,
                       tariff_rate: float,
                       battery_soc: float,
                       battery_health: float,
                       charge_cost: float,
                       discharge_revenue: float,
                       degradation_cost: float,
                       is_peak_hour: bool,
                       current_hour: int) -> Tuple[str, float, str]:
        """Make BUY/SELL/HOLD decision based on economic analysis.
        
        Args:
            load_kw: Current load in kW
            tariff_rate: Tariff rate in UAH/MWh
            battery_soc: Battery state of charge (0-100%)
            battery_health: Battery health (0-100%)
            charge_cost: Cost to charge battery (UAH/kWh)
            discharge_revenue: Revenue from discharge (UAH/kWh)
            degradation_cost: Degradation cost per cycle (UAH/kWh)
            is_peak_hour: Whether current hour is peak pricing
            current_hour: Current hour (0-23)
        
        Returns:
            Tuple of (action, confidence, reasoning)
        """
        thresholds = DECISION_THRESHOLDS

        # Don't discharge if health is degrading
        if battery_health < thresholds['critical_health_floor']:
            return (
                'HOLD',
                thresholds['critical_health_confidence'],
                f"Battery health critical ({battery_health:.1f}%). Cannot discharge.",
            )

        if is_peak_hour:
            return self._make_peak_hour_decision(
                current_hour=current_hour,
                battery_soc=battery_soc,
                charge_cost=charge_cost,
                discharge_revenue=discharge_revenue,
                tariff_rate=tariff_rate,
            )

        return self._make_off_peak_decision(
            tariff_rate=tariff_rate,
            battery_soc=battery_soc,
            charge_cost=charge_cost,
            discharge_revenue=discharge_revenue,
        )
        
    def _calculate_degradation_cost(self) -> float:
        """Calculate battery degradation cost per kWh cycled.
        
        Returns:
            Cost in UAH/kWh
        """
        try:
            cycles_remaining = self.battery_config.cycles_to_eol
            battery_cost_uah = 50000  # Estimated battery cost in UAH
            cost_per_cycle = battery_cost_uah / max(cycles_remaining, 100)
            degradation_per_kwh = cost_per_cycle / self.config.battery_capacity_kwh
            return degradation_per_kwh
        except Exception as e:
            logger.error(f"Error calculating degradation cost: {e}")
            return 0.1
    
    def _calculate_savings(self, 
                          action: str,
                          charge_cost: float,
                          discharge_revenue: float,
                          load_kw: float) -> float:
        """Calculate estimated savings from recommended action.
        
        Args:
            action: 'BUY', 'SELL', or 'HOLD'
            charge_cost: Cost to charge (UAH/kWh)
            discharge_revenue: Revenue from discharge (UAH/kWh)
            load_kw: Current load in kW
        
        Returns:
            Estimated savings in UAH
        """
        if action == 'SELL' and load_kw > 0:
            # Discharge to reduce grid consumption
            discharge_savings = discharge_revenue * load_kw
            return discharge_savings
        elif action == 'BUY' and load_kw > 0:
            # Charge battery for later use (avoid peak charging)
            future_peak_rate = 0.75  # 75% higher during peak
            charge_benefit = (charge_cost * future_peak_rate) * load_kw
            return charge_benefit
        else:
            return 0.0
    
    def _calculate_battery_impact(self, action: str) -> float:
        """Calculate battery health impact from action.
        
        Args:
            action: 'BUY', 'SELL', or 'HOLD'
        
        Returns:
            Health loss as percentage (0.0-1.0 per cycle)
        """
        if action == 'BUY':
            # Charging impact: ~0.01% per cycle for LFP
            return 0.01
        elif action == 'SELL':
            # Discharging impact: ~0.05% per cycle for LFP
            return 0.05
        else:
            return 0.0
    
    def validate_all_inputs(self) -> Tuple[bool, List[str]]:
        """Validate battery, load, tariff, and config inputs.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Validate battery config
        if self.config.battery_capacity_kwh <= 0:
            errors.append(f"Invalid battery capacity: {self.config.battery_capacity_kwh}")
        
        if not (0.7 <= self.config.battery_efficiency <= 1.0):
            errors.append(f"Invalid efficiency: {self.config.battery_efficiency}")
        
        if self.config.battery_type not in ['LFP', 'Lead-Acid', 'VRFB']:
            errors.append(f"Unknown battery type: {self.config.battery_type}")
        
        # Validate load profile
        if self.config.load_peak_kw <= 0:
            errors.append(f"Invalid peak load: {self.config.load_peak_kw}")
        
        if self.config.load_profile_type not in ['standard', 'multi-shift', '24_7', 'custom']:
            errors.append(f"Unknown load profile: {self.config.load_profile_type}")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def get_hourly_forecast(self, hours: int = 24) -> pl.DataFrame:
        """Generate 24-hour forecast of recommendations.
        
        Args:
            hours: Number of hours to forecast (default 24)
        
        Returns:
            DataFrame with columns: hour, action, confidence, reasoning, savings_estimate
        """
        start_hour = datetime.now().hour
        forecasts = []
        
        for offset in range(hours):
            hour = (start_hour + offset) % 24
            recommendation = self.calculate_recommendation(current_hour=hour)
            
            forecasts.append({
                'hour': hour,
                'action': recommendation['action'],
                'confidence': recommendation['confidence'],
                'reasoning': recommendation['reasoning'],
                'savings_estimate': recommendation['estimated_savings'],
                'battery_impact': recommendation['battery_impact'],
            })
        
        return pl.DataFrame(forecasts)
    def get_status(self) -> PipelineStatusPayload:
        """Get current pipeline status and state.
        
        Returns:
            Dictionary with all component states
        """
        current_hour = datetime.now().hour
        load_kw = self.load_profile.get_hourly_coefficient(current_hour, 0) * self.config.load_peak_kw
        soc_percent, health_percent, cycles_remaining = self._resolve_battery_state()
        
        return {
            'config': self.config.model_dump() if hasattr(self.config, 'model_dump') else self.config.dict(),
            'battery_state': {
                'soc_percent': soc_percent,
                'health_percent': health_percent,
                'cycles_remaining': cycles_remaining,
            },
            'load_profile': {
                'type': self.config.load_profile_type,
                'peak_kw': self.config.load_peak_kw,
                'current_hour': current_hour,
                'current_load_kw': load_kw,
            },
            'tariff': {
                'region': self.config.tariff_region,
                'current_rate_uah_mwh': self._resolve_tariff_rate_uah_mwh(current_hour),
                'is_peak_hour': 6 <= current_hour < 23,
            },
            'last_recommendation': self._last_recommendation,
            'timestamp': datetime.now().isoformat(),
        }

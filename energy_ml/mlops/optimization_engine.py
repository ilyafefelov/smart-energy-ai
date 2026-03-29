"""
Optimization Engine for User Preferences Integration

Handles user optimization strategies:
- Max Earn: Maximize financial returns
- Max Battery Health: Minimize degradation
- Max Charge: Maintain high charge availability
"""
import importlib.util
import logging
from pathlib import Path
from datetime import datetime
import sys
from typing import Any, Dict, Optional, Tuple

from energy_ml.user_config import UserConfigModel

try:
    from energy_ml.mlops.optimization_engine_support import (
        build_optimized_prediction,
        build_strategy_info,
        build_strategy_response,
        calculate_action_score,
        calculate_confidence_adjustment,
        check_constraints,
        generate_optimization_reasoning,
        resolve_weights,
    )
except ImportError:
    _SUPPORT_MODULE_NAME = "energy_ml.mlops.optimization_engine_support"
    _SUPPORT_PATH = Path(__file__).with_name("optimization_engine_support.py")
    _SUPPORT_SPEC = importlib.util.spec_from_file_location(_SUPPORT_MODULE_NAME, _SUPPORT_PATH)
    if _SUPPORT_SPEC is None or _SUPPORT_SPEC.loader is None:
        raise ImportError(f"Unable to load optimization engine support module from {_SUPPORT_PATH}")
    _SUPPORT_MODULE = sys.modules.get(_SUPPORT_MODULE_NAME)
    if _SUPPORT_MODULE is None:
        _SUPPORT_MODULE = importlib.util.module_from_spec(_SUPPORT_SPEC)
        sys.modules[_SUPPORT_MODULE_NAME] = _SUPPORT_MODULE
        _SUPPORT_SPEC.loader.exec_module(_SUPPORT_MODULE)
    build_optimized_prediction = _SUPPORT_MODULE.build_optimized_prediction
    build_strategy_info = _SUPPORT_MODULE.build_strategy_info
    build_strategy_response = _SUPPORT_MODULE.build_strategy_response
    calculate_action_score = _SUPPORT_MODULE.calculate_action_score
    calculate_confidence_adjustment = _SUPPORT_MODULE.calculate_confidence_adjustment
    check_constraints = _SUPPORT_MODULE.check_constraints
    generate_optimization_reasoning = _SUPPORT_MODULE.generate_optimization_reasoning
    resolve_weights = _SUPPORT_MODULE.resolve_weights

logger = logging.getLogger(__name__)


class OptimizationEngine:
    """Engine for optimizing energy decisions based on user preferences."""
    
    OPTIMIZATION_STRATEGIES = {
        'max_earn': {
            'description': 'Maximize financial returns from energy trading',
            'weights': {'earnings': 0.8, 'battery_health': 0.1, 'charge_availability': 0.1},
            'constraints': {'min_soc': 20, 'max_cycles_per_day': 10}
        },
        'max_battery_health': {
            'description': 'Minimize battery degradation and maximize lifespan',
            'weights': {'earnings': 0.2, 'battery_health': 0.7, 'charge_availability': 0.1},
            'constraints': {'min_soc': 40, 'max_cycles_per_day': 2}
        },
        'max_charge': {
            'description': 'Maintain high charge availability for reliability',
            'weights': {'earnings': 0.3, 'battery_health': 0.2, 'charge_availability': 0.5},
            'constraints': {'min_soc': 60, 'max_cycles_per_day': 4}
        },
        'balanced': {
            'description': 'Balanced approach considering all factors',
            'weights': {'earnings': 0.4, 'battery_health': 0.4, 'charge_availability': 0.2},
            'constraints': {'min_soc': 30, 'max_cycles_per_day': 6}
        }
    }
    
    def __init__(self):
        """Initialize optimization engine."""
        self.current_strategy = 'balanced'
        self.custom_weights = None
        self.daily_cycle_count = 0

    def _build_strategy_response(
        self,
        strategy: str,
        strategy_config: Dict[str, Any],
        *,
        success: bool,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return a stable public envelope for strategy lookups."""
        return build_strategy_response(
            strategy,
            strategy_config,
            self.custom_weights,
            datetime.now().isoformat(),
            success=success,
            error=error,
        )
        
    def get_user_strategy(self, user_config: UserConfigModel) -> Dict[str, Any]:
        """Load user optimization strategy from configuration.
        
        Args:
            user_config: User configuration model
            
        Returns:
            dict with strategy details
        """
        try:
            # Get strategy from user config (extend UserConfigModel to include this)
            strategy = getattr(user_config, 'optimization_strategy', 'balanced')
            
            if strategy not in self.OPTIMIZATION_STRATEGIES:
                logger.warning(f"Unknown strategy {strategy}, using balanced")
                strategy = 'balanced'
            
            self.current_strategy = strategy
            strategy_config = self.OPTIMIZATION_STRATEGIES[strategy].copy()
            self.custom_weights = None
            
            # Allow user to override weights if they have custom preferences
            custom_weights = getattr(user_config, 'custom_optimization_weights', None)
            if custom_weights:
                self.custom_weights = custom_weights
                strategy_config['weights'].update(custom_weights)
            
            logger.info(f"Loaded optimization strategy: {strategy}")
            return self._build_strategy_response(strategy, strategy_config, success=True)
            
        except Exception as e:
            logger.error(f"Error loading user strategy: {e}")
            self.current_strategy = 'balanced'
            self.custom_weights = None
            return self._build_strategy_response(
                'balanced',
                self.OPTIMIZATION_STRATEGIES['balanced'],
                success=False,
                error=str(e),
            )
    
    def optimize_decision(self, 
                         base_prediction: Dict[str, Any],
                         strategy: str,
                         physics_data: Dict[str, Any] = None,
                         renewable_data: Dict[str, Any] = None,
                         weights: Dict[str, float] = None) -> Dict[str, Any]:
        """Optimize prediction based on user strategy.
        
        Args:
            base_prediction: Base ML model prediction
            strategy: Optimization strategy ('max_earn', 'max_battery_health', etc.)
            physics_data: Battery physics simulation data
            renewable_data: Renewable generation forecast data
            weights: Custom optimization weights
            
        Returns:
            optimized prediction dict
        """
        try:
            weights = resolve_weights(strategy, self.OPTIMIZATION_STRATEGIES, weights)
            base_action = base_prediction.get('action', 'HOLD')
            base_confidence = base_prediction.get('confidence', 0.5)
            current_hour = datetime.now().hour
            action_scores = {}
            for action in ['BUY', 'SELL', 'HOLD']:
                action_scores[action] = self._calculate_action_score(
                    action,
                    weights,
                    physics_data,
                    renewable_data,
                    strategy,
                    current_hour=current_hour,
                )

            best_action = max(action_scores.keys(), key=lambda x: action_scores[x])
            best_score = action_scores[best_action]
            confidence_adjustment = self._calculate_confidence_adjustment(
                base_action, best_action, best_score, strategy
            )
            new_confidence = min(1.0, max(0.0, base_confidence + confidence_adjustment))
            reasoning = self._generate_optimization_reasoning(
                base_action, best_action, strategy, action_scores, physics_data
            )
            constraints_met, constraint_message = self._check_constraints(
                best_action, strategy, physics_data
            )
            if not constraints_met:
                best_action = 'HOLD'
                reasoning = f"{constraint_message} {reasoning}"
                new_confidence *= 0.8

            optimized_prediction = build_optimized_prediction(
                base_prediction,
                best_action,
                new_confidence,
                reasoning,
                strategy,
                action_scores,
                constraints_met,
                constraint_message,
                datetime.now().isoformat(),
            )

            logger.info(f"Optimized decision: {base_action} -> {best_action} (strategy: {strategy})")
            return optimized_prediction
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            # Return base prediction with error info
            return {
                **base_prediction,
                'optimization_applied': False,
                'optimization_error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _calculate_action_score(self, 
                               action: str,
                               weights: Dict[str, float],
                               physics_data: Dict[str, Any],
                               renewable_data: Dict[str, Any],
                               strategy: str,
                               current_hour: Optional[int] = None) -> float:
        """Calculate optimization score for a specific action.
        
        Args:
            action: Action to score ('BUY', 'SELL', 'HOLD')
            weights: Optimization weights
            physics_data: Battery physics data
            renewable_data: Renewable data
            strategy: Current strategy
            
        Returns:
            Optimization score (0-1, higher is better)
        """
        try:
            return calculate_action_score(
                action,
                weights,
                physics_data,
                renewable_data,
                current_hour if current_hour is not None else datetime.now().hour,
            )
            
        except Exception as e:
            logger.error(f"Error calculating action score: {e}")
            return 0.5  # Neutral score on error
    
    def _calculate_earnings_score(self, action: str, renewable_data: Dict[str, Any]) -> float:
        """Calculate earnings potential score for action."""
        return calculate_action_score(
            action,
            {'earnings': 1.0, 'battery_health': 0.0, 'charge_availability': 0.0},
            None,
            renewable_data,
            datetime.now().hour,
        )
    
    def _calculate_battery_health_score(self, action: str, physics_data: Dict[str, Any]) -> float:
        """Calculate battery health impact score for action."""
        return calculate_action_score(
            action,
            {'earnings': 0.0, 'battery_health': 1.0, 'charge_availability': 0.0},
            physics_data,
            None,
            datetime.now().hour,
        )
    
    def _calculate_charge_availability_score(self, action: str, physics_data: Dict[str, Any]) -> float:
        """Calculate charge availability score for action."""
        return calculate_action_score(
            action,
            {'earnings': 0.0, 'battery_health': 0.0, 'charge_availability': 1.0},
            physics_data,
            None,
            datetime.now().hour,
        )
    
    def _calculate_confidence_adjustment(self, 
                                       base_action: str,
                                       optimized_action: str,
                                       optimization_score: float,
                                       strategy: str) -> float:
        """Calculate confidence adjustment based on optimization."""
        return calculate_confidence_adjustment(base_action, optimized_action, optimization_score)
    
    def _generate_optimization_reasoning(self, 
                                       base_action: str,
                                       optimized_action: str,
                                       strategy: str,
                                       action_scores: Dict[str, float],
                                       physics_data: Dict[str, Any]) -> str:
        """Generate human-readable reasoning for optimization decision."""
        strategy_desc = self.OPTIMIZATION_STRATEGIES.get(strategy, {}).get('description', strategy)
        return generate_optimization_reasoning(base_action, optimized_action, strategy_desc, action_scores)
    
    def _check_constraints(self, 
                          action: str,
                          strategy: str,
                          physics_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if action meets strategy constraints."""
        return check_constraints(
            action,
            strategy,
            self.OPTIMIZATION_STRATEGIES,
            self.daily_cycle_count,
            physics_data,
        )
    
    def update_daily_cycles(self, action: str):
        """Update daily cycle count."""
        if action in ['BUY', 'SELL']:
            self.daily_cycle_count += 1
    
    def reset_daily_cycles(self):
        """Reset daily cycle count (call at midnight)."""
        self.daily_cycle_count = 0
    
    def get_strategy_info(self, strategy: str = None) -> Dict[str, Any]:
        """Get information about optimization strategy."""
        if strategy is None:
            strategy = self.current_strategy
        return build_strategy_info(strategy, self.OPTIMIZATION_STRATEGIES, self.daily_cycle_count)
"""
Optimization Engine for User Preferences Integration

Handles user optimization strategies:
- Max Earn: Maximize financial returns
- Max Battery Health: Minimize degradation
- Max Charge: Maintain high charge availability
"""
import logging
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import json

from energy_ml.user_config import UserConfigModel

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
        return {
            'strategy': strategy,
            'description': strategy_config['description'],
            'weights': dict(strategy_config['weights']),
            'constraints': dict(strategy_config['constraints']),
            'custom_weights': self.custom_weights,
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'error': error,
        }
        
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
            # Use provided weights or load from strategy
            if weights is None:
                if strategy in self.OPTIMIZATION_STRATEGIES:
                    weights = self.OPTIMIZATION_STRATEGIES[strategy]['weights']
                else:
                    weights = self.OPTIMIZATION_STRATEGIES['balanced']['weights']
            
            # Get base prediction details
            base_action = base_prediction.get('action', 'HOLD')
            base_confidence = base_prediction.get('confidence', 0.5)
            
            # Calculate optimization scores for each possible action
            action_scores = {}
            for action in ['BUY', 'SELL', 'HOLD']:
                score = self._calculate_action_score(
                    action, weights, physics_data, renewable_data, strategy
                )
                action_scores[action] = score
            
            # Find best action
            best_action = max(action_scores.keys(), key=lambda x: action_scores[x])
            best_score = action_scores[best_action]
            
            # Calculate new confidence based on optimization
            confidence_adjustment = self._calculate_confidence_adjustment(
                base_action, best_action, best_score, strategy
            )
            new_confidence = min(1.0, max(0.0, base_confidence + confidence_adjustment))
            
            # Generate optimization reasoning
            reasoning = self._generate_optimization_reasoning(
                base_action, best_action, strategy, action_scores, physics_data
            )
            
            # Check strategy constraints
            constraints_met, constraint_message = self._check_constraints(
                best_action, strategy, physics_data
            )
            
            if not constraints_met:
                # Override to HOLD if constraints not met
                best_action = 'HOLD'
                reasoning = f"{constraint_message} {reasoning}"
                new_confidence *= 0.8  # Reduce confidence due to constraint violation
            
            # Build optimized prediction
            optimized_prediction = {
                **base_prediction,  # Keep all base prediction data
                'action': best_action,
                'confidence': new_confidence,
                'reasoning': reasoning,
                'optimization_strategy': strategy,
                'action_scores': action_scores,
                'constraints_met': constraints_met,
                'constraint_message': constraint_message,
                'base_action': base_action,
                'optimization_applied': True,
                'timestamp': datetime.now().isoformat()
            }
            
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
                               strategy: str) -> float:
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
            # Base scores for each criterion
            earnings_score = self._calculate_earnings_score(action, renewable_data)
            battery_health_score = self._calculate_battery_health_score(action, physics_data)
            charge_availability_score = self._calculate_charge_availability_score(action, physics_data)
            
            # Weighted sum
            total_score = (
                earnings_score * weights.get('earnings', 0.33) +
                battery_health_score * weights.get('battery_health', 0.33) +
                charge_availability_score * weights.get('charge_availability', 0.33)
            )
            
            return min(1.0, max(0.0, total_score))
            
        except Exception as e:
            logger.error(f"Error calculating action score: {e}")
            return 0.5  # Neutral score on error
    
    def _calculate_earnings_score(self, action: str, renewable_data: Dict[str, Any]) -> float:
        """Calculate earnings potential score for action."""
        # Mock earnings calculation - in real implementation, use market data
        current_hour = datetime.now().hour
        is_peak = 6 <= current_hour < 23
        
        # Check if renewable generation is available
        renewable_available = False
        if renewable_data and renewable_data.get('status') == 'success':
            total_renewable = renewable_data.get('total_renewable', {})
            current_generation = total_renewable.get(f'hour_{current_hour}', 0)
            renewable_available = current_generation > 0
        
        if action == 'SELL':
            # Higher score for selling during peak hours or when renewable generation is high
            if is_peak:
                return 0.9 + (0.1 if renewable_available else 0)
            else:
                return 0.4 + (0.2 if renewable_available else 0)
                
        elif action == 'BUY':
            # Higher score for buying during off-peak hours
            if not is_peak:
                return 0.8
            else:
                return 0.3
                
        else:  # HOLD
            return 0.5  # Neutral earnings
    
    def _calculate_battery_health_score(self, action: str, physics_data: Dict[str, Any]) -> float:
        """Calculate battery health impact score for action."""
        if physics_data and physics_data.get('status') == 'success':
            degradation_model = physics_data.get('degradation_model', {})
            cycle_impact = degradation_model.get('cycle_impact', 0.01)
        else:
            # Default degradation impact
            cycle_impact = 0.01 if action in ['BUY', 'SELL'] else 0
        
        if action == 'HOLD':
            return 1.0  # No degradation
        elif action == 'BUY':
            return max(0, 1.0 - cycle_impact * 2)  # Charging is gentler
        else:  # SELL
            return max(0, 1.0 - cycle_impact * 4)  # Discharging is harsher
    
    def _calculate_charge_availability_score(self, action: str, physics_data: Dict[str, Any]) -> float:
        """Calculate charge availability score for action."""
        # Mock SOC - in real implementation, get from battery state
        current_soc = 60.0  # percent
        
        if physics_data and physics_data.get('status') == 'success':
            simulation_results = physics_data.get('simulation_results', {})
            current_soc = simulation_results.get('current_soc', 60.0)
        
        if action == 'BUY':
            # Higher score if SOC is low (need to charge)
            return max(0, (100 - current_soc) / 100)
        elif action == 'SELL':
            # Higher score if SOC is high (can afford to discharge)
            return max(0, (current_soc - 20) / 80)
        else:  # HOLD
            # Neutral score, slightly higher if in good SOC range
            if 40 <= current_soc <= 80:
                return 0.7
            else:
                return 0.4
    
    def _calculate_confidence_adjustment(self, 
                                       base_action: str,
                                       optimized_action: str,
                                       optimization_score: float,
                                       strategy: str) -> float:
        """Calculate confidence adjustment based on optimization."""
        if base_action == optimized_action:
            # Same action, increase confidence
            return 0.1 + (optimization_score - 0.5) * 0.2
        else:
            # Different action, adjust based on optimization strength
            if optimization_score > 0.8:
                return 0.05  # Strong optimization, slight confidence boost
            elif optimization_score > 0.6:
                return 0.0   # Moderate optimization, no change
            else:
                return -0.1  # Weak optimization, slight confidence reduction
    
    def _generate_optimization_reasoning(self, 
                                       base_action: str,
                                       optimized_action: str,
                                       strategy: str,
                                       action_scores: Dict[str, float],
                                       physics_data: Dict[str, Any]) -> str:
        """Generate human-readable reasoning for optimization decision."""
        strategy_desc = self.OPTIMIZATION_STRATEGIES.get(strategy, {}).get('description', strategy)
        
        if base_action == optimized_action:
            reasoning = f"Base ML prediction aligns with {strategy_desc}. "
        else:
            reasoning = f"Optimized from {base_action} to {optimized_action} for {strategy_desc}. "
        
        # Add score details
        best_score = action_scores.get(optimized_action, 0)
        reasoning += f"Optimization score: {best_score:.2f}. "
        
        # Add specific reasoning based on action
        if optimized_action == 'BUY':
            reasoning += "Charging favored to improve charge availability and utilize low prices."
        elif optimized_action == 'SELL':
            reasoning += "Discharging favored to capture high prices while maintaining battery health."
        else:
            reasoning += "Holding position to preserve battery health and await better conditions."
        
        return reasoning
    
    def _check_constraints(self, 
                          action: str,
                          strategy: str,
                          physics_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if action meets strategy constraints."""
        if strategy not in self.OPTIMIZATION_STRATEGIES:
            return True, ""
        
        constraints = self.OPTIMIZATION_STRATEGIES[strategy]['constraints']
        
        # Mock current state - in real implementation, get from system
        current_soc = 60.0
        daily_cycles = self.daily_cycle_count
        
        if physics_data and physics_data.get('status') == 'success':
            simulation_results = physics_data.get('simulation_results', {})
            current_soc = simulation_results.get('current_soc', 60.0)
        
        # Check SOC constraints
        min_soc = constraints.get('min_soc', 0)
        if action == 'SELL' and current_soc <= min_soc:
            return False, f"SOC too low ({current_soc:.0f}%) for discharge (min: {min_soc}%)."
        
        # Check daily cycle constraints
        max_cycles = constraints.get('max_cycles_per_day', 999)
        if action in ['BUY', 'SELL'] and daily_cycles >= max_cycles:
            return False, f"Daily cycle limit reached ({daily_cycles}/{max_cycles})."
        
        return True, ""
    
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
            
        if strategy in self.OPTIMIZATION_STRATEGIES:
            return {
                'strategy': strategy,
                **self.OPTIMIZATION_STRATEGIES[strategy],
                'current_cycles': self.daily_cycle_count,
                'available_strategies': list(self.OPTIMIZATION_STRATEGIES.keys())
            }
        else:
            return {
                'strategy': 'unknown',
                'error': f'Strategy {strategy} not found',
                'available_strategies': list(self.OPTIMIZATION_STRATEGIES.keys())
            }
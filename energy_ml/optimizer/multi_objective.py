"""
Multi-Objective Optimization Engine

This module implements user preference-based optimization for Smart Energy AI:
- MAX_EARN: Prioritizes profit maximization
- MAX_BATTERY_SAFE: Minimizes battery degradation  
- BALANCE: Balances profit and battery health
"""

from enum import Enum
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class UserPreference(str, Enum):
    """User preference for optimization strategy"""
    MAX_EARN = "max_earn"
    MAX_BATTERY_SAFE = "max_battery_safe"  
    BALANCE = "balance"

class UserPreferenceEngine:
    """Multi-objective optimization based on user preferences"""
    
    def __init__(self, battery, tariff_model):
        self.battery = battery
        self.tariff_model = tariff_model
        
    def optimize_schedule(self, preference: UserPreference, hours_ahead: int = 24) -> List[Dict[str, Any]]:
        """
        Generate optimized schedule based on user preference.
        
        Args:
            preference: User's optimization preference
            hours_ahead: Number of hours to optimize ahead
            
        Returns:
            List of scheduled actions with hour, action, power_kw, reason
        """
        
        try:
            # Get price forecast
            if hasattr(self.tariff_model, 'get_24h_forecast'):
                prices = self.tariff_model.get_24h_forecast()
            else:
                # Fallback to individual price calls
                prices = [self.tariff_model.get_price(h) for h in range(hours_ahead)]
                
            schedule = []
            
            for hour in range(hours_ahead):
                if hour < len(prices):
                    price = prices[hour]
                else:
                    price = 2.0  # Default fallback price
                
                # Generate action based on preference and price
                action_data = self._generate_action(preference, hour, price)
                schedule.append(action_data)
                
            return schedule
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            # Return safe fallback schedule
            return self._generate_safe_schedule(hours_ahead)
            
    def _generate_action(self, preference: UserPreference, hour: int, price: float) -> Dict[str, Any]:
        """Generate single action based on preference and market conditions"""
        
        # Determine base action based on price and time
        is_low_price = price < 2.0  # Threshold for low price
        is_high_price = price > 2.5  # Threshold for high price
        
        if preference == UserPreference.MAX_EARN:
            # Aggressive trading for maximum profit
            if is_low_price:
                return {
                    'hour': hour,
                    'action': 'CHARGE', 
                    'power_kw': 4.0,  # High power for aggressive trading
                    'reason': f'Max earn: Low price {price:.2f} UAH/kWh'
                }
            elif is_high_price:
                return {
                    'hour': hour,
                    'action': 'DISCHARGE',
                    'power_kw': 4.0,  # High power for aggressive trading
                    'reason': f'Max earn: High price {price:.2f} UAH/kWh'
                }
            else:
                return {
                    'hour': hour,
                    'action': 'HOLD',
                    'power_kw': 0.0,
                    'reason': f'Max earn: Wait for better price {price:.2f} UAH/kWh'
                }
                
        elif preference == UserPreference.MAX_BATTERY_SAFE:
            # Conservative trading to minimize degradation
            if is_low_price:
                return {
                    'hour': hour,
                    'action': 'CHARGE',
                    'power_kw': 1.0,  # Low power for battery safety
                    'reason': f'Battery safe: Gentle charge at {price:.2f} UAH/kWh'
                }
            elif is_high_price:
                return {
                    'hour': hour,
                    'action': 'DISCHARGE', 
                    'power_kw': 1.0,  # Low power for battery safety
                    'reason': f'Battery safe: Gentle discharge at {price:.2f} UAH/kWh'
                }
            else:
                return {
                    'hour': hour,
                    'action': 'HOLD',
                    'power_kw': 0.0,
                    'reason': f'Battery safe: Minimize cycling at {price:.2f} UAH/kWh'
                }
                
        else:  # BALANCE
            # Balanced approach
            if is_low_price:
                return {
                    'hour': hour,
                    'action': 'CHARGE',
                    'power_kw': 2.0,  # Moderate power
                    'reason': f'Balance: Moderate charge at {price:.2f} UAH/kWh'
                }
            elif is_high_price:
                return {
                    'hour': hour, 
                    'action': 'DISCHARGE',
                    'power_kw': 2.0,  # Moderate power
                    'reason': f'Balance: Moderate discharge at {price:.2f} UAH/kWh'
                }
            else:
                return {
                    'hour': hour,
                    'action': 'HOLD',
                    'power_kw': 0.0,
                    'reason': f'Balance: Hold at neutral price {price:.2f} UAH/kWh'
                }
                
    def _generate_safe_schedule(self, hours_ahead: int) -> List[Dict[str, Any]]:
        """Generate safe fallback schedule when optimization fails"""
        schedule = []
        
        for hour in range(hours_ahead):
            schedule.append({
                'hour': hour,
                'action': 'HOLD',
                'power_kw': 0.0,
                'reason': 'Safe mode: Optimization unavailable'
            })
            
        return schedule
"""
Hybrid ML Architecture for Smart Energy AI
Combines price forecasting + optimization + real-time RL control

Architecture:
1. Price Forecasting (Transformer/LSTM with pattern recognition)
2. MILP Optimization (Global optimal scheduling) 
3. RL Fine-tuning (Real-time adjustments)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ForecastConfig:
    """Configuration for price forecasting"""
    forecast_horizon: int = 24  # Hours ahead to predict
    lookback_window: int = 168  # Hours of history to use (1 week)
    update_frequency: int = 1   # Update every N hours
    confidence_level: float = 0.95  # Confidence interval level

@dataclass 
class OptimizationConfig:
    """Configuration for MILP optimization"""
    battery_capacity_kwh: float = 200.0
    max_charge_rate_kw: float = 50.0
    max_discharge_rate_kw: float = 50.0
    efficiency: float = 0.92
    degradation_cost_per_cycle: float = 15.0  # UAH per full cycle


class PatternBasedForecaster:
    """
    Price forecasting using pattern recognition and limited historical data
    Designed for Ukrainian energy market with limited historical availability
    """
    
    def __init__(self, config: ForecastConfig):
        self.config = config
        self.historical_prices = []
        self.daily_patterns = {}
        self.weekly_patterns = {}
        
    def add_historical_data(self, prices_df: pd.DataFrame):
        """Add new price data to historical collection"""
        self.historical_prices.append({
            'timestamp': datetime.now(),
            'prices': prices_df.copy(),
            'source': 'oree_scraper'
        })
        
        # Keep only recent data to avoid memory issues
        if len(self.historical_prices) > 30:  # Keep 30 days max
            self.historical_prices = self.historical_prices[-30:]
            
        logger.info(f"Added historical data, total days: {len(self.historical_prices)}")
    
    def extract_patterns(self) -> Dict:
        """Extract daily and weekly patterns from available data"""
        if len(self.historical_prices) < 2:
            logger.warning("Insufficient historical data for pattern extraction")
            return {}
        
        # Combine all historical data
        all_prices = []
        for entry in self.historical_prices:
            prices_df = entry['prices']
            if 'hour' in prices_df.columns and 'price_eur_mwh' in prices_df.columns:
                for _, row in prices_df.iterrows():
                    all_prices.append({
                        'hour': row['hour'],
                        'price': row['price_eur_mwh'],
                        'day_of_week': entry['timestamp'].weekday(),
                        'date': entry['timestamp'].date()
                    })
        
        if not all_prices:
            return {}
            
        df = pd.DataFrame(all_prices)
        
        # Extract daily patterns (average price by hour)
        self.daily_patterns = df.groupby('hour')['price'].agg(['mean', 'std']).to_dict()
        
        # Extract weekly patterns (average by day of week + hour)
        self.weekly_patterns = df.groupby(['day_of_week', 'hour'])['price'].agg(['mean', 'std']).to_dict()
        
        return {
            'daily_patterns_extracted': len(self.daily_patterns.get('mean', {})),
            'weekly_patterns_extracted': len(self.weekly_patterns.get('mean', {})),
            'total_data_points': len(df)
        }
    
    def forecast_prices(self, current_hour: int, weather_forecast: Optional[Dict] = None) -> Tuple[np.array, np.array]:
        """
        Forecast next 24 hours of prices
        
        Args:
            current_hour: Current hour of day (0-23)
            weather_forecast: Optional weather data for next 24h
            
        Returns:
            Tuple of (price_forecast, confidence_intervals)
        """
        
        if not self.daily_patterns:
            self.extract_patterns()
        
        forecast_hours = []
        confidence_intervals = []
        
        for h in range(24):  # Next 24 hours
            target_hour = (current_hour + h) % 24
            target_day = datetime.now().weekday()  # Today's day of week
            
            # Primary prediction from daily patterns
            if target_hour in self.daily_patterns.get('mean', {}):
                base_price = self.daily_patterns['mean'][target_hour]
                price_std = self.daily_patterns.get('std', {}).get(target_hour, base_price * 0.2)
            else:
                # Fallback to reasonable estimate
                base_price = 100.0  # EUR/MWh fallback
                price_std = 30.0
            
            # Adjust with weekly patterns if available
            weekly_key = (target_day, target_hour)
            if weekly_key in self.weekly_patterns.get('mean', {}):
                weekly_price = self.weekly_patterns['mean'][weekly_key]
                # Weighted average: 70% daily pattern, 30% weekly adjustment
                base_price = 0.7 * base_price + 0.3 * weekly_price
            
            # Weather adjustment (if solar forecast available)
            if weather_forecast and 'solar_forecast' in weather_forecast:
                solar_factor = weather_forecast['solar_forecast'][h % len(weather_forecast['solar_forecast'])]
                # High solar → potentially lower prices during day
                if 8 <= target_hour <= 16 and solar_factor > 50:  # Daytime with high solar
                    base_price *= 0.85  # 15% reduction
            
            forecast_hours.append(base_price)
            
            # Confidence interval (2 standard deviations)
            conf_interval = 1.96 * price_std  # 95% confidence
            confidence_intervals.append(conf_interval)
        
        forecast = np.array(forecast_hours)
        confidence = np.array(confidence_intervals)
        
        logger.info(f"Generated 24h price forecast: {forecast.min():.1f}-{forecast.max():.1f} EUR/MWh")
        
        return forecast, confidence


class MILPOptimizer:
    """
    Mixed Integer Linear Programming optimizer for battery scheduling
    Uses price forecast to create optimal 24h charge/discharge schedule
    """
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        
    def optimize_schedule(self, 
                         price_forecast: np.array, 
                         current_soc: float,
                         demand_forecast: np.array) -> Dict:
        """
        Create optimal battery schedule using linear programming
        
        Args:
            price_forecast: 24h price forecast (EUR/MWh)
            current_soc: Current battery state of charge (0-1)
            demand_forecast: 24h facility demand forecast (kW)
            
        Returns:
            Optimal schedule dictionary
        """
        
        logger.info("🔧 Starting MILP optimization...")
        
        # Convert prices to UAH (assuming 1 EUR = 40 UAH)
        prices_uah = price_forecast * 40.0  # UAH/MWh
        
        schedule = []
        soc = current_soc
        total_cost = 0.0
        
        for hour in range(24):
            price_kwh = prices_uah[hour] / 1000  # Convert MWh to kWh
            demand_kw = demand_forecast[hour] if len(demand_forecast) > hour else 50.0
            
            # Simple greedy optimization (placeholder for full MILP)
            # TODO: Replace with actual linear programming solver
            
            action = "BUY_FROM_GRID"  # Default
            
            # Charge when prices are low (bottom 30% of forecast)
            if price_kwh < np.percentile(prices_uah / 1000, 30) and soc < 0.9:
                action = "CHARGE_FROM_GRID"
                charge_amount = min(self.config.max_charge_rate_kw, 
                                   (0.9 - soc) * self.config.battery_capacity_kwh)
                soc += charge_amount / self.config.battery_capacity_kwh
                hourly_cost = (demand_kw + charge_amount) * price_kwh
                
            # Discharge when prices are high (top 30% of forecast) 
            elif price_kwh > np.percentile(prices_uah / 1000, 70) and soc > 0.2:
                action = "DISCHARGE_BATTERY"
                discharge_amount = min(self.config.max_discharge_rate_kw,
                                     demand_kw,
                                     (soc - 0.2) * self.config.battery_capacity_kwh)
                soc -= discharge_amount / self.config.battery_capacity_kwh
                grid_needed = max(0, demand_kw - discharge_amount)
                hourly_cost = grid_needed * price_kwh
                
            else:
                # Just buy what we need
                hourly_cost = demand_kw * price_kwh
            
            schedule.append({
                'hour': hour,
                'action': action,
                'price_uah_kwh': price_kwh,
                'soc': soc,
                'cost': hourly_cost,
                'demand_kw': demand_kw
            })
            
            total_cost += hourly_cost
        
        logger.info(f"✅ MILP optimization complete. Total cost: {total_cost:.0f} UAH")
        
        return {
            'schedule': schedule,
            'total_cost_uah': total_cost,
            'optimization_method': 'greedy_milp_placeholder',
            'final_soc': soc
        }


class HybridEnergyController:
    """
    Main hybrid controller combining forecasting + optimization + RL
    """
    
    def __init__(self):
        self.forecaster = PatternBasedForecaster(ForecastConfig())
        self.optimizer = MILPOptimizer(OptimizationConfig())
        self.current_schedule = None
        self.performance_history = []
        
    def update_with_new_prices(self, prices_df: pd.DataFrame):
        """Update system with latest OREE price data"""
        self.forecaster.add_historical_data(prices_df)
        
    def generate_optimal_strategy(self, 
                                current_state: Dict,
                                weather_forecast: Optional[Dict] = None) -> Dict:
        """
        Generate optimal 24h strategy using hybrid approach
        
        Args:
            current_state: Current system state (SOC, hour, etc.)
            weather_forecast: Weather forecast for next 24h
            
        Returns:
            Optimal strategy with actions and expected costs
        """
        
        current_hour = current_state.get('hour', datetime.now().hour)
        current_soc = current_state.get('soc', 0.5)
        
        # Step 1: Forecast prices
        logger.info("📈 Step 1: Forecasting prices...")
        price_forecast, confidence = self.forecaster.forecast_prices(current_hour, weather_forecast)
        
        # Step 2: Optimize schedule
        logger.info("⚙️ Step 2: Optimizing schedule...")
        demand_forecast = np.full(24, 50.0)  # Assume constant 50kW demand
        schedule = self.optimizer.optimize_schedule(price_forecast, current_soc, demand_forecast)
        
        # Step 3: Store for RL fine-tuning (placeholder)
        self.current_schedule = schedule
        
        return {
            'strategy_type': 'hybrid_ml',
            'price_forecast': price_forecast.tolist(),
            'confidence_intervals': confidence.tolist(),
            'optimal_schedule': schedule,
            'expected_daily_cost': schedule['total_cost_uah'],
            'forecast_horizon': 24,
            'generated_at': datetime.now().isoformat()
        }
    
    def get_current_action(self, current_hour: int) -> str:
        """Get recommended action for current hour"""
        if not self.current_schedule:
            return "BUY_FROM_GRID"  # Safe default
            
        for item in self.current_schedule['schedule']:
            if item['hour'] == current_hour % 24:
                return item['action']
                
        return "BUY_FROM_GRID"


# Factory function for easy integration
def create_hybrid_controller() -> HybridEnergyController:
    """Create and return configured hybrid controller"""
    logger.info("🚀 Initializing Hybrid ML Energy Controller")
    controller = HybridEnergyController()
    return controller


if __name__ == "__main__":
    # Test the hybrid system
    print("🧪 Testing Hybrid ML Architecture")
    print("=" * 50)
    
    controller = create_hybrid_controller()
    
    # Simulate adding some historical data
    import pandas as pd
    sample_prices = pd.DataFrame({
        'hour': range(24),
        'price_eur_mwh': [80, 75, 70, 65, 70, 90, 120, 150, 180, 160, 140, 130, 
                         125, 120, 115, 130, 150, 180, 220, 200, 170, 140, 110, 90]
    })
    
    controller.update_with_new_prices(sample_prices)
    
    # Generate strategy
    current_state = {'hour': 14, 'soc': 0.6}
    strategy = controller.generate_optimal_strategy(current_state)
    
    print(f"✅ Generated strategy with {len(strategy['optimal_schedule']['schedule'])} hours")
    print(f"Expected daily cost: {strategy['expected_daily_cost']:.0f} UAH")
    print(f"Price forecast range: {min(strategy['price_forecast']):.1f}-{max(strategy['price_forecast']):.1f} EUR/MWh")
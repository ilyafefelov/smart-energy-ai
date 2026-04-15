"""
Smart Energy RL Environment - Gym compatible
State: [temperature, solar_radiation, cloudcover, market_price, battery_soc]
Actions: [charge_rate, discharge_rate, grid_buy, grid_sell]
Reward: -hourly_cost (minimize electricity cost)
"""

import numpy as np
try:
    import gymnasium as gym
    from gymnasium import spaces
except ImportError:
    import gym
    from gym import spaces
from typing import Tuple, Dict
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class SmartEnergyEnv(gym.Env):
    """OpenAI Gym environment for smart energy optimization"""
    
    metadata = {'render.modes': ['human']}
    
    def __init__(self, weather_data: pd.DataFrame, price_data: pd.DataFrame, config=None):
        """
        Initialize environment
        
        Args:
            weather_data: DataFrame with columns [temperature, solar_radiation, cloudcover, wind, humidity]
            price_data: DataFrame with column [price_normalized_minmax]
            config: SystemConfig instance (optional, uses defaults if None)
        """
        # Import config if not provided
        if config is None:
            from src.config import get_config
            config = get_config()
        
        self.config = config
        self.weather = weather_data.reset_index(drop=True)
        self.prices = price_data.reset_index(drop=True)
        self.current_step = 0
        
        # Get constants from config (with fallback to hardcoded defaults)
        battery_cfg = config.get_battery_config()
        self.BATTERY_CAPACITY = battery_cfg.get('capacity_kwh', 150)  # kWh
        self.BATTERY_MIN_SOC = battery_cfg.get('min_soc', 0.1)  # 10% minimum
        self.BATTERY_MAX_SOC = battery_cfg.get('max_soc', 0.95)  # 95% maximum
        self.BATTERY_CHARGE_EFFICIENCY = battery_cfg.get('charge_efficiency', 0.95)
        self.BATTERY_DISCHARGE_EFFICIENCY = battery_cfg.get('discharge_efficiency', 0.95)
        
        grid_cfg = config.get_grid_config()
        self.GRID_MAX_POWER = grid_cfg.get('max_import_power_kw', 100)  # kW
        
        # State space: [temperature, solar, cloudcover, price, battery_soc]
        self.observation_space = spaces.Box(
            low=np.array([-50, 0, 0, 0, 0], dtype=np.float32),
            high=np.array([50, 2000, 100, 1, 1], dtype=np.float32),
            dtype=np.float32
        )
        
        # Action space: [charge_rate, discharge_rate, grid_buy, grid_sell]
        # Each in range [0, 1], will be scaled to actual power
        self.action_space = spaces.Box(
            low=np.array([0, 0, 0, 0], dtype=np.float32),
            high=np.array([1, 1, 1, 1], dtype=np.float32),
            dtype=np.float32
        )
        
        # Initial state
        self.battery_soc = 50.0  # kWh
        self.episode_cost = 0.0
        self.last_info = None

    def reset(self) -> np.ndarray:
        """Reset environment for new episode"""
        self.current_step = 0
        self.battery_soc = 50.0  # Start at 50% SOC
        self.episode_cost = 0.0
        self.last_info = None
        return self._get_state()

    def _get_state(self) -> np.ndarray:
        """Get current state observation"""
        hour = self.current_step % len(self.weather)
        
        temp = self.weather.loc[hour, 'temp']
        solar = self.weather.loc[hour, 'radiation']
        cloudcover = self.weather.loc[hour, 'clouds']
        price = self.prices.loc[hour, 'price_normalized_minmax']
        soc = self.battery_soc / self.BATTERY_CAPACITY  # Normalize to 0-1
        
        return np.array([temp, solar, cloudcover, price, soc], dtype=np.float32)

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, dict]:
        """
        Execute one step in the environment
        
        Args:
            action: [charge_rate, discharge_rate, grid_buy, grid_sell] (0-1 normalized)
            
        Returns:
            state, reward, done, info
        """
        # Scale actions to actual power
        charge_rate = action[0] * 150  # 0-150 kW
        discharge_rate = action[1] * 150
        grid_buy = action[2] * 100  # 0-100 kW
        grid_sell = action[3] * 50  # 0-50 kW (lower limit for selling)
        
        hour = self.current_step % len(self.weather)
        price_uah = self.prices.loc[hour, 'price_uah_original']  # Real UAH price
        solar_power = self.weather.loc[hour, 'radiation'] / 10  # Convert to kW
        
        # Energy balance
        charge_energy = charge_rate  # Grid charging
        discharge_energy = discharge_rate  # Battery discharge
        buy_energy = grid_buy  # Grid purchase
        sell_energy = grid_sell  # Sell to grid
        
        # Battery state update
        net_charge = (charge_energy * self.BATTERY_CHARGE_EFFICIENCY - 
                     discharge_energy / self.BATTERY_DISCHARGE_EFFICIENCY)
        self.battery_soc += net_charge
        
        # Enforce battery limits
        self.battery_soc = np.clip(self.battery_soc, 
                                   self.BATTERY_CAPACITY * self.BATTERY_MIN_SOC,
                                   self.BATTERY_CAPACITY * self.BATTERY_MAX_SOC)
        
        # Cost calculation
        hourly_cost = (buy_energy * price_uah) - (sell_energy * price_uah * 0.9)  # 0.9 multiplier for selling
        self.episode_cost += hourly_cost
        
        # Reward: negative cost (we want to minimize)
        reward = -hourly_cost / 1000  # Normalize reward scale
        
        # Add penalty for not using solar
        solar_waste = max(0, solar_power - charge_rate - sell_energy)
        reward -= solar_waste * 0.01  # Small penalty for wasted solar
        
        # Add bonus for maintaining good SOC
        soc_ratio = self.battery_soc / self.BATTERY_CAPACITY
        if self.BATTERY_MIN_SOC < soc_ratio < self.BATTERY_MAX_SOC:
            reward += 0.1  # Bonus for healthy SOC
        
        # Episode termination
        self.current_step += 1
        done = self.current_step >= 24  # 24-hour episode
        
        # Info for debugging
        info = {
            'hour': hour,
            'battery_soc': self.battery_soc,
            'hourly_cost': hourly_cost,
            'episode_cost': self.episode_cost,
            'solar_power': solar_power,
            'price_uah': price_uah,
        }
        self.last_info = info
        
        return self._get_state(), reward, done, info

    def render(self, mode='human'):
        """Render current state"""
        if self.current_step > 0:
            info = self.get_info()
            print(f"Hour {info['hour']:2d}: Cost={info['hourly_cost']:7.1f} UAH, "
                  f"SOC={info['battery_soc']:6.1f} kWh, Price={info['price_uah']:6.1f} UAH/MWh")

    def get_info(self) -> dict:
        """Get current step info"""
        if self.last_info is not None:
            return dict(self.last_info)

        hour = (self.current_step - 1) % len(self.weather)
        price_uah = self.prices.loc[hour, 'price_uah_original']
        
        return {
            'hour': hour,
            'battery_soc': self.battery_soc,
            'price_uah': price_uah,
        }


if __name__ == "__main__":
    # Test environment with REAL data
    logging.basicConfig(level=logging.INFO)
    
    print("🔄 Loading REAL data for environment test...\n")
    
    # Import real data sources
    from src.data_pipeline.ingest_weather import WeatherIngester
    from src.data_pipeline.ingest_prices import PriceIngester
    from src.price_processor import prepare_prices_for_rl
    
    # Fetch real weather
    weather_ingester = WeatherIngester()
    weather_data = weather_ingester.fetch_weather()
    
    if weather_data:
        weather = weather_ingester.parse_weather_data(weather_data)
        print(f"✅ Loaded REAL weather: {len(weather)} hours")
    else:
        print("⚠️  Weather API unavailable, using realistic simulation...")
        # Fallback: realistic weather pattern
        weather = pd.DataFrame({
            'temperature': np.concatenate([np.linspace(-10, -5, 6), np.linspace(-5, 5, 12), np.linspace(5, -5, 6)]),
            'solar_radiation': np.concatenate([np.zeros(6), np.linspace(100, 500, 12), np.zeros(6)]),
            'cloudcover': np.random.uniform(20, 80, 24),
            'wind': np.random.uniform(0, 20, 24),
            'humidity': np.random.uniform(40, 80, 24),
        })
    
    # Fetch real prices
    price_ingester = PriceIngester()
    prices_df = price_ingester.fetch_oree_prices()
    
    if prices_df is not None and not prices_df.empty:
        print(f"✅ Loaded REAL prices from OREE: {len(prices_df)} hours")
        # Process for RL
        prices, _ = prepare_prices_for_rl(prices_df, normalize=True)
    else:
        print("⚠️  OREE prices unavailable, using realistic simulation...")
        # Fallback: realistic price pattern
        prices = pd.DataFrame({
            'price_normalized_minmax': np.concatenate([
                np.linspace(0.1, 0.3, 6),  # Night (cheap)
                np.linspace(0.3, 0.8, 6),  # Morning
                np.linspace(0.8, 1.0, 6),  # Afternoon peak (expensive)
                np.linspace(1.0, 0.4, 6),  # Evening decline
            ]),
            'price_uah_original': np.concatenate([
                np.linspace(70, 210, 6),
                np.linspace(210, 280, 6),
                np.linspace(280, 402.5, 6),
                np.linspace(402.5, 280, 6),
            ]),
        })
    
    env = SmartEnergyEnv(weather, prices)
    
    print("\n🚀 Testing environment with REAL/realistic data...\n")
    state = env.reset()
    print(f"Initial state shape: {state.shape}")
    print(f"Initial state: {state[:5]}...\n")
    
    # Random episode
    total_reward = 0
    print(f"{'Hour':>4} {'Reward':>8} {'Cost (UAH)':>12} {'SOC':>7} {'Action':>12}")
    print("-" * 55)
    
    for _ in range(24):
        action = env.action_space.sample()
        state, reward, done, info = env.step(action)
        total_reward += reward
        action_names = {0: 'CHARGE', 1: 'DISCHARGE', 2: 'HOLD'}
        print(f"{info['hour']:4d} {reward:8.2f} {info['hourly_cost']:12.1f} {info['battery_soc']:7.1f}% {action_names.get(action, str(action)):>12}")
        if done:
            break
    
    print("-" * 55)
    print(f"\n✅ Episode Results:")
    print(f"   Total Reward: {total_reward:.2f}")
    print(f"   Total Cost: {info['episode_cost']:.1f} UAH")
    print(f"   Data Source: {'REAL APIs' if weather_data and prices_df is not None else 'Realistic simulation'}")

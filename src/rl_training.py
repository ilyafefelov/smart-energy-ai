"""
RL Agent Training - PPO (Proximal Policy Optimization)
Uses Stable-Baselines3 to train on 7-day sample data
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime

# Try Stable-Baselines3, fallback to simpler training
try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv
    STABLE_BASELINES_AVAILABLE = True
except ImportError:
    STABLE_BASELINES_AVAILABLE = False

from src.rl_environment import SmartEnergyEnv

logger = logging.getLogger(__name__)


class RLTrainer:
    """Train RL agent for smart energy optimization"""
    
    def __init__(self, weather_df: pd.DataFrame, prices_df: pd.DataFrame,
                 model_path: str = "models/ppo_agent.zip"):
        """
        Initialize trainer
        
        Args:
            weather_df: Weather data
            prices_df: Price data (with price_normalized_minmax and price_uah_original)
            model_path: Path to save trained model
        """
        self.weather = weather_df
        self.prices = prices_df
        self.model_path = Path(model_path)
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.env = SmartEnergyEnv(weather_df, prices_df)
        self.model = None
        self.training_log = []

    def train_ppo(self, timesteps: int = 10000, learning_rate: float = 3e-4) -> dict:
        """
        Train PPO agent
        
        Args:
            timesteps: Total training timesteps
            learning_rate: PPO learning rate
            
        Returns:
            Training results dict
        """
        if not STABLE_BASELINES_AVAILABLE:
            logger.warning("Stable-Baselines3 not available, running simplified training demo")
            return self._train_simple()
        
        logger.info("Starting PPO training...")
        logger.info(f"Timesteps: {timesteps}, Learning rate: {learning_rate}")
        
        # Create vectorized environment
        vec_env = DummyVecEnv([lambda: self.env])
        
        # Create PPO agent
        self.model = PPO(
            "MlpPolicy",
            vec_env,
            learning_rate=learning_rate,
            n_steps=2048,
            batch_size=64,
            n_epochs=20,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            verbose=1,
            tensorboard_log="./logs/",
        )
        
        # Train
        start_time = datetime.now()
        self.model.learn(total_timesteps=timesteps)
        training_time = datetime.now() - start_time
        
        # Save model
        self.model.save(str(self.model_path))
        logger.info(f"✓ Model saved to {self.model_path}")
        
        return {
            'status': 'completed',
            'timesteps': timesteps,
            'training_time': str(training_time),
            'model_path': str(self.model_path),
        }

    def _train_simple(self) -> dict:
        """Simplified training demo (without Stable-Baselines3)"""
        logger.info("Running simplified training (no SB3)")
        
        episodes = 10
        results = {
            'episodes': [],
            'episode_costs': [],
            'episode_rewards': [],
        }
        
        for ep in range(episodes):
            state = self.env.reset()
            episode_reward = 0
            episode_cost = 0
            
            for step in range(24):
                # Simple random policy with bias towards good actions
                # In production, this would be the trained agent
                action = self.env.action_space.sample()
                
                # Simple heuristic: charge when price low, discharge when price high
                if step < 6 or step > 20:  # Night (cheap)
                    action[0] = 0.8  # Charge heavily
                    action[1] = 0.1
                elif step > 16:  # Evening peak (expensive)
                    action[0] = 0.1
                    action[1] = 0.8  # Discharge heavily
                
                state, reward, done, info = self.env.step(action)
                episode_reward += reward
                episode_cost = info['episode_cost']
            
            results['episodes'].append(ep)
            results['episode_costs'].append(episode_cost)
            results['episode_rewards'].append(episode_reward)
            
            logger.info(f"Episode {ep+1}: Cost={episode_cost:.1f} UAH, Reward={episode_reward:.2f}")
        
        # Calculate improvement
        baseline_cost = 200000  # Typical unoptimized cost
        avg_cost = np.mean(results['episode_costs'])
        improvement = (baseline_cost - avg_cost) / baseline_cost * 100
        
        return {
            'status': 'completed_simple',
            'episodes': episodes,
            'avg_cost': float(avg_cost),
            'baseline_cost': baseline_cost,
            'improvement_pct': float(improvement),
        }

    def evaluate(self, episodes: int = 5) -> dict:
        """
        Evaluate trained model
        
        Args:
            episodes: Number of episodes to evaluate
            
        Returns:
            Evaluation results
        """
        if self.model is None:
            # Load if not trained yet
            try:
                self.model = PPO.load(str(self.model_path))
            except Exception as e:
                logger.warning(f"Could not load model: {e}")
                return {'status': 'model_not_found'}
        
        results = {
            'episodes': [],
            'episode_costs': [],
            'episode_rewards': [],
        }
        
        for ep in range(episodes):
            state = self.env.reset()
            episode_reward = 0
            episode_cost = 0
            
            for step in range(24):
                action, _ = self.model.predict(state, deterministic=True)
                state, reward, done, info = self.env.step(action)
                episode_reward += reward
                episode_cost = info['episode_cost']
                
                if done:
                    break
            
            results['episodes'].append(ep)
            results['episode_costs'].append(episode_cost)
            results['episode_rewards'].append(episode_reward)
            
            logger.info(f"Eval Episode {ep+1}: Cost={episode_cost:.1f} UAH, Reward={episode_reward:.2f}")
        
        avg_cost = np.mean(results['episode_costs'])
        avg_reward = np.mean(results['episode_rewards'])
        
        return {
            'status': 'completed',
            'episodes': episodes,
            'avg_cost': float(avg_cost),
            'avg_reward': float(avg_reward),
            'min_cost': float(min(results['episode_costs'])),
            'max_cost': float(max(results['episode_costs'])),
        }


def train_rl_agent(train_days: int = 7) -> dict:
    """
    Main entry point for RL training
    
    Args:
        train_days: Number of days of data to use for training
        
    Returns:
        Training results summary
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Loading training data...")
    
    # Load sample data
    weather_df = pd.read_csv('data/raw/weather_forecast.csv')
    prices_df = pd.read_csv('data/processed/opt_normal.csv')  # Contains prices
    
    # Prepare price data
    from src.price_processor import PriceProcessor
    
    processor = PriceProcessor(
        prices_df['Price'],  # Assuming column name is 'Price'
        normalize=True,
        add_noise=False
    )
    
    # Extend data for multiple days
    weather_extended = pd.concat([weather_df] * train_days, ignore_index=True)
    
    # Process prices
    processed_prices = processor.process_for_training()
    prices_extended = pd.concat([processed_prices] * train_days, ignore_index=True)
    
    logger.info(f"Training data: {len(weather_extended)} hours ({train_days} days)")
    
    # Train agent
    trainer = RLTrainer(weather_extended, prices_extended)
    
    logger.info("Starting training...")
    train_results = trainer.train_ppo(timesteps=2400)  # 100 episodes × 24 hours
    
    # Evaluate
    logger.info("Evaluating trained model...")
    eval_results = trainer.evaluate(episodes=3)
    
    return {
        'training': train_results,
        'evaluation': eval_results,
        'timestamp': datetime.now().isoformat(),
    }


if __name__ == "__main__":
    results = train_rl_agent(train_days=7)
    
    print("\n=== TRAINING RESULTS ===")
    print(f"Status: {results['training']['status']}")
    print(f"Timesteps: {results['training'].get('timesteps', 'N/A')}")
    
    if 'evaluation' in results:
        print("\n=== EVALUATION RESULTS ===")
        eval_res = results['evaluation']
        if eval_res.get('status') == 'completed':
            print(f"Average Cost: {eval_res['avg_cost']:.1f} UAH")
            print(f"Average Reward: {eval_res['avg_reward']:.2f}")
            print(f"Min Cost: {eval_res['min_cost']:.1f} UAH")
            print(f"Max Cost: {eval_res['max_cost']:.1f} UAH")

"""
Configurable System Constants
All hardware specs and tuning parameters in one place
Can be modified at runtime via Streamlit UI
"""

import json
import os
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class SystemConfig:
    """Manages all system constants and configuration"""
    
    def __init__(self, config_file: str = "config/system_config.json"):
        """
        Initialize system configuration
        
        Args:
            config_file: Path to JSON config file
        """
        self.config_file = config_file
        self.defaults = {
            # Battery specifications
            "battery": {
                "capacity_kwh": 150,
                "min_soc_percent": 10,
                "max_soc_percent": 95,
                "charge_efficiency": 0.95,
                "discharge_efficiency": 0.95,
                "min_soc": 0.1,
                "max_soc": 0.95,
            },
            
            # Solar specifications
            "solar": {
                "installed_capacity_kw": 20,
                "panel_efficiency": 0.20,
                "inverter_efficiency": 0.95,
            },
            
            # Grid specifications
            "grid": {
                "max_import_power_kw": 100,
                "max_export_power_kw": 50,
            },
            
            # Diesel generator (backup)
            "diesel_generator": {
                "capacity_kw": 50,
                "fuel_cost_eur_per_kwh": 0.25,
            },
            
            # RL training parameters
            "training": {
                "learning_rate": 0.0003,
                "gamma": 0.99,
                "batch_size": 64,
                "episodes": 100,
                "timesteps_per_episode": 24,
            },
            
            # Optimizer thresholds
            "optimizer": {
                "cheap_price_threshold_eur": 3.0,
                "expensive_price_threshold_eur": 8.0,
                "low_battery_threshold": 0.2,
                "high_battery_threshold": 0.9,
            }
        }
        
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load config from file or use defaults"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                logger.info(f"✅ Loaded config from {self.config_file}")
                return loaded
            except Exception as e:
                logger.warning(f"⚠️  Failed to load config: {e}, using defaults")
                return self.defaults.copy()
        else:
            logger.info(f"ℹ️  No config file found, using defaults...")
            return self.defaults.copy()
    
    def save_config(self):
        """Save current config to file"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        logger.info(f"💾 Saved config to {self.config_file}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot notation (e.g., 'battery.capacity_kwh')"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value
    
    def set(self, key: str, value: Any):
        """Set config value by dot notation"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        logger.info(f"✏️  Updated {key} = {value}")
    
    def get_battery_config(self) -> Dict[str, float]:
        """Get all battery parameters"""
        return self.config.get('battery', {})
    
    def get_solar_config(self) -> Dict[str, float]:
        """Get all solar parameters"""
        return self.config.get('solar', {})
    
    def get_grid_config(self) -> Dict[str, float]:
        """Get all grid parameters"""
        return self.config.get('grid', {})
    
    def get_training_config(self) -> Dict[str, Any]:
        """Get all training parameters"""
        return self.config.get('training', {})
    
    def get_optimizer_config(self) -> Dict[str, float]:
        """Get all optimizer parameters"""
        return self.config.get('optimizer', {})
    
    def reset_to_defaults(self):
        """Reset all config to defaults"""
        self.config = self.defaults.copy()
        self.save_config()
        logger.info("🔄 Reset config to defaults")
    
    def to_dict(self) -> Dict[str, Any]:
        """Get entire config as dictionary"""
        return self.config.copy()
    
    def display_summary(self) -> str:
        """Get formatted summary of all constants"""
        summary = "═" * 60 + "\n"
        summary += "SYSTEM CONFIGURATION\n"
        summary += "═" * 60 + "\n\n"
        
        for section, values in self.config.items():
            summary += f"📋 {section.upper()}\n"
            summary += "─" * 40 + "\n"
            if isinstance(values, dict):
                for key, val in values.items():
                    if isinstance(val, float):
                        summary += f"  {key:.<30} {val:.4f}\n"
                    else:
                        summary += f"  {key:.<30} {val}\n"
            else:
                summary += f"  {values}\n"
            summary += "\n"
        
        summary += "═" * 60
        return summary


# Global instance
_config = None

def get_config() -> SystemConfig:
    """Get or create global config instance"""
    global _config
    if _config is None:
        _config = SystemConfig()
    return _config


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    config = get_config()
    print(config.display_summary())
    
    print("\n💾 Example modifications:")
    print(f"Before: Battery capacity = {config.get('battery.capacity_kwh')} kWh")
    config.set('battery.capacity_kwh', 200)
    print(f"After:  Battery capacity = {config.get('battery.capacity_kwh')} kWh")
    config.save_config()
    print("✅ Changes saved!")

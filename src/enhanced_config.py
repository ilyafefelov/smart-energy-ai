"""
Enhanced System Configuration with User Profiles + Version Tracking
Manages all settings: Battery, Solar, Grid, Training, and User-specific configs
Tracks model versions and training history
"""

import json
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ModelVersion:
    """Model version information and training metrics"""
    version: str  # semver: 1.0.0
    trained_at: str  # ISO timestamp
    episodes: int
    avg_reward: float
    best_reward: float
    training_time_seconds: float
    model_path: str
    metrics: Dict[str, float] = None
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'version': self.version,
            'trained_at': self.trained_at,
            'episodes': self.episodes,
            'avg_reward': self.avg_reward,
            'best_reward': self.best_reward,
            'training_time_seconds': self.training_time_seconds,
            'model_path': self.model_path,
            'metrics': self.metrics or {},
            'notes': self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ModelVersion':
        """Create from dictionary"""
        return cls(
            version=data['version'],
            trained_at=data['trained_at'],
            episodes=data['episodes'],
            avg_reward=data['avg_reward'],
            best_reward=data['best_reward'],
            training_time_seconds=data['training_time_seconds'],
            model_path=data['model_path'],
            metrics=data.get('metrics', {}),
            notes=data.get('notes', ''),
        )
    
    def get_summary(self) -> str:
        """Get formatted summary"""
        return f"""
  Version: {self.version}
  Trained: {self.trained_at}
  Episodes: {self.episodes}
  Avg Reward: {self.avg_reward:.2f}
  Best Reward: {self.best_reward:.2f}
  Training Time: {self.training_time_seconds:.1f}s
  Path: {self.model_path}
"""


@dataclass
class UserProfile:
    """User/Client profile configuration"""
    name: str
    description: str
    created_at: str
    
    # Battery config (kWh, %)
    battery_capacity_kwh: float = 150.0
    battery_min_soc_percent: float = 10.0
    battery_max_soc_percent: float = 95.0
    battery_charge_efficiency: float = 0.95
    battery_discharge_efficiency: float = 0.95
    
    # Solar config (kW)
    solar_capacity_kw: float = 20.0
    solar_panel_efficiency: float = 0.20
    solar_inverter_efficiency: float = 0.95
    
    # Grid config (kW)
    grid_max_import_kw: float = 100.0
    grid_max_export_kw: float = 50.0
    
    # Diesel generator (kW, EUR/kWh)
    diesel_capacity_kw: float = 50.0
    diesel_cost_eur_per_kwh: float = 0.25
    
    # User preferences
    prioritize: str = "cost"  # "cost", "sustainability", "balanced"
    risk_tolerance: str = "medium"  # "low", "medium", "high"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """Create from dictionary"""
        return cls(**data)
    
    def get_summary(self) -> str:
        """Get formatted summary"""
        summary = f"""
╔══════════════════════════════════════════════════════════════╗
║  USER PROFILE: {self.name}
║  {self.description}
╚══════════════════════════════════════════════════════════════╝

📦 BATTERY SYSTEM
  ├─ Capacity: {self.battery_capacity_kwh} kWh
  ├─ SOC Range: {self.battery_min_soc_percent}% - {self.battery_max_soc_percent}%
  ├─ Charge Efficiency: {self.battery_charge_efficiency * 100:.1f}%
  └─ Discharge Efficiency: {self.battery_discharge_efficiency * 100:.1f}%

☀️  SOLAR SYSTEM
  ├─ Capacity: {self.solar_capacity_kw} kW
  ├─ Panel Efficiency: {self.solar_panel_efficiency * 100:.1f}%
  └─ Inverter Efficiency: {self.solar_inverter_efficiency * 100:.1f}%

🔌 GRID CONNECTION
  ├─ Max Import: {self.grid_max_import_kw} kW
  └─ Max Export: {self.grid_max_export_kw} kW

⛽ BACKUP GENERATOR
  ├─ Capacity: {self.diesel_capacity_kw} kW
  └─ Fuel Cost: {self.diesel_cost_eur_per_kwh} EUR/kWh

⚙️  PREFERENCES
  ├─ Prioritize: {self.prioritize.upper()}
  └─ Risk Tolerance: {self.risk_tolerance.upper()}
"""
        return summary


class EnhancedSystemConfig:
    """Enhanced config manager with user profiles and version tracking"""
    
    def __init__(self, config_dir: str = "config"):
        """Initialize config system"""
        self.config_dir = config_dir
        self.profiles_dir = os.path.join(config_dir, "profiles")
        self.training_config_file = os.path.join(config_dir, "training.json")
        self.optimizer_config_file = os.path.join(config_dir, "optimizer.json")
        self.version_history_file = os.path.join(config_dir, "version_history.json")
        self.models_dir = os.path.join(config_dir, "models")
        
        # Ensure directories exist
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.profiles_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Default training config
        self.training_defaults = {
            "learning_rate": 0.0003,
            "gamma": 0.99,
            "batch_size": 64,
            "episodes": 100,
            "timesteps_per_episode": 24,
            "network_layers": [128, 128],
            "epsilon_start": 1.0,
            "epsilon_end": 0.01,
            "epsilon_decay": 0.995,
        }
        
        # Default optimizer config
        self.optimizer_defaults = {
            "cheap_price_threshold_eur": 3.0,
            "expensive_price_threshold_eur": 8.0,
            "low_battery_threshold": 0.2,
            "high_battery_threshold": 0.9,
            "force_charge_at_night": True,
            "force_discharge_at_peak": True,
        }
        
        # Load configs
        self.training_config = self._load_json(self.training_config_file, self.training_defaults)
        self.optimizer_config = self._load_json(self.optimizer_config_file, self.optimizer_defaults)
        
        # Version tracking
        self.version_history = self._load_json(self.version_history_file, {
            'current_version': '1.0.0',
            'versions': {}
        })
        self.current_model_version = self.version_history.get('current_version', '1.0.0')
        
        # Current user profile
        self.current_profile = None
    
    def _load_json(self, filepath: str, defaults: Dict) -> Dict:
        """Load JSON config or use defaults"""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️  Failed to load {filepath}: {e}")
                return defaults.copy()
        return defaults.copy()
    
    def _save_json(self, filepath: str, data: Dict):
        """Save JSON config"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"💾 Saved {filepath}")
    
    # ─── USER PROFILE MANAGEMENT ───
    
    def create_profile(self, **kwargs) -> UserProfile:
        """Create new user profile"""
        profile = UserProfile(
            created_at=datetime.now().isoformat(),
            **kwargs
        )
        self.save_profile(profile)
        return profile
    
    def save_profile(self, profile: UserProfile):
        """Save user profile to file"""
        filepath = os.path.join(self.profiles_dir, f"{profile.name}.json")
        self._save_json(filepath, profile.to_dict())
        logger.info(f"✅ Saved profile: {profile.name}")
    
    def load_profile(self, name: str) -> UserProfile:
        """Load user profile from file"""
        filepath = os.path.join(self.profiles_dir, f"{name}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
            self.current_profile = UserProfile.from_dict(data)
            logger.info(f"✅ Loaded profile: {name}")
            return self.current_profile
        else:
            raise FileNotFoundError(f"Profile not found: {name}")
    
    def list_profiles(self) -> List[str]:
        """List all available profiles"""
        profiles = []
        if os.path.exists(self.profiles_dir):
            for file in os.listdir(self.profiles_dir):
                if file.endswith('.json'):
                    profiles.append(file[:-5])  # Remove .json
        return sorted(profiles)
    
    def delete_profile(self, name: str):
        """Delete user profile"""
        filepath = os.path.join(self.profiles_dir, f"{name}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"🗑️  Deleted profile: {name}")
        if self.current_profile and self.current_profile.name == name:
            self.current_profile = None
    
    def get_current_profile(self) -> UserProfile:
        """Get current active profile"""
        if self.current_profile is None:
            raise ValueError("No profile loaded. Call load_profile() first.")
        return self.current_profile
    
    # ─── TRAINING CONFIG ───
    
    def get_training_config(self) -> Dict[str, Any]:
        """Get training parameters"""
        return self.training_config.copy()
    
    def set_training_config(self, **kwargs):
        """Update training parameters"""
        for key, value in kwargs.items():
            if key in self.training_config:
                self.training_config[key] = value
                logger.info(f"✏️  Updated training.{key} = {value}")
        self._save_json(self.training_config_file, self.training_config)
    
    # ─── OPTIMIZER CONFIG ───
    
    def get_optimizer_config(self) -> Dict[str, Any]:
        """Get optimizer parameters"""
        return self.optimizer_config.copy()
    
    def set_optimizer_config(self, **kwargs):
        """Update optimizer parameters"""
        for key, value in kwargs.items():
            if key in self.optimizer_config:
                self.optimizer_config[key] = value
                logger.info(f"✏️  Updated optimizer.{key} = {value}")
        self._save_json(self.optimizer_config_file, self.optimizer_config)
    
    # ─── VERSION MANAGEMENT ───
    
    def get_battery_config(self) -> Dict[str, float]:
        """Get battery configuration from current profile or defaults"""
        if self.current_profile:
            return {
                'capacity_kwh': self.current_profile.battery_capacity_kwh,
                'min_soc': self.current_profile.battery_min_soc_percent / 100.0,
                'max_soc': self.current_profile.battery_max_soc_percent / 100.0,
                'charge_efficiency': self.current_profile.battery_charge_efficiency,
                'discharge_efficiency': self.current_profile.battery_discharge_efficiency,
            }
        # Default values
        return {
            'capacity_kwh': 150.0,
            'min_soc': 0.1,
            'max_soc': 0.95,
            'charge_efficiency': 0.95,
            'discharge_efficiency': 0.95,
        }
    
    def get_grid_config(self) -> Dict[str, float]:
        """Get grid configuration from current profile or defaults"""
        if self.current_profile:
            return {
                'max_import_power_kw': self.current_profile.grid_max_import_kw,
                'max_export_power_kw': self.current_profile.grid_max_export_kw,
            }
        return {
            'max_import_power_kw': 100.0,
            'max_export_power_kw': 50.0,
        }
    
    def get_solar_config(self) -> Dict[str, float]:
        """Get solar configuration from current profile or defaults"""
        if self.current_profile:
            return {
                'capacity_kw': self.current_profile.solar_capacity_kw,
                'panel_efficiency': self.current_profile.solar_panel_efficiency,
                'inverter_efficiency': self.current_profile.solar_inverter_efficiency,
            }
        return {
            'capacity_kw': 20.0,
            'panel_efficiency': 0.20,
            'inverter_efficiency': 0.95,
        }
    
    def increment_version(self) -> str:
        """Increment patch version and return new version"""
        parts = self.current_model_version.split('.')
        parts[2] = str(int(parts[2]) + 1)  # Increment patch
        new_version = '.'.join(parts)
        self.current_model_version = new_version
        self.version_history['current_version'] = new_version
        self._save_json(self.version_history_file, self.version_history)
        logger.info(f"📌 Incremented model version to {new_version}")
        return new_version
    
    def record_training(self, episodes: int, avg_reward: float, best_reward: float,
                       training_time: float, model_path: str, metrics: Dict = None,
                       notes: str = "") -> ModelVersion:
        """Record a training session with metrics"""
        version = self.increment_version()
        
        model_ver = ModelVersion(
            version=version,
            trained_at=datetime.now().isoformat(),
            episodes=episodes,
            avg_reward=avg_reward,
            best_reward=best_reward,
            training_time_seconds=training_time,
            model_path=model_path,
            metrics=metrics or {},
            notes=notes,
        )
        
        # Store in history
        if 'versions' not in self.version_history:
            self.version_history['versions'] = {}
        
        self.version_history['versions'][version] = model_ver.to_dict()
        self._save_json(self.version_history_file, self.version_history)
        
        logger.info(f"✅ Recorded training v{version}: {episodes} episodes, avg_reward={avg_reward:.2f}")
        return model_ver
    
    def get_current_version(self) -> str:
        """Get current model version"""
        return self.current_model_version
    
    def get_version_history(self) -> List[ModelVersion]:
        """Get all recorded versions sorted by date"""
        versions = []
        if 'versions' in self.version_history:
            for ver_data in self.version_history['versions'].values():
                versions.append(ModelVersion.from_dict(ver_data))
        
        # Sort by trained_at descending (newest first)
        versions.sort(key=lambda v: v.trained_at, reverse=True)
        return versions
    
    def get_version_info(self, version: str) -> Optional[ModelVersion]:
        """Get info for specific version"""
        if 'versions' in self.version_history:
            if version in self.version_history['versions']:
                return ModelVersion.from_dict(self.version_history['versions'][version])
        return None
    
    # ─── SAFETY & RETRAINING ───
    
    def export_config(self, filepath: str):
        """Export all configs to file"""
        all_config = {
            'profile': self.current_profile.to_dict() if self.current_profile else None,
            'training': self.training_config,
            'optimizer': self.optimizer_config,
            'exported_at': datetime.now().isoformat(),
        }
        self._save_json(filepath, all_config)
        logger.info(f"📦 Exported config to {filepath}")
    
    def import_config(self, filepath: str):
        """Import configs from file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        if 'profile' in data and data['profile']:
            self.current_profile = UserProfile.from_dict(data['profile'])
        
        if 'training' in data:
            self.training_config.update(data['training'])
            self._save_json(self.training_config_file, self.training_config)
        
        if 'optimizer' in data:
            self.optimizer_config.update(data['optimizer'])
            self._save_json(self.optimizer_config_file, self.optimizer_config)
        
        logger.info(f"📥 Imported config from {filepath}")
    
    def create_default_profiles(self):
        """Create example profiles for testing"""
        now = datetime.now().isoformat()
        profiles = [
            UserProfile(
                name="residential_small",
                description="Small residential system (apartment)",
                created_at=now,
                battery_capacity_kwh=50.0,
                solar_capacity_kw=5.0,
                grid_max_import_kw=10.0,
                prioritize="cost",
                risk_tolerance="low",
            ),
            UserProfile(
                name="residential_large",
                description="Large residential system (villa)",
                created_at=now,
                battery_capacity_kwh=150.0,
                solar_capacity_kw=20.0,
                grid_max_import_kw=100.0,
                prioritize="sustainability",
                risk_tolerance="medium",
            ),
            UserProfile(
                name="industrial_small",
                description="Small industrial facility",
                created_at=now,
                battery_capacity_kwh=500.0,
                solar_capacity_kw=100.0,
                diesel_capacity_kw=100.0,
                grid_max_import_kw=500.0,
                prioritize="cost",
                risk_tolerance="high",
            ),
        ]
        
        for profile in profiles:
            self.save_profile(profile)
        
        logger.info(f"✅ Created {len(profiles)} default profiles")


# Global instance
_config = None


def get_config() -> EnhancedSystemConfig:
    """Get or create global config instance"""
    global _config
    if _config is None:
        _config = EnhancedSystemConfig()
    return _config


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    config = get_config()
    
    # Create default profiles
    config.create_default_profiles()
    
    # List profiles
    print("\n✅ Available profiles:")
    for profile_name in config.list_profiles():
        print(f"  - {profile_name}")
    
    # Load and display a profile
    print("\n" + "="*70)
    profile = config.load_profile("residential_large")
    print(profile.get_summary())
    
    # Show training config
    print("\n" + "="*70)
    print("\n⚙️  TRAINING CONFIG")
    for key, val in config.get_training_config().items():
        print(f"  {key:.<40} {val}")

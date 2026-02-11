"""User configuration management for Phase 4E.

Handles battery, load profile, and tariff settings persistence.
"""
from pathlib import Path
from typing import Dict, Optional, Literal
import json
from pydantic import BaseModel, ValidationError


class UserConfigModel(BaseModel):
    """User configuration data model."""
    battery_type: Literal['LFP', 'Lead-Acid', 'VRFB'] = 'LFP'
    battery_capacity_kwh: float = 10.0
    battery_efficiency: float = 0.95
    
    load_profile_type: Literal['standard', 'multi-shift', '24/7', 'custom'] = 'standard'
    load_peak_kw: float = 10.0
    
    tariff_region: str = 'ukraine'  # For future multi-region support
    
    class Config:
        """Pydantic config."""
        extra = 'allow'


class ConfigurationManager:
    """Manages user configuration persistence and validation."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            config_dir: Directory to store configs (defaults to energy_ml/configs/)
        """
        if config_dir is None:
            config_dir = Path(__file__).resolve().parent / "configs"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "user_config.json"
    
    def load_config(self) -> UserConfigModel:
        """Load user configuration from disk.
        
        Returns:
            UserConfigModel with loaded settings or defaults if not found
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return UserConfigModel(**data)
            except (json.JSONDecodeError, ValidationError):
                # Return defaults on error
                return UserConfigModel()
        return UserConfigModel()
    
    def save_config(self, config: UserConfigModel) -> bool:
        """Save user configuration to disk.
        
        Args:
            config: UserConfigModel to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config.dict(), f, indent=2)
            return True
        except Exception:
            return False
    
    def validate_battery_config(self, 
                               battery_type: str,
                               capacity_kwh: float,
                               efficiency: float = 0.95) -> Dict[str, any]:
        """Validate battery configuration.
        
        Args:
            battery_type: One of 'LFP', 'Lead-Acid', 'VRFB'
            capacity_kwh: Battery capacity in kWh (> 0)
            efficiency: Round-trip efficiency (0.7-1.0)
            
        Returns:
            Dict with 'valid': bool and 'errors': list of error messages
        """
        errors = []
        
        if battery_type not in ['LFP', 'Lead-Acid', 'VRFB']:
            errors.append(f"Invalid battery type: {battery_type}")
        
        if capacity_kwh <= 0:
            errors.append("Battery capacity must be > 0 kWh")
        elif capacity_kwh > 1000:
            errors.append("Battery capacity > 1000 kWh not supported")
        
        if not (0.7 <= efficiency <= 1.0):
            errors.append("Battery efficiency must be between 0.7 and 1.0")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def validate_load_profile(self,
                             profile_type: str,
                             peak_load_kw: float) -> Dict[str, any]:
        """Validate load profile configuration.
        
        Args:
            profile_type: One of 'standard', 'multi-shift', '24/7', 'custom'
            peak_load_kw: Peak load in kW (> 0)
            
        Returns:
            Dict with 'valid': bool and 'errors': list of error messages
        """
        errors = []
        
        if profile_type not in ['standard', 'multi-shift', '24/7', 'custom']:
            errors.append(f"Invalid profile type: {profile_type}")
        
        if peak_load_kw <= 0:
            errors.append("Peak load must be > 0 kW")
        elif peak_load_kw > 500:
            errors.append("Peak load > 500 kW not supported")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def get_battery_templates(self) -> Dict[str, Dict]:
        """Get battery configuration templates.
        
        Returns:
            Dict mapping battery type to recommended config
        """
        return {
            'LFP': {
                'name': 'Lithium Iron Phosphate (LFP)',
                'capacity_kwh': 10.0,
                'efficiency': 0.95,
                'description': '8000 cycles, best for daily cycling'
            },
            'Lead-Acid': {
                'name': 'Lead-Acid (Gel/AGM)',
                'capacity_kwh': 5.0,
                'efficiency': 0.85,
                'description': '600 cycles, lower cost, limited cycling'
            },
            'VRFB': {
                'name': 'Vanadium Redox Flow Battery',
                'capacity_kwh': 20.0,
                'efficiency': 0.75,
                'description': '20000+ cycles, long duration, large systems'
            }
        }
    
    def get_profile_templates(self) -> Dict[str, Dict]:
        """Get load profile templates.
        
        Returns:
            Dict mapping profile type to description
        """
        return {
            'standard': {
                'name': 'Standard Work Hours (9-18)',
                'peak_load_kw': 10.0,
                'description': 'Office or retail operation, active 9 AM - 6 PM'
            },
            'multi-shift': {
                'name': 'Multi-Shift (2-Shift)',
                'peak_load_kw': 15.0,
                'description': 'Manufacturing: 6 AM-2 PM + 10 PM-6 AM'
            },
            '24/7': {
                'name': '24/7 Continuous',
                'peak_load_kw': 20.0,
                'description': 'Continuous operation with baseline load'
            },
            'custom': {
                'name': 'Custom Hourly',
                'peak_load_kw': 10.0,
                'description': 'Define custom hourly load coefficients'
            }
        }

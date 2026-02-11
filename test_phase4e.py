"""Phase 4E: User Configuration UI and Dashboard Forms - Comprehensive Tests"""
import pytest
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from energy_ml.user_config import ConfigurationManager, UserConfigModel


class TestUserConfigModel:
    """Test Pydantic UserConfigModel."""
    
    def test_default_config_creation(self):
        """Test creating config with defaults."""
        config = UserConfigModel()
        
        assert config.battery_type == 'LFP'
        assert config.battery_capacity_kwh == 10.0
        assert config.battery_efficiency == 0.95
        assert config.load_profile_type == 'standard'
        assert config.load_peak_kw == 10.0
        assert config.tariff_region == 'ukraine'
    
    def test_custom_config_creation(self):
        """Test creating config with custom values."""
        config = UserConfigModel(
            battery_type='Lead-Acid',
            battery_capacity_kwh=20.0,
            battery_efficiency=0.85,
            load_profile_type='multi-shift',
            load_peak_kw=25.0,
            tariff_region='ukraine'
        )
        
        assert config.battery_type == 'Lead-Acid'
        assert config.battery_capacity_kwh == 20.0
        assert config.battery_efficiency == 0.85
        assert config.load_profile_type == 'multi-shift'
        assert config.load_peak_kw == 25.0
    
    def test_config_serialization(self):
        """Test config can be serialized to dict."""
        config = UserConfigModel(battery_capacity_kwh=15.0)
        config_dict = config.dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict['battery_capacity_kwh'] == 15.0
        assert config_dict['battery_type'] == 'LFP'
    
    def test_config_from_dict(self):
        """Test creating config from dict."""
        data = {
            'battery_type': 'VRFB',
            'battery_capacity_kwh': 50.0,
            'battery_efficiency': 0.75,
            'load_profile_type': '24/7',
            'load_peak_kw': 30.0,
            'tariff_region': 'ukraine'
        }
        
        config = UserConfigModel(**data)
        
        assert config.battery_type == 'VRFB'
        assert config.battery_capacity_kwh == 50.0
        assert config.load_profile_type == '24/7'


class TestConfigurationManager:
    """Test ConfigurationManager class."""
    
    def test_manager_initialization(self, tmp_path):
        """Test ConfigurationManager initialization."""
        manager = ConfigurationManager(config_dir=str(tmp_path))
        
        assert manager.config_dir == tmp_path
        assert manager.config_file == tmp_path / 'user_config.json'
        assert tmp_path.exists()
    
    def test_load_config_default(self, tmp_path):
        """Test loading default config when file doesn't exist."""
        manager = ConfigurationManager(config_dir=str(tmp_path))
        config = manager.load_config()
        
        assert isinstance(config, UserConfigModel)
        assert config.battery_type == 'LFP'
        assert config.battery_capacity_kwh == 10.0
    
    def test_save_and_load_config(self, tmp_path):
        """Test saving and loading configuration."""
        manager = ConfigurationManager(config_dir=str(tmp_path))
        
        # Create and save config
        original_config = UserConfigModel(
            battery_type='VRFB',
            battery_capacity_kwh=25.0,
            load_profile_type='24/7',
            load_peak_kw=20.0
        )
        
        success = manager.save_config(original_config)
        assert success is True
        assert manager.config_file.exists()
        
        # Load config
        loaded_config = manager.load_config()
        
        assert loaded_config.battery_type == 'VRFB'
        assert loaded_config.battery_capacity_kwh == 25.0
        assert loaded_config.load_profile_type == '24/7'
        assert loaded_config.load_peak_kw == 20.0
    
    def test_config_file_format(self, tmp_path):
        """Test that config is saved as valid JSON."""
        manager = ConfigurationManager(config_dir=str(tmp_path))
        
        config = UserConfigModel(battery_capacity_kwh=15.0)
        manager.save_config(config)
        
        # Verify file is valid JSON
        with open(manager.config_file, 'r') as f:
            data = json.load(f)
        
        assert isinstance(data, dict)
        assert data['battery_capacity_kwh'] == 15.0


class TestBatteryValidation:
    """Test battery configuration validation."""
    
    def test_validate_lfp_battery(self):
        """Test validating LFP battery."""
        manager = ConfigurationManager()
        result = manager.validate_battery_config('LFP', 10.0, 0.95)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
    
    def test_validate_lead_acid_battery(self):
        """Test validating Lead-Acid battery."""
        manager = ConfigurationManager()
        result = manager.validate_battery_config('Lead-Acid', 5.0, 0.85)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
    
    def test_validate_vrfb_battery(self):
        """Test validating VRFB battery."""
        manager = ConfigurationManager()
        result = manager.validate_battery_config('VRFB', 50.0, 0.75)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
    
    def test_invalid_battery_type(self):
        """Test error on invalid battery type."""
        manager = ConfigurationManager()
        result = manager.validate_battery_config('InvalidType', 10.0)
        
        assert result['valid'] is False
        assert len(result['errors']) == 1
        assert 'Invalid battery type' in result['errors'][0]
    
    def test_zero_capacity(self):
        """Test error on zero capacity."""
        manager = ConfigurationManager()
        result = manager.validate_battery_config('LFP', 0)
        
        assert result['valid'] is False
        assert any('must be > 0 kWh' in e for e in result['errors'])
    
    def test_negative_capacity(self):
        """Test error on negative capacity."""
        manager = ConfigurationManager()
        result = manager.validate_battery_config('LFP', -5.0)
        
        assert result['valid'] is False
        assert any('must be > 0 kWh' in e for e in result['errors'])
    
    def test_capacity_too_large(self):
        """Test error on capacity > 1000 kWh."""
        manager = ConfigurationManager()
        result = manager.validate_battery_config('LFP', 1001.0)
        
        assert result['valid'] is False
        assert any('1000 kWh' in e for e in result['errors'])
    
    def test_efficiency_too_low(self):
        """Test error on efficiency < 0.7."""
        manager = ConfigurationManager()
        result = manager.validate_battery_config('LFP', 10.0, 0.6)
        
        assert result['valid'] is False
        assert any('0.7 and 1.0' in e for e in result['errors'])
    
    def test_efficiency_too_high(self):
        """Test error on efficiency > 1.0."""
        manager = ConfigurationManager()
        result = manager.validate_battery_config('LFP', 10.0, 1.1)
        
        assert result['valid'] is False
        assert any('0.7 and 1.0' in e for e in result['errors'])
    
    def test_multiple_battery_errors(self):
        """Test multiple validation errors."""
        manager = ConfigurationManager()
        result = manager.validate_battery_config('InvalidType', 0, 0.5)
        
        assert result['valid'] is False
        assert len(result['errors']) >= 3
    
    def test_efficiency_boundary_low(self):
        """Test efficiency at lower boundary (0.7)."""
        manager = ConfigurationManager()
        result = manager.validate_battery_config('LFP', 10.0, 0.7)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
    
    def test_efficiency_boundary_high(self):
        """Test efficiency at upper boundary (1.0)."""
        manager = ConfigurationManager()
        result = manager.validate_battery_config('LFP', 10.0, 1.0)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0


class TestLoadProfileValidation:
    """Test load profile configuration validation."""
    
    def test_validate_standard_profile(self):
        """Test validating standard profile."""
        manager = ConfigurationManager()
        result = manager.validate_load_profile('standard', 10.0)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
    
    def test_validate_multi_shift_profile(self):
        """Test validating multi-shift profile."""
        manager = ConfigurationManager()
        result = manager.validate_load_profile('multi-shift', 15.0)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
    
    def test_validate_24_7_profile(self):
        """Test validating 24/7 profile."""
        manager = ConfigurationManager()
        result = manager.validate_load_profile('24/7', 20.0)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
    
    def test_validate_custom_profile(self):
        """Test validating custom profile."""
        manager = ConfigurationManager()
        result = manager.validate_load_profile('custom', 10.0)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
    
    def test_invalid_profile_type(self):
        """Test error on invalid profile type."""
        manager = ConfigurationManager()
        result = manager.validate_load_profile('invalid', 10.0)
        
        assert result['valid'] is False
        assert any('Invalid profile type' in e for e in result['errors'])
    
    def test_zero_peak_load(self):
        """Test error on zero peak load."""
        manager = ConfigurationManager()
        result = manager.validate_load_profile('standard', 0)
        
        assert result['valid'] is False
        assert any('must be > 0 kW' in e for e in result['errors'])
    
    def test_negative_peak_load(self):
        """Test error on negative peak load."""
        manager = ConfigurationManager()
        result = manager.validate_load_profile('standard', -10.0)
        
        assert result['valid'] is False
        assert any('must be > 0 kW' in e for e in result['errors'])
    
    def test_peak_load_too_large(self):
        """Test error on peak load > 500 kW."""
        manager = ConfigurationManager()
        result = manager.validate_load_profile('standard', 501.0)
        
        assert result['valid'] is False
        assert any('500 kW' in e for e in result['errors'])
    
    def test_peak_load_boundary_low(self):
        """Test peak load at lower boundary (>0)."""
        manager = ConfigurationManager()
        result = manager.validate_load_profile('standard', 0.1)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
    
    def test_peak_load_boundary_high(self):
        """Test peak load at upper boundary (500)."""
        manager = ConfigurationManager()
        result = manager.validate_load_profile('standard', 500.0)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0


class TestConfigurationTemplates:
    """Test configuration templates."""
    
    def test_get_battery_templates(self):
        """Test getting battery templates."""
        manager = ConfigurationManager()
        templates = manager.get_battery_templates()
        
        assert isinstance(templates, dict)
        assert 'LFP' in templates
        assert 'Lead-Acid' in templates
        assert 'VRFB' in templates
    
    def test_battery_template_structure_lfp(self):
        """Test LFP battery template structure."""
        manager = ConfigurationManager()
        templates = manager.get_battery_templates()
        lfp = templates['LFP']
        
        assert 'name' in lfp
        assert 'capacity_kwh' in lfp
        assert 'efficiency' in lfp
        assert 'description' in lfp
        
        assert lfp['name'] == 'Lithium Iron Phosphate (LFP)'
        assert isinstance(lfp['capacity_kwh'], (int, float))
        assert isinstance(lfp['efficiency'], (int, float))
    
    def test_battery_template_structure_lead_acid(self):
        """Test Lead-Acid battery template structure."""
        manager = ConfigurationManager()
        templates = manager.get_battery_templates()
        pb = templates['Lead-Acid']
        
        assert 'name' in pb
        assert pb['name'] == 'Lead-Acid (Gel/AGM)'
        assert 'cycles' in pb['description'].lower()
    
    def test_battery_template_structure_vrfb(self):
        """Test VRFB battery template structure."""
        manager = ConfigurationManager()
        templates = manager.get_battery_templates()
        vrfb = templates['VRFB']
        
        assert 'name' in vrfb
        assert 'Vanadium' in vrfb['name']
        assert 'cycles' in vrfb['description'].lower()
    
    def test_get_profile_templates(self):
        """Test getting load profile templates."""
        manager = ConfigurationManager()
        templates = manager.get_profile_templates()
        
        assert isinstance(templates, dict)
        assert 'standard' in templates
        assert 'multi-shift' in templates
        assert '24/7' in templates
        assert 'custom' in templates
    
    def test_profile_template_structure(self):
        """Test load profile template structure."""
        manager = ConfigurationManager()
        templates = manager.get_profile_templates()
        
        for profile_name, template in templates.items():
            assert 'name' in template
            assert 'peak_load_kw' in template
            assert 'description' in template
            assert isinstance(template['name'], str)
            assert isinstance(template['peak_load_kw'], (int, float))
            assert isinstance(template['description'], str)
    
    def test_standard_profile_template(self):
        """Test standard profile template details."""
        manager = ConfigurationManager()
        templates = manager.get_profile_templates()
        standard = templates['standard']
        
        assert 'Standard' in standard['name'] or '9' in standard['name']
        assert standard['peak_load_kw'] > 0


class TestConfigurationIntegration:
    """Integration tests for configuration system."""
    
    def test_full_config_lifecycle(self, tmp_path):
        """Test complete config save/load lifecycle."""
        manager = ConfigurationManager(config_dir=str(tmp_path))
        
        # Create a complex config
        config = UserConfigModel(
            battery_type='VRFB',
            battery_capacity_kwh=75.5,
            battery_efficiency=0.78,
            load_profile_type='multi-shift',
            load_peak_kw=45.25,
            tariff_region='ukraine'
        )
        
        # Save
        assert manager.save_config(config) is True
        
        # Load
        loaded = manager.load_config()
        
        # Verify
        assert loaded.battery_type == config.battery_type
        assert loaded.battery_capacity_kwh == config.battery_capacity_kwh
        assert loaded.battery_efficiency == config.battery_efficiency
        assert loaded.load_profile_type == config.load_profile_type
        assert loaded.load_peak_kw == config.load_peak_kw
    
    def test_config_persistence_multiple_saves(self, tmp_path):
        """Test that multiple saves work correctly."""
        manager = ConfigurationManager(config_dir=str(tmp_path))
        
        # First save
        config1 = UserConfigModel(battery_capacity_kwh=10.0)
        manager.save_config(config1)
        
        loaded1 = manager.load_config()
        assert loaded1.battery_capacity_kwh == 10.0
        
        # Second save with different values
        config2 = UserConfigModel(battery_capacity_kwh=20.0)
        manager.save_config(config2)
        
        loaded2 = manager.load_config()
        assert loaded2.battery_capacity_kwh == 20.0
    
    def test_validate_and_save_workflow(self, tmp_path):
        """Test validating then saving config."""
        manager = ConfigurationManager(config_dir=str(tmp_path))
        
        # Validate before saving
        battery_val = manager.validate_battery_config('LFP', 15.0)
        load_val = manager.validate_load_profile('24/7', 25.0)
        
        assert battery_val['valid'] is True
        assert load_val['valid'] is True
        
        # Create and save valid config
        config = UserConfigModel(
            battery_type='LFP',
            battery_capacity_kwh=15.0,
            load_profile_type='24/7',
            load_peak_kw=25.0
        )
        
        assert manager.save_config(config) is True
        assert manager.load_config().battery_capacity_kwh == 15.0


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_corrupted_json_graceful_fallback(self, tmp_path):
        """Test graceful fallback when JSON is corrupted."""
        manager = ConfigurationManager(config_dir=str(tmp_path))
        
        # Write corrupted JSON
        with open(manager.config_file, 'w') as f:
            f.write('{ invalid json')
        
        # Should return defaults
        config = manager.load_config()
        assert isinstance(config, UserConfigModel)
        assert config.battery_type == 'LFP'
    
    def test_missing_directory_creation(self, tmp_path):
        """Test that missing directory is created."""
        nested_path = tmp_path / 'nested' / 'config' / 'dir'
        manager = ConfigurationManager(config_dir=str(nested_path))
        
        assert nested_path.exists()
        assert nested_path.is_dir()
    
    def test_config_with_extra_fields(self):
        """Test config can handle extra fields."""
        data = {
            'battery_type': 'LFP',
            'battery_capacity_kwh': 10.0,
            'battery_efficiency': 0.95,
            'load_profile_type': 'standard',
            'load_peak_kw': 10.0,
            'tariff_region': 'ukraine',
            'extra_field': 'should_be_ignored'
        }
        
        # Pydantic allows extra fields by default
        config = UserConfigModel(**data)
        assert config.battery_type == 'LFP'


class TestDataTypes:
    """Test data type handling and conversions."""
    
    def test_numeric_precision(self):
        """Test numeric values maintain precision."""
        config = UserConfigModel(
            battery_capacity_kwh=10.123456,
            battery_efficiency=0.95678
        )
        
        assert config.battery_capacity_kwh == 10.123456
        assert config.battery_efficiency == 0.95678
    
    def test_string_types(self):
        """Test string type handling."""
        config = UserConfigModel(
            battery_type='LFP',
            load_profile_type='24/7',
            tariff_region='ukraine'
        )
        
        assert isinstance(config.battery_type, str)
        assert isinstance(config.load_profile_type, str)
        assert isinstance(config.tariff_region, str)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

/**
 * Server-side config helper
 * Bridges Python ConfigurationManager with TypeScript API endpoints
 */

import { spawn } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import fs from 'fs';

// Use synchronous imports for simple models
export interface IUserConfigModel {
  battery_type: 'LFP' | 'Lead-Acid' | 'VRFB';
  battery_capacity_kwh: number;
  battery_efficiency: number;
  load_profile_type: 'standard' | 'multi-shift' | '24/7' | 'custom';
  load_peak_kw: number;
  tariff_region: string;
}

export class UserConfigModel implements IUserConfigModel {
  battery_type: 'LFP' | 'Lead-Acid' | 'VRFB' = 'LFP';
  battery_capacity_kwh: number = 10.0;
  battery_efficiency: number = 0.95;
  load_profile_type: 'standard' | 'multi-shift' | '24/7' | 'custom' = 'standard';
  load_peak_kw: number = 10.0;
  tariff_region: string = 'ukraine';
  
  constructor(data?: Partial<IUserConfigModel>) {
    if (data) {
      Object.assign(this, data);
    }
  }
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

export interface BatteryTemplate {
  name: string;
  capacity_kwh: number;
  efficiency: number;
  description: string;
}

export interface LoadProfileTemplate {
  name: string;
  peak_load_kw: number;
  description: string;
}

/**
 * Configuration manager - handles Python interop
 */
export class ConfigurationManager {
  private configDir: string;
  private configFile: string;
  
  constructor(configDir?: string) {
    if (!configDir) {
      // Default to energy_ml/configs/
      const projectRoot = process.cwd();
      configDir = path.join(projectRoot, '..', 'energy_ml', 'configs');
    }
    
    this.configDir = configDir;
    this.configFile = path.join(this.configDir, 'user_config.json');
    
    // Ensure directory exists
    if (!fs.existsSync(this.configDir)) {
      fs.mkdirSync(this.configDir, { recursive: true });
    }
  }
  
  /**
   * Load user configuration from disk
   */
  load_config(): UserConfigModel {
    try {
      if (fs.existsSync(this.configFile)) {
        const data = JSON.parse(fs.readFileSync(this.configFile, 'utf-8'));
        return new UserConfigModel(data);
      }
    } catch (error) {
      console.error('[ConfigurationManager] Error loading config:', error);
    }
    
    // Return defaults
    return new UserConfigModel();
  }
  
  /**
   * Save user configuration to disk
   */
  save_config(config: UserConfigModel): boolean {
    try {
      const json = JSON.stringify(config, null, 2);
      fs.writeFileSync(this.configFile, json, 'utf-8');
      return true;
    } catch (error) {
      console.error('[ConfigurationManager] Error saving config:', error);
      return false;
    }
  }
  
  /**
   * Validate battery configuration
   */
  validate_battery_config(
    battery_type: string,
    capacity_kwh: number,
    efficiency: number = 0.95
  ): ValidationResult {
    const errors: string[] = [];
    
    if (!['LFP', 'Lead-Acid', 'VRFB'].includes(battery_type)) {
      errors.push(`Invalid battery type: ${battery_type}`);
    }
    
    if (capacity_kwh <= 0) {
      errors.push('Battery capacity must be > 0 kWh');
    } else if (capacity_kwh > 1000) {
      errors.push('Battery capacity > 1000 kWh not supported');
    }
    
    if (efficiency < 0.7 || efficiency > 1.0) {
      errors.push('Battery efficiency must be between 0.7 and 1.0');
    }
    
    return {
      valid: errors.length === 0,
      errors
    };
  }
  
  /**
   * Validate load profile configuration
   */
  validate_load_profile(
    profile_type: string,
    peak_load_kw: number
  ): ValidationResult {
    const errors: string[] = [];
    
    if (!['standard', 'multi-shift', '24/7', 'custom'].includes(profile_type)) {
      errors.push(`Invalid profile type: ${profile_type}`);
    }
    
    if (peak_load_kw <= 0) {
      errors.push('Peak load must be > 0 kW');
    } else if (peak_load_kw > 500) {
      errors.push('Peak load > 500 kW not supported');
    }
    
    return {
      valid: errors.length === 0,
      errors
    };
  }
  
  /**
   * Get battery configuration templates
   */
  get_battery_templates(): Record<string, BatteryTemplate> {
    return {
      'LFP': {
        name: 'Lithium Iron Phosphate (LFP)',
        capacity_kwh: 10.0,
        efficiency: 0.95,
        description: '8000 cycles, best for daily cycling'
      },
      'Lead-Acid': {
        name: 'Lead-Acid (Gel/AGM)',
        capacity_kwh: 5.0,
        efficiency: 0.85,
        description: '600 cycles, lower cost, limited cycling'
      },
      'VRFB': {
        name: 'Vanadium Redox Flow Battery',
        capacity_kwh: 20.0,
        efficiency: 0.75,
        description: '20000+ cycles, long duration, large systems'
      }
    };
  }
  
  /**
   * Get load profile templates
   */
  get_profile_templates(): Record<string, LoadProfileTemplate> {
    return {
      'standard': {
        name: 'Standard Work Hours (9-18)',
        peak_load_kw: 10.0,
        description: 'Office or retail operation, active 9 AM - 6 PM'
      },
      'multi-shift': {
        name: 'Multi-Shift (2-Shift)',
        peak_load_kw: 15.0,
        description: 'Manufacturing: 6 AM-2 PM + 10 PM-6 AM'
      },
      '24/7': {
        name: '24/7 Continuous',
        peak_load_kw: 20.0,
        description: 'Continuous operation with baseline load'
      },
      'custom': {
        name: 'Custom Hourly',
        peak_load_kw: 10.0,
        description: 'Define custom hourly load coefficients'
      }
    };
  }
}

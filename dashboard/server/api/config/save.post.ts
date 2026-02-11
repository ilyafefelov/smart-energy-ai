/**
 * POST /api/config/save
 * Accepts battery and load configuration, validates, and saves
 * Returns { success: bool, errors?: string[] }
 */
export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event);
    
    const { ConfigurationManager } = await import('../../utils/config-helper');
    const configManager = new ConfigurationManager();
    
    // Validate battery configuration
    const batteryValidation = configManager.validate_battery_config(
      body.battery_type || 'LFP',
      body.battery_capacity_kwh || 10.0,
      body.battery_efficiency || 0.95
    );
    
    // Validate load profile configuration
    const loadValidation = configManager.validate_load_profile(
      body.load_profile_type || 'standard',
      body.load_peak_kw || 10.0
    );
    
    const errors: string[] = [
      ...batteryValidation.errors,
      ...loadValidation.errors
    ];
    
    if (!batteryValidation.valid || !loadValidation.valid) {
      setResponseStatus(event, 400);
      return {
        success: false,
        errors
      };
    }
    
    // Create configuration model
    const { UserConfigModel } = await import('../../utils/config-helper');
    const config = new UserConfigModel({
      battery_type: body.battery_type || 'LFP',
      battery_capacity_kwh: body.battery_capacity_kwh || 10.0,
      battery_efficiency: body.battery_efficiency || 0.95,
      load_profile_type: body.load_profile_type || 'standard',
      load_peak_kw: body.load_peak_kw || 10.0,
      tariff_region: body.tariff_region || 'ukraine'
    });
    
    // Save configuration
    const success = configManager.save_config(config);
    
    if (!success) {
      setResponseStatus(event, 500);
      return {
        success: false,
        errors: ['Failed to save configuration to disk']
      };
    }
    
    setResponseStatus(event, 200);
    return {
      success: true,
      data: {
        battery_type: config.battery_type,
        battery_capacity_kwh: config.battery_capacity_kwh,
        battery_efficiency: config.battery_efficiency,
        load_profile_type: config.load_profile_type,
        load_peak_kw: config.load_peak_kw,
        tariff_region: config.tariff_region
      }
    };
  } catch (error) {
    console.error('[API] Error saving config:', error);
    setResponseStatus(event, 500);
    return {
      success: false,
      errors: ['Server error saving configuration']
    };
  }
});

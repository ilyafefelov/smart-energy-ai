/**
 * GET /api/config/current
 * Returns the current user configuration with defaults
 * Uses ConfigurationManager.load_config()
 */
export default defineEventHandler(async () => {
  try {
    const { ConfigurationManager } = await import('../../utils/config-helper');
    
    const configManager = new ConfigurationManager();
    const config = configManager.load_config();
    
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
    console.error('[API] Error loading config:', error);
    
    // Return defaults on error
    return {
      success: true,
      data: {
        battery_type: 'LFP',
        battery_capacity_kwh: 10.0,
        battery_efficiency: 0.95,
        load_profile_type: 'standard',
        load_peak_kw: 10.0,
        tariff_region: 'ukraine'
      }
    };
  }
});

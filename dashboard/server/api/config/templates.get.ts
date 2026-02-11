/**
 * GET /api/config/templates
 * Returns battery and load profile templates
 * Uses ConfigurationManager methods
 */
export default defineEventHandler(async () => {
  try {
    const { ConfigurationManager } = await import('../../utils/config-helper');
    
    const configManager = new ConfigurationManager();
    
    const templates = {
      battery: configManager.get_battery_templates(),
      load_profiles: configManager.get_profile_templates()
    };
    
    return {
      success: true,
      data: templates
    };
  } catch (error) {
    console.error('[API] Error loading templates:', error);
    
    // Return default templates on error
    return {
      success: true,
      data: {
        battery: {
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
        },
        load_profiles: {
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
        }
      }
    };
  }
});

/**
 * Configuration Templates API Endpoint
 * Returns battery and load profile templates
 */
export default defineEventHandler(async (event) => {
  try {
    const batteryTemplates = {
      'LFP': {
        name: 'Lithium Iron Phosphate (LFP)',
        description: '8000 cycles, best for daily cycling, safe chemistry',
        capacity_kwh: 10.0,
        efficiency: 0.95,
        c_rate_charge: 0.5,
        c_rate_discharge: 1.0,
        dod_max: 0.9,
        cycles_max: 8000,
        cost_uah_per_kwh: 13000,
        degradation_cost_per_cycle_uah: 16.25, // 13000 * 10 / 8000
        suitability_score: 9,
        pros: ['Long lifespan', 'High efficiency', 'Safe chemistry', 'Good for daily cycling'],
        cons: ['Higher upfront cost', 'Lower energy density than NMC']
      },
      'Lead-Acid': {
        name: 'Lead-Acid Deep Cycle',
        description: '600 cycles, lower cost but frequent replacement needed',
        capacity_kwh: 5.0,
        efficiency: 0.85,
        c_rate_charge: 0.2,
        c_rate_discharge: 0.3,
        dod_max: 0.5,
        cycles_max: 600,
        cost_uah_per_kwh: 5500,
        degradation_cost_per_cycle_uah: 45.83, // 5500 * 5 / 600
        suitability_score: 4,
        pros: ['Low upfront cost', 'Well-understood technology', 'Recyclable'],
        cons: ['Short lifespan', 'Low efficiency', 'High maintenance', 'Limited DoD']
      },
      'VRFB': {
        name: 'Vanadium Redox Flow Battery',
        description: '20000+ cycles, best for long-duration storage',
        capacity_kwh: 50.0,
        efficiency: 0.75,
        c_rate_charge: 0.25,
        c_rate_discharge: 0.25,
        dod_max: 1.0,
        cycles_max: 20000,
        cost_uah_per_kwh: 22000,
        degradation_cost_per_cycle_uah: 55.0, // 22000 * 50 / 20000
        suitability_score: 7,
        pros: ['Extremely long life', '100% DoD', 'Scalable', 'Low degradation'],
        cons: ['High upfront cost', 'Low power density', 'Complex system', 'Large footprint']
      }
    }

    const loadProfileTemplates = {
      'standard': {
        name: 'Standard Business Hours (9-18)',
        description: 'Office or retail operation, active 9 AM - 6 PM weekdays',
        peak_kw: 10.0,
        base_kw: 2.0,
        weekend_factor: 0.3,
        seasonal_variation: 0.15,
        peak_hours: '09:00-18:00',
        hourly_pattern: [
          0.2, 0.2, 0.2, 0.2, 0.2, 0.3,  // 00-05: Night
          0.4, 0.6, 0.8,                  // 06-08: Morning ramp
          1.0, 1.0, 0.9, 0.8, 0.9, 1.0, 1.0, 0.9, 0.8, // 09-17: Business hours
          0.6, 0.5, 0.4, 0.3, 0.3, 0.2   // 18-23: Evening
        ],
        arbitrage_potential: 8, // out of 10
        use_cases: ['Offices', 'Retail stores', 'Schools', 'Government buildings']
      },
      'multi_shift': {
        name: 'Multi-Shift Manufacturing',
        description: 'Two-shift manufacturing: 6 AM-2 PM + 10 PM-6 AM',
        peak_kw: 15.0,
        base_kw: 3.0,
        weekend_factor: 0.7,
        seasonal_variation: 0.25,
        peak_hours: '06:00-14:00, 22:00-06:00',
        hourly_pattern: [
          0.8, 0.8, 0.7, 0.6, 0.5, 0.4,  // 00-05: Night shift
          1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, // 06-13: Day shift
          0.3, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.3, // 14-21: Break
          0.9, 0.9                        // 22-23: Night shift start
        ],
        arbitrage_potential: 6,
        use_cases: ['Manufacturing', 'Processing plants', 'Mining operations', 'Logistics centers']
      },
      '24_7': {
        name: '24/7 Continuous Operations',
        description: 'Continuous process with minimal daily variation',
        peak_kw: 20.0,
        base_kw: 18.0,
        weekend_factor: 0.95,
        seasonal_variation: 0.1,
        peak_hours: 'Continuous',
        hourly_pattern: [
          0.9, 0.9, 0.9, 0.9, 0.9, 0.95, // 00-05: Slight reduction
          1.0, 1.0, 1.0, 1.0, 1.0, 1.0,  // 06-11: Full load
          1.0, 1.0, 1.0, 1.0, 1.0, 1.0,  // 12-17: Full load
          1.0, 1.0, 0.95, 0.95, 0.9, 0.9 // 18-23: Slight reduction
        ],
        arbitrage_potential: 4,
        use_cases: ['Data centers', 'Hospitals', 'Water treatment', 'Continuous process industries']
      },
      'custom': {
        name: 'Custom Hourly Profile',
        description: 'Define your own 24-hour load pattern',
        peak_kw: 10.0,
        base_kw: 2.0,
        weekend_factor: 0.6,
        seasonal_variation: 0.2,
        peak_hours: 'User-defined',
        hourly_pattern: new Array(24).fill(0.5), // Flat 50% profile
        arbitrage_potential: 5,
        use_cases: ['Unique operations', 'Testing scenarios', 'Specialized facilities']
      }
    }

    const tariffInfo = {
      ukraine: {
        name: 'Ukraine Standard Tariff',
        currency: 'UAH',
        peak_rate_default: 12.5,
        off_peak_rate_default: 8.0,
        peak_hours_default: '06:00-23:00',
        price_spread: 4.5,
        notes: [
          'Rates vary by region and consumer category',
          'Industrial consumers may have different rates',
          'Peak hours may vary by season'
        ]
      }
    }

    return {
      success: true,
      data: {
        battery: batteryTemplates,
        load_profiles: loadProfileTemplates,
        tariffs: tariffInfo
      },
      timestamp: new Date().toISOString(),
      version: '1.0'
    }
    
  } catch (error) {
    console.error('Templates fetch error:', error)
    
    throw createError({
      statusCode: 500,
      statusMessage: 'Internal server error fetching configuration templates'
    })
  }
})
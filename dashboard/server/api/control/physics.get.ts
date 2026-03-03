// Control API - Battery Physics Status Endpoint
// GET /api/control/physics

export default defineEventHandler(async (event) => {
  try {
    const [physicsPayload, batteryStatus] = await Promise.all([
      $fetch<any>('/api/physics/battery').catch(() => null),
      $fetch<any>('/api/battery/status').catch(() => null),
    ])

    const physics = physicsPayload?.data || null
    const battery = batteryStatus?.battery || {}

    if (physics) {
      const remainingCapacity = Number(physics?.degradation_model?.remaining_capacity_fraction ?? 0.95)
      const roundTrip = Number(physics?.efficiency_model?.round_trip_efficiency ?? 0.9)

      return {
        success: true,
        battery_type: physics.chemistry || 'LFP',
        capacity_kwh: Number(physics.capacity_kwh ?? battery.capacity ?? 150),
        max_power_kw: Number(physics?.power_limits?.max_discharge_power_kw ?? 5),
        state: {
          soc: Number((physics?.current_state?.soc_percent ?? battery.soc ?? 50) / 100),
          soh: remainingCapacity,
          temperature_c: Number(physics?.current_state?.temperature ?? battery.temperature ?? 25),
          cycles_completed: Number(physics?.current_state?.cycles_completed ?? battery.cycles ?? 0),
          current_power_kw: Number(battery.power ?? 0),
          voltage: Number(physics?.current_state?.voltage ?? battery.voltage ?? 52),
          internal_resistance: Number(physics?.degradation_model?.cycle_impact ?? 0.02)
        },
        current_efficiency: Number(physics?.efficiency_model?.charge_efficiency ?? 0.95),
        max_charge_power: Number(physics?.power_limits?.max_charge_power_kw ?? 5),
        max_discharge_power: Number(physics?.power_limits?.max_discharge_power_kw ?? 5),
        degradation_model: {
          nominal_cycles: Number(physics?.degradation_model?.expected_eol_cycles ?? 8000),
          degradation_per_cycle: Number(physics?.degradation_model?.cycle_impact ?? 0.00002),
          optimal_soc_range: [
            Number((physics?.physics_constraints?.recommended_soc_range?.[0] ?? 20) / 100),
            Number((physics?.physics_constraints?.recommended_soc_range?.[1] ?? 90) / 100),
          ],
          temperature_coefficient: 0.005
        },
        performance_metrics: {
          round_trip_efficiency: roundTrip,
          power_fade_factor: Number((1 - Math.max(0, 1 - remainingCapacity) * 0.3).toFixed(6)),
          capacity_fade_factor: remainingCapacity,
          internal_resistance_growth: Number((1 + Math.max(0, 1 - remainingCapacity) * 0.5).toFixed(6))
        },
        source: 'physics_api',
        last_updated: new Date().toISOString()
      }
    }
    
    return {
      success: true,
      battery_type: 'LFP',
      capacity_kwh: Number(battery.capacity ?? 150),
      max_power_kw: 5.0,
      state: {
        soc: Number((battery.soc ?? 50) / 100),
        soh: Number((battery.health ?? 95) / 100),
        temperature_c: Number(battery.temperature ?? 25),
        cycles_completed: Number(battery.cycles ?? 0),
        current_power_kw: Number(battery.power ?? 0),
        voltage: Number(battery.voltage ?? 52),
        internal_resistance: 0.02
      },
      current_efficiency: 0.95,
      max_charge_power: 5.0,
      max_discharge_power: 5.0,
      degradation_model: {
        nominal_cycles: 8000,
        degradation_per_cycle: 0.00002,
        optimal_soc_range: [0.2, 0.9],
        temperature_coefficient: 0.005
      },
      performance_metrics: {
        round_trip_efficiency: 0.9,
        power_fade_factor: 1.0,
        capacity_fade_factor: 1.0,
        internal_resistance_growth: 1.0
      },
      source: 'battery_status_fallback',
      last_updated: new Date().toISOString()
    }
    
  } catch (error) {
    console.error('Physics endpoint error:', error)
    
    return {
      success: false,
      error: error.message,
      // Minimal fallback
      battery_type: 'LFP',
      capacity_kwh: 10.0,
      max_power_kw: 5.0,
      state: {
        soc: 0.5,
        soh: 1.0,
        temperature_c: 25,
        cycles_completed: 0,
        current_power_kw: 0,
        voltage: 52,
        internal_resistance: 0.02
      },
      current_efficiency: 0.95,
      source: 'error_fallback'
    }
  }
})
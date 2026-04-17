// Control API - Battery Physics Status Endpoint
// GET /api/control/physics

import { getErrorMessage } from '../../utils/control-memory'

type BatteryStatusPayload = {
  battery?: {
    capacity?: number | null
    soc?: number | null
    health?: number | null
    temperature?: number | null
    cycles?: number | null
    power?: number | null
    voltage?: number | null
  } | null
}

type PhysicsPayload = {
  data?: {
    chemistry?: string | null
    capacity_kwh?: number | null
    current_state?: {
      soc_percent?: number | null
      temperature?: number | null
      cycles_completed?: number | null
      voltage?: number | null
    } | null
    degradation_model?: {
      remaining_capacity_fraction?: number | null
      cycle_impact?: number | null
      expected_eol_cycles?: number | null
    } | null
    efficiency_model?: {
      round_trip_efficiency?: number | null
      charge_efficiency?: number | null
    } | null
    power_limits?: {
      max_charge_power_kw?: number | null
      max_discharge_power_kw?: number | null
    } | null
    physics_constraints?: {
      recommended_soc_range?: Array<number | null | undefined> | null
    } | null
  } | null
}

type ControlPhysicsResponse = {
  success: boolean
  battery_type: string
  capacity_kwh: number
  max_power_kw: number
  state: {
    soc: number
    soh: number
    temperature_c: number
    cycles_completed: number
    current_power_kw: number
    voltage: number
    internal_resistance: number
  }
  current_efficiency: number
  max_charge_power: number
  max_discharge_power: number
  degradation_model?: {
    nominal_cycles: number
    degradation_per_cycle: number
    optimal_soc_range: [number, number]
    temperature_coefficient: number
  }
  performance_metrics?: {
    round_trip_efficiency: number
    power_fade_factor: number
    capacity_fade_factor: number
    internal_resistance_growth: number
  }
  source: string
  last_updated?: string
  error?: string
}

export default defineEventHandler(async (_event): Promise<ControlPhysicsResponse> => {
  try {
    const [physicsPayload, batteryStatus]: [PhysicsPayload | null, BatteryStatusPayload | null] = await Promise.all([
      $fetch<PhysicsPayload>('/api/physics/battery').catch(() => null),
      $fetch<BatteryStatusPayload>('/api/battery/status').catch(() => null),
    ])

    const physics = physicsPayload?.data ?? null
    const battery = batteryStatus?.battery ?? {}

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
      error: getErrorMessage(error, 'Physics endpoint error'),
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
      max_charge_power: 5.0,
      max_discharge_power: 5.0,
      source: 'error_fallback'
    }
  }
})
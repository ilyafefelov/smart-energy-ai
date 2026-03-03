import { getBatteryState, simulateBatteryBehavior } from '../../utils/battery'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

export default defineEventHandler(async (event) => {
  // GET /api/battery/status
  // STANDARDIZED RESPONSE: { success, battery: { soc, voltage, current, power, temperature, health, capacity, lastUpdated } }

  try {
    const tenant = await resolveTenantContext(event)
    // Optional: simulate behavior for testing
    const query = getQuery(event)
    if (query.simulate === 'true') {
      await simulateBatteryBehavior(tenant.id)
    }
    
    const state = await getBatteryState(tenant.id)
    
    // Compute derived fields
    const availableToDraw = Math.max(0, (state.soc - 15) / 100 * state.capacity)
    const availableToCharge = Math.max(0, (100 - state.soc) / 100 * state.capacity)
    const power = (state.voltage * state.current) / 1000 // kW
    
    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      battery: {
        soc: state.soc,
        capacity: state.capacity,
        voltage: state.voltage,
        current: state.current,
        temperature: state.temperature,
        health: state.health,
        power: parseFloat(power.toFixed(3)),
        availableToDraw: parseFloat(availableToDraw.toFixed(2)),
        availableToCharge: parseFloat(availableToCharge.toFixed(2)),
        lastUpdated: state.lastUpdate || new Date().toISOString()
      }
    }
  } catch (e: any) {
    const errorData = e?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('Failed to get battery status:', e)
    return {
      success: false,
      error: e.message || 'Failed to get battery status',
      battery: null
    }
  }
})


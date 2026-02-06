import { getBatteryState, simulateBatteryBehavior } from '~/server/utils/battery'

export default defineEventHandler(async (event) => {
  try {
    // Optional: simulate behavior for testing
    const query = getQuery(event)
    if (query.simulate === 'true') {
      await simulateBatteryBehavior()
    }
    
    const state = await getBatteryState()
    
    // Compute derived fields
    const availableToDraw = Math.max(0, (state.soc - 15) / 100 * state.capacity)
    const availableToCharge = Math.max(0, (100 - state.soc) / 100 * state.capacity)
    const power = (state.voltage * state.current) / 1000 // kW
    
    return {
      soc: state.soc,
      capacity: state.capacity,
      voltage: state.voltage,
      current: state.current,
      temperature: state.temperature,
      cycles: state.cycles,
      health: state.health,
      lastUpdate: state.lastUpdate,
      // Computed fields
      availableToDraw: parseFloat(availableToDraw.toFixed(2)),
      availableToCharge: parseFloat(availableToCharge.toFixed(2)),
      power: parseFloat(power.toFixed(3)),
      timestamp: Date.now()
    }
  } catch (e) {
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to get battery status: ${e.message}`
    })
  }
})

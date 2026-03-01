// Battery simulation API endpoint

let batteryState = {
  soc: 0.5, // 50%
  power: 0,
  voltage: 48,
  current: 0,
  temperature: 25,
  health: 1.0,
  cycleCount: 0,
  lastUpdated: new Date().toISOString()
}

let powerCommand = 0
let manualMode = true
let autoOptimization = false

export default defineEventHandler(async (event) => {
  const method = getMethod(event)
  
  if (method === 'GET') {
    return {
      success: true,
      battery: {
        soc: batteryState.soc,
        socPercentage: Math.round(batteryState.soc * 100 * 10) / 10,
        power: batteryState.power,
        voltage: batteryState.voltage,
        current: batteryState.current,
        temperature: batteryState.temperature,
        health: Math.round(batteryState.health * 100),
        cycleCount: batteryState.cycleCount,
        type: 'LFP',
        capacity: 10,
        usableCapacity: 8,
        socMin: 10,
        socMax: 90,
        maxChargePower: 5,
        maxDischargePower: 10,
        isCharging: batteryState.power > 0.1,
        isDischarging: batteryState.power < -0.1,
        isIdle: Math.abs(batteryState.power) <= 0.1,
        estimatedRuntime: null,
        estimatedChargeTime: null,
        powerCommand,
        manualMode,
        autoOptimization,
        isSimulationRunning: true,
        lastUpdated: batteryState.lastUpdated
      },
      specs: {
        typeName: 'LFP',
        efficiency: 0.95,
        roundTripEfficiency: 0.90,
        nominalVoltage: 48,
        selfDischarge: 1
      }
    }
  }
  
  if (method === 'POST') {
    const body = await readBody(event)
    
    if (body.action === 'setPower') {
      powerCommand = Number(body.power) || 0
      return { success: true, message: `Power set to ${powerCommand}kW`, powerCommand }
    }
    
    if (body.action === 'setAutoMode') {
      manualMode = false
      autoOptimization = body.enabled ?? true
      powerCommand = 0
      return { success: true, message: `Auto mode ${autoOptimization ? 'enabled' : 'disabled'}`, autoOptimization }
    }
    
    if (body.action === 'reset') {
      batteryState = { soc: 0.5, power: 0, voltage: 48, current: 0, temperature: 25, health: 1.0, cycleCount: 0, lastUpdated: new Date().toISOString() }
      return { success: true, message: 'Battery reset' }
    }
    
    return { success: false, error: 'Unknown action' }
  }
  
  return { success: false, error: 'Method not allowed' }
})

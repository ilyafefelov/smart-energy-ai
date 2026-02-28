import { createBatteryPhysics, type BatteryConfig, type BatteryState } from '../../utils/batteryPhysics'

// In-memory battery simulation state
let batteryEngine: any = null
let simulationInterval: NodeJS.Timeout | null = null
let isSimulationRunning = false

// Default battery configuration
const defaultBatteryConfig: BatteryConfig = {
  type: 'LFP',
  capacity: 10, // kWh
  efficiency: 0.95,
  cRateCharge: 0.5, // 0.5C = 2 hour charge
  cRateDischarge: 1.0, // 1C = 1 hour discharge
  socMin: 0.1, // 10%
  socMax: 0.9, // 90%
  temperature: 25,
  degradationRate: 0.0000125, // Per cycle
  maxCycles: 8000
}

// Initialize battery engine
function initializeBattery(config?: Partial<BatteryConfig>, initialState?: Partial<BatteryState>) {
  const fullConfig = { ...defaultBatteryConfig, ...config }
  batteryEngine = createBatteryPhysics(fullConfig, initialState)
  console.log('[Battery Simulator] Initialized with config:', fullConfig)
}

// Global power command (controlled by UI or automation)
let powerCommand = 0 // kW (+ = charge, - = discharge)
let manualMode = true
let autoOptimization = false

// Simulation step (runs every 5 seconds, simulates 5-second intervals)
function simulationStep() {
  if (!batteryEngine) return

  // Simulate 5-second time step (5/3600 = ~0.00139 hours)
  const deltaTime = 5 / 3600 // 5 seconds in hours
  
  // Apply current power command
  const newState = batteryEngine.simulate(powerCommand, deltaTime)
  
  // Auto power reduction near limits (safety feature)
  if (newState.soc >= 0.95 && powerCommand > 0) {
    powerCommand = 0 // Stop charging when nearly full
  }
  if (newState.soc <= 0.05 && powerCommand < 0) {
    powerCommand = 0 // Stop discharging when nearly empty
  }

  console.log(`[Battery] SOC: ${(newState.soc*100).toFixed(1)}%, Power: ${newState.power.toFixed(1)}kW, Health: ${(newState.health*100).toFixed(1)}%`)
}

// Start real-time simulation
function startSimulation() {
  if (isSimulationRunning) return
  
  if (!batteryEngine) {
    initializeBattery()
  }
  
  isSimulationRunning = true
  simulationInterval = setInterval(simulationStep, 5000) // Every 5 seconds
  console.log('[Battery Simulator] Started real-time simulation')
}

// Stop simulation
function stopSimulation() {
  if (simulationInterval) {
    clearInterval(simulationInterval)
    simulationInterval = null
  }
  isSimulationRunning = false
  console.log('[Battery Simulator] Stopped simulation')
}

// Start simulation on server start
startSimulation()

export default defineEventHandler(async (event) => {
  const method = getMethod(event)
  const url = getRequestURL(event)
  
  // Initialize battery if not exists
  if (!batteryEngine) {
    initializeBattery()
  }

  if (method === 'GET') {
    // Get current battery status
    const state = batteryEngine.getState()
    const config = batteryEngine.getConfig()
    const specs = batteryEngine.getSpecs()
    
    // Calculate additional metrics
    const maxPower = batteryEngine.calculateMaxPower?.() || { maxCharge: config.capacity * config.cRateCharge, maxDischarge: config.capacity * config.cRateDischarge }
    const runtime = powerCommand < 0 ? batteryEngine.estimateRuntime(powerCommand) : null
    const chargeTime = powerCommand > 0 ? batteryEngine.estimateChargeTime(powerCommand) : null
    
    return {
      success: true,
      battery: {
        // State
        soc: state.soc,
        socPercentage: Math.round(state.soc * 100 * 10) / 10,
        power: Math.round(state.power * 100) / 100,
        voltage: Math.round(state.voltage * 10) / 10,
        current: Math.round(state.current * 10) / 10,
        temperature: Math.round(state.temperature * 10) / 10,
        health: Math.round(state.health * 100),
        cycleCount: Math.round(state.cycleCount),
        
        // Configuration
        type: config.type,
        capacity: config.capacity,
        usableCapacity: config.capacity * (config.socMax - config.socMin),
        socMin: config.socMin * 100,
        socMax: config.socMax * 100,
        
        // Operational limits
        maxChargePower: Math.round(maxPower.maxCharge * 100) / 100,
        maxDischargePower: Math.round(maxPower.maxDischarge * 100) / 100,
        
        // Status
        isCharging: state.power > 0.1,
        isDischarging: state.power < -0.1,
        isIdle: Math.abs(state.power) <= 0.1,
        
        // Estimates
        estimatedRuntime: runtime ? Math.round(runtime * 60) : null, // minutes
        estimatedChargeTime: chargeTime ? Math.round(chargeTime * 60) : null, // minutes
        
        // Control
        powerCommand,
        manualMode,
        autoOptimization,
        
        // Simulation
        isSimulationRunning,
        lastUpdated: state.lastUpdated
      },
      specs: {
        typeName: config.type,
        efficiency: specs.efficiency,
        roundTripEfficiency: specs.roundTripEfficiency,
        nominalVoltage: specs.nominalVoltage,
        selfDischarge: specs.selfDischarge * 24 * 100 // % per day
      }
    }
  }

  if (method === 'POST') {
    const body = await readBody(event)
    
    if (body.action === 'setPower') {
      // Set manual power command
      const newPower = Number(body.power) || 0
      const maxCharge = batteryEngine.getConfig().capacity * batteryEngine.getConfig().cRateCharge
      const maxDischarge = batteryEngine.getConfig().capacity * batteryEngine.getConfig().cRateDischarge
      
      // Clamp power to safe limits
      powerCommand = Math.max(-maxDischarge, Math.min(maxCharge, newPower))
      manualMode = true
      autoOptimization = false
      
      console.log(`[Battery] Power command set to ${powerCommand}kW`)
      
      return {
        success: true,
        message: `Power set to ${powerCommand}kW`,
        powerCommand
      }
    }

    if (body.action === 'setAutoMode') {
      manualMode = false
      autoOptimization = body.enabled ?? true
      powerCommand = 0 // Reset to idle for auto mode
      
      console.log(`[Battery] Auto optimization ${autoOptimization ? 'enabled' : 'disabled'}`)
      
      return {
        success: true,
        message: `Auto mode ${autoOptimization ? 'enabled' : 'disabled'}`,
        autoOptimization
      }
    }

    if (body.action === 'updateConfig') {
      // Update battery configuration
      const { type, capacity, cRateCharge, cRateDischarge, socMin, socMax, efficiency } = body.config || {}
      
      const updates: Partial<BatteryConfig> = {}
      if (type) updates.type = type
      if (capacity) updates.capacity = Number(capacity)
      if (cRateCharge) updates.cRateCharge = Number(cRateCharge)
      if (cRateDischarge) updates.cRateDischarge = Number(cRateDischarge)
      if (socMin !== undefined) updates.socMin = Number(socMin) / 100
      if (socMax !== undefined) updates.socMax = Number(socMax) / 100
      if (efficiency) updates.efficiency = Number(efficiency)
      
      batteryEngine.updateConfig(updates)
      console.log(`[Battery] Configuration updated:`, updates)
      
      return {
        success: true,
        message: 'Configuration updated',
        config: batteryEngine.getConfig()
      }
    }

    if (body.action === 'reset') {
      // Reset battery state
      const newState: Partial<BatteryState> = {}
      if (body.soc !== undefined) newState.soc = Number(body.soc) / 100
      if (body.health !== undefined) newState.health = Number(body.health) / 100
      if (body.temperature !== undefined) newState.temperature = Number(body.temperature)
      if (body.cycleCount !== undefined) newState.cycleCount = Number(body.cycleCount)
      
      batteryEngine.reset(newState)
      powerCommand = 0
      
      console.log(`[Battery] Reset with state:`, newState)
      
      return {
        success: true,
        message: 'Battery reset',
        state: batteryEngine.getState()
      }
    }

    if (body.action === 'startSimulation') {
      startSimulation()
      return {
        success: true,
        message: 'Simulation started',
        isRunning: isSimulationRunning
      }
    }

    if (body.action === 'stopSimulation') {
      stopSimulation()
      return {
        success: true,
        message: 'Simulation stopped',
        isRunning: isSimulationRunning
      }
    }

    return {
      success: false,
      error: 'Unknown action'
    }
  }

  return {
    success: false,
    error: 'Method not allowed'
  }
})
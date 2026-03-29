// Battery Physics Simulation Engine
// Implements real battery behavior for LFP, Lead-Acid, and VRFB

export interface BatteryConfig {
  type: 'LFP' | 'Lead-Acid' | 'VRFB'
  capacity: number // kWh
  efficiency: number // 0-1
  cRateCharge: number // C-rate for charging (e.g., 0.5C = charge in 2 hours)
  cRateDischarge: number // C-rate for discharging
  socMin: number // Minimum SOC (0-1)
  socMax: number // Maximum SOC (0-1)
  temperature: number // Celsius
  degradationRate: number // Per cycle
  maxCycles: number
}

export interface BatteryState {
  soc: number // State of Charge (0-1)
  temperature: number // Celsius
  voltage: number // V
  current: number // A (+ = charging, - = discharging)
  power: number // kW (+ = charging, - = discharging)
  health: number // 0-1 (battery health)
  cycleCount: number
  lastUpdated: Date
}

export interface PowerFlowState {
  gridPower: number // kW (+ = from grid, - = to grid)
  batteryPower: number // kW (+ = charging, - = discharging)
  solarPower: number // kW (generation)
  windPower: number // kW (generation)
  loadPower: number // kW (consumption)
  efficiency: number // Overall system efficiency
}

class BatteryPhysicsEngine {
  private config: BatteryConfig
  private state: BatteryState
  private readonly batterySpecs: Record<string, any>

  constructor(config: BatteryConfig, initialState?: Partial<BatteryState>) {
    this.config = config
    
    // Battery technology specifications
    this.batterySpecs = {
      'LFP': {
        nominalVoltage: 3.2,
        chargeVoltage: 3.6,
        dischargeVoltage: 2.5,
        internalResistance: 0.05, // Ohms
        tempCoefficient: -0.003, // per °C
        selfDischarge: 0.0001, // per hour
        efficiency: 0.95,
        roundTripEfficiency: 0.90
      },
      'Lead-Acid': {
        nominalVoltage: 2.0,
        chargeVoltage: 2.4,
        dischargeVoltage: 1.75,
        internalResistance: 0.1,
        tempCoefficient: -0.005,
        selfDischarge: 0.002,
        efficiency: 0.85,
        roundTripEfficiency: 0.72
      },
      'VRFB': {
        nominalVoltage: 1.26,
        chargeVoltage: 1.6,
        dischargeVoltage: 0.8,
        internalResistance: 0.02,
        tempCoefficiency: -0.002,
        selfDischarge: 0.0005,
        efficiency: 0.75,
        roundTripEfficiency: 0.65
      }
    }

    this.state = {
      soc: initialState?.soc ?? 0.5,
      temperature: initialState?.temperature ?? 25,
      voltage: this.calculateVoltage(initialState?.soc ?? 0.5),
      current: 0,
      power: 0,
      health: initialState?.health ?? 1.0,
      cycleCount: initialState?.cycleCount ?? 0,
      lastUpdated: new Date()
    }
  }

  // Calculate voltage based on SOC and temperature
  private calculateVoltage(soc: number): number {
    const specs = this.batterySpecs[this.config.type]
    const baseVoltage = specs.nominalVoltage
    
    // SOC-voltage curve (simplified)
    let voltageMultiplier = 0.85 + (soc * 0.3) // 85% to 115% of nominal
    
    // Temperature compensation
    const tempDiff = this.state?.temperature ?? 25 - 25 // Difference from 25°C
    voltageMultiplier += tempDiff * specs.tempCoefficient
    
    return baseVoltage * voltageMultiplier * (this.config.capacity / 1) // Scale for battery bank
  }

  // Calculate internal resistance based on SOC and temperature
  private calculateInternalResistance(): number {
    const specs = this.batterySpecs[this.config.type]
    let resistance = specs.internalResistance
    
    // Resistance increases at low SOC
    if (this.state.soc < 0.2) {
      resistance *= (1 + (0.2 - this.state.soc) * 2)
    }
    
    // Resistance increases at low temperature
    const tempFactor = Math.max(0.5, 1 - (25 - this.state.temperature) * 0.02)
    resistance /= tempFactor
    
    // Resistance increases with degradation
    resistance *= (1 + (1 - this.state.health) * 0.5)
    
    return resistance
  }

  // Calculate maximum charge/discharge power based on C-rate and SOC
  private calculateMaxPower(): { maxCharge: number; maxDischarge: number } {
    const specs = this.batterySpecs[this.config.type]
    
    // Base power from C-rate
    let maxCharge = this.config.capacity * this.config.cRateCharge
    let maxDischarge = this.config.capacity * this.config.cRateDischarge
    
    // Reduce charge power near full SOC
    if (this.state.soc > 0.8) {
      const reduction = Math.pow((this.state.soc - 0.8) / 0.2, 2)
      maxCharge *= (1 - reduction * 0.7) // Up to 70% reduction
    }
    
    // Reduce discharge power near empty SOC
    if (this.state.soc < 0.2) {
      const reduction = Math.pow((0.2 - this.state.soc) / 0.2, 2)
      maxDischarge *= (1 - reduction * 0.8) // Up to 80% reduction
    }
    
    // Temperature derating
    if (this.state.temperature < 0) {
      const derating = Math.max(0.3, 1 + this.state.temperature * 0.02)
      maxCharge *= derating
      maxDischarge *= derating
    }
    
    // Health-based derating
    maxCharge *= this.state.health
    maxDischarge *= this.state.health
    
    return { maxCharge, maxDischarge }
  }

  // Simulate battery operation for a given power command
  simulate(powerCommand: number, deltaTimeHours: number): BatteryState {
    const { maxCharge, maxDischarge } = this.calculateMaxPower()
    
    // Clamp power to battery limits and SOC constraints
    let actualPower = powerCommand
    
    // Check SOC limits
    if (powerCommand > 0 && this.state.soc >= this.config.socMax) {
      actualPower = 0 // Can't charge when full
    } else if (powerCommand < 0 && this.state.soc <= this.config.socMin) {
      actualPower = 0 // Can't discharge when empty
    } else {
      // Clamp to C-rate limits
      actualPower = Math.max(-maxDischarge, Math.min(maxCharge, powerCommand))
    }
    
    // Calculate efficiency
    const specs = this.batterySpecs[this.config.type]
    let efficiency = specs.efficiency
    
    // Efficiency decreases with high power
    const powerRatio = Math.abs(actualPower) / this.config.capacity
    if (powerRatio > 0.5) {
      efficiency *= (1 - (powerRatio - 0.5) * 0.2) // Up to 20% reduction
    }
    
    // Apply efficiency based on charge/discharge
    const energyFlow = actualPower > 0 
      ? actualPower * efficiency * deltaTimeHours // Charging (less energy stored)
      : actualPower * deltaTimeHours / efficiency // Discharging (more energy drawn)
    
    // Calculate SOC change
    const socChange = energyFlow / this.config.capacity
    let newSoc = Math.max(0, Math.min(1, this.state.soc + socChange))
    
    // Self-discharge
    const selfDischarge = specs.selfDischarge * deltaTimeHours
    newSoc = Math.max(0, newSoc - selfDischarge)
    
    // Calculate current and voltage
    const newVoltage = this.calculateVoltage(newSoc)
    const internalR = this.calculateInternalResistance()
    const current = actualPower * 1000 / newVoltage // Convert kW to A
    
    // Update degradation (simplified)
    let newHealth = this.state.health
    if (Math.abs(actualPower) > 0) {
      const cycleDepth = Math.abs(socChange) * 2 // Full cycle = 100% SOC change
      const degradationFactor = this.config.degradationRate * cycleDepth
      newHealth = Math.max(0.5, this.state.health - degradationFactor)
    }
    
    // Temperature simulation (simplified)
    let newTemperature = this.state.temperature
    if (Math.abs(actualPower) > 0) {
      const heatGeneration = Math.pow(current, 2) * internalR * 0.001 // I²R losses in kW
      const tempRise = heatGeneration * deltaTimeHours * 10 // Simplified thermal model
      newTemperature += tempRise
      
      // Natural cooling
      const ambientTemp = 25
      const coolingRate = (newTemperature - ambientTemp) * 0.1 * deltaTimeHours
      newTemperature -= coolingRate
    }

    // Update state
    this.state = {
      soc: newSoc,
      temperature: newTemperature,
      voltage: newVoltage,
      current,
      power: actualPower,
      health: newHealth,
      cycleCount: this.state.cycleCount + (Math.abs(socChange) / 2), // Increment cycle count
      lastUpdated: new Date()
    }

    return { ...this.state }
  }

  // Get current battery state
  getState(): BatteryState {
    return { ...this.state }
  }

  // Get battery configuration
  getConfig(): BatteryConfig {
    return { ...this.config }
  }

  // Update battery configuration
  updateConfig(newConfig: Partial<BatteryConfig>): void {
    this.config = { ...this.config, ...newConfig }
  }

  // Get battery specifications for the current type
  getSpecs() {
    return this.batterySpecs[this.config.type]
  }

  // Calculate estimated runtime at current power
  estimateRuntime(power: number): number {
    if (power >= 0) return Infinity // Charging or idle
    
    const availableEnergy = (this.state.soc - this.config.socMin) * this.config.capacity
    const efficiency = this.batterySpecs[this.config.type].efficiency
    const usableEnergy = availableEnergy * efficiency
    
    return Math.max(0, usableEnergy / Math.abs(power)) // Hours
  }

  // Calculate estimated charge time
  estimateChargeTime(power: number): number {
    if (power <= 0) return Infinity // Discharging or idle
    
    const remainingCapacity = (this.config.socMax - this.state.soc) * this.config.capacity
    const efficiency = this.batterySpecs[this.config.type].efficiency
    const energyNeeded = remainingCapacity / efficiency
    
    return Math.max(0, energyNeeded / power) // Hours
  }

  // Reset battery to initial state
  reset(newState?: Partial<BatteryState>): void {
    this.state = {
      soc: newState?.soc ?? 0.5,
      temperature: newState?.temperature ?? 25,
      voltage: this.calculateVoltage(newState?.soc ?? 0.5),
      current: 0,
      power: 0,
      health: newState?.health ?? 1.0,
      cycleCount: newState?.cycleCount ?? 0,
      lastUpdated: new Date()
    }
  }
}

// Factory function to create battery physics engine
export function createBatteryPhysics(config: BatteryConfig, initialState?: Partial<BatteryState>): BatteryPhysicsEngine {
  return new BatteryPhysicsEngine(config, initialState)
}

// Utility functions
export function calculateBatteryMetrics(config: BatteryConfig, state: BatteryState) {
  const specs = {
    'LFP': { costPerKwh: 13000, maxCycles: 8000 },
    'Lead-Acid': { costPerKwh: 5500, maxCycles: 600 },
    'VRFB': { costPerKwh: 22000, maxCycles: 20000 }
  }
  
  const spec = specs[config.type]
  const usableCapacity = config.capacity * (config.socMax - config.socMin)
  const remainingCycles = Math.max(0, spec.maxCycles - state.cycleCount)
  const remainingLife = remainingCycles / spec.maxCycles
  
  return {
    usableCapacity,
    remainingCycles,
    remainingLife,
    estimatedValue: config.capacity * spec.costPerKwh * state.health,
    degradationCost: config.capacity * spec.costPerKwh * (1 - state.health)
  }
}

export { BatteryPhysicsEngine }
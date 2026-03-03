export type AutoStrategy = 'balanced' | 'max_earn' | 'max_battery_health' | 'max_charge'
export type LoadProfileType = 'standard' | 'multi-shift' | '24/7' | 'custom'
export type ExecutableCommand = 'charge' | 'discharge' | 'hold'

export type StrategyWeights = {
  cost: number
  batteryHealth: number
  renewableUse: number
  reliability: number
}

export type AutoStrategyContext = {
  optimizationStrategy: AutoStrategy
  loadProfileType: LoadProfileType
  currentHour: number
  currentPriceUahKwh: number | null
  avgPriceUahKwh: number | null
  batterySocPercent: number | null
  fallbackPowerKw: number
}

export type AutoStrategyDecision = {
  command: ExecutableCommand
  powerKw: number
  notes: string[]
  weights: StrategyWeights
}

function toNumberOrNull(value: unknown): number | null {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : null
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

function normalizePower(command: ExecutableCommand, powerKw: number, fallbackPowerKw: number): number {
  if (command === 'hold') {
    return 0
  }

  const absFallback = clamp(Math.abs(fallbackPowerKw || 2.5), 0.5, 10)
  const absPower = clamp(Math.abs(powerKw || absFallback), 0.5, 10)
  return command === 'charge' ? absPower : -absPower
}

function isMultiShiftDemandWindow(hour: number): boolean {
  return (hour >= 6 && hour <= 13) || hour === 22 || hour === 23
}

function isMultiShiftPreChargeWindow(hour: number): boolean {
  return hour === 4 || hour === 5 || hour === 20 || hour === 21
}

export function normalizeOptimizationStrategy(value: unknown): AutoStrategy {
  const normalized = String(value || '').trim().toLowerCase()
  if (normalized === 'max-earn' || normalized === 'max_earn') return 'max_earn'
  if (normalized === 'max-health' || normalized === 'max_battery_health') return 'max_battery_health'
  if (normalized === 'max-charge' || normalized === 'max_charge') return 'max_charge'
  return 'balanced'
}

export function normalizeLoadProfileType(value: unknown): LoadProfileType {
  const normalized = String(value || '').trim().toLowerCase()
  if (normalized === 'multi_shift' || normalized === 'multi-shift') return 'multi-shift'
  if (normalized === '24_7' || normalized === '24/7') return '24/7'
  if (normalized === 'custom') return 'custom'
  return 'standard'
}

export function buildStrategyWeights(strategy: AutoStrategy): StrategyWeights {
  if (strategy === 'max_earn') {
    return { cost: 0.65, batteryHealth: 0.1, renewableUse: 0.15, reliability: 0.1 }
  }
  if (strategy === 'max_battery_health') {
    return { cost: 0.15, batteryHealth: 0.65, renewableUse: 0.1, reliability: 0.1 }
  }
  if (strategy === 'max_charge') {
    return { cost: 0.2, batteryHealth: 0.1, renewableUse: 0.6, reliability: 0.1 }
  }
  return { cost: 0.35, batteryHealth: 0.25, renewableUse: 0.25, reliability: 0.15 }
}

export function mapRecommendationActionToExecution(
  action: string,
  fallbackPowerKw: number,
): { command: ExecutableCommand; power_kw: number } {
  const normalized = String(action || 'HOLD').toUpperCase()
  if (normalized === 'BUY' || normalized === 'CHARGE') {
    return { command: 'charge', power_kw: Math.max(0.5, Math.abs(fallbackPowerKw)) }
  }
  if (normalized === 'SELL' || normalized === 'DISCHARGE') {
    return { command: 'discharge', power_kw: -Math.max(0.5, Math.abs(fallbackPowerKw)) }
  }
  return { command: 'hold', power_kw: 0 }
}

export function mapExecutionCommandToRecommendationAction(command: ExecutableCommand): 'BUY' | 'SELL' | 'HOLD' {
  if (command === 'charge') return 'BUY'
  if (command === 'discharge') return 'SELL'
  return 'HOLD'
}

export function applyAutoStrategyDecision(
  baseCommand: ExecutableCommand,
  basePowerKw: number,
  context: AutoStrategyContext,
): AutoStrategyDecision {
  const notes: string[] = []
  const strategy = context.optimizationStrategy
  const loadProfile = context.loadProfileType
  const weights = buildStrategyWeights(strategy)

  let command: ExecutableCommand = baseCommand
  let powerKw = basePowerKw

  const soc = toNumberOrNull(context.batterySocPercent) ?? 50
  const currentPrice = toNumberOrNull(context.currentPriceUahKwh)
  const avgPrice = toNumberOrNull(context.avgPriceUahKwh)
  const hasPriceSignal = currentPrice != null && avgPrice != null && avgPrice > 0
  const spreadRatio = hasPriceSignal ? ((currentPrice as number) - (avgPrice as number)) / (avgPrice as number) : 0

  if (strategy === 'max_charge') {
    if (soc < 88 && command !== 'charge') {
      command = 'charge'
      powerKw = Math.max(Math.abs(context.fallbackPowerKw) * 0.85, 0.9)
      notes.push('max_charge bias converted action to charge below 88% SoC')
    }
    if (soc >= 95) {
      command = 'hold'
      powerKw = 0
      notes.push('max_charge guardrail held command above 95% SoC')
    }
  } else if (strategy === 'max_battery_health') {
    if (soc >= 35 && soc <= 75) {
      command = 'hold'
      powerKw = 0
      notes.push('max_battery_health reduced cycling in 35-75% SoC band')
    } else if (soc < 25) {
      command = 'charge'
      powerKw = Math.max(Math.abs(context.fallbackPowerKw) * 0.55, 0.6)
      notes.push('max_battery_health recovery charge below 25% SoC')
    } else if (soc > 85) {
      command = 'discharge'
      powerKw = -Math.max(Math.abs(context.fallbackPowerKw) * 0.55, 0.6)
      notes.push('max_battery_health protective discharge above 85% SoC')
    } else if (command !== 'hold') {
      powerKw = Math.sign(powerKw || 1) * Math.max(Math.abs(powerKw) * 0.6, 0.5)
      notes.push('max_battery_health scaled power magnitude down')
    }
  } else if (strategy === 'max_earn' && hasPriceSignal) {
    if (spreadRatio <= -0.08) {
      command = 'charge'
      powerKw = Math.max(Math.abs(context.fallbackPowerKw) * 1.1, 1)
      notes.push('max_earn charging on discounted price signal')
    } else if (spreadRatio >= 0.08 && soc > 25) {
      command = 'discharge'
      powerKw = -Math.max(Math.abs(context.fallbackPowerKw) * 1.1, 1)
      notes.push('max_earn discharging on premium price signal')
    }
  }

  if (loadProfile === 'multi-shift') {
    if (isMultiShiftDemandWindow(context.currentHour) && command === 'hold' && soc > 45) {
      command = 'discharge'
      powerKw = -Math.max(Math.abs(context.fallbackPowerKw) * 0.7, 0.8)
      notes.push('multi-shift demand window triggered peak-shave discharge')
    }

    if (isMultiShiftPreChargeWindow(context.currentHour) && command === 'hold' && soc < 75) {
      command = 'charge'
      powerKw = Math.max(Math.abs(context.fallbackPowerKw) * 0.7, 0.8)
      notes.push('multi-shift pre-window triggered pre-charge')
    }

    if (isMultiShiftDemandWindow(context.currentHour) && command === 'discharge') {
      powerKw = -Math.max(Math.abs(powerKw) * 1.15, 0.9)
      notes.push('multi-shift boosted discharge intensity during active shift')
    }
  }

  if (loadProfile === '24/7' && command !== 'hold') {
    powerKw = Math.sign(powerKw || 1) * Math.max(Math.abs(powerKw) * 0.85, 0.5)
    notes.push('24/7 profile smoothed command magnitude for continuous load')
  }

  const normalizedPower = normalizePower(command, powerKw, context.fallbackPowerKw)

  return {
    command,
    powerKw: normalizedPower,
    notes,
    weights,
  }
}

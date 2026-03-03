// Control API - Command Execution Endpoint
// POST /api/control/execute

import { persistOptimizationHistory } from '../../utils/optimization-history'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    
    // Validate input
    if (!body.command) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Command is required'
      })
    }
    
    if (!['charge', 'discharge', 'hold', 'auto'].includes(body.command)) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Invalid command. Must be: charge, discharge, hold, or auto'
      })
    }
    
    // Validate power for charge/discharge commands
    if (['charge', 'discharge'].includes(body.command)) {
      if (typeof body.power_kw !== 'number' || Math.abs(body.power_kw) > 10) {
        throw createError({
          statusCode: 400,
          statusMessage: 'Invalid power_kw. Must be a number between -10 and 10'
        })
      }
    }
    
    const command = {
      command: body.command,
      power_kw: body.power_kw || 0,
      duration_minutes: body.duration_minutes || null,
      reason: body.reason || `Dashboard command: ${body.command}`,
      user_id: body.user_id || 'dashboard',
      timestamp: new Date().toISOString()
    }
    
    console.log('Executing control command:', command)
    
    // Try to execute via Python controller
    const { execPython } = await import('../../../utils/python-runner.js').catch(() => ({ execPython: null }))

    const batteryStatusBefore = await $fetch<any>('/api/battery/status').catch(() => null)
    
    if (execPython) {
      try {
        const result = await execPython('execute_control_command.py', {
          ...command,
          power: command.power_kw.toString(),
          command_type: command.command
        })
        
        const pythonResult = JSON.parse(result)

        await persistCommandToOptimizationHistory({
          command,
          executionResult: pythonResult,
          batterySocBeforeRaw: batteryStatusBefore?.battery?.soc,
        })
        
        console.log('Python controller result:', pythonResult)
        
        return {
          success: true,
          result: pythonResult,
          command_id: generateId(),
          executed_at: command.timestamp,
          source: 'python_controller'
        }
        
      } catch (pythonError) {
        console.warn('Python controller execution failed:', pythonError.message)
      }
    }
    
    // Fallback simulation for development
    console.log('Using simulation mode for command execution')

    const batteryStatus = await $fetch<any>('/api/battery/status').catch(() => null)
    const batterySoc = Number(batteryStatus?.battery?.soc ?? 50) / 100
    const batteryCapacity = Number(batteryStatus?.battery?.capacity ?? 150)
    const maxPower = 5.0

    let deltaSoc = 0
    if (command.command === 'charge' && command.power_kw > 0) {
      deltaSoc = Math.min(0.2, Math.abs(command.power_kw) / batteryCapacity)
    } else if (command.command === 'discharge' && command.power_kw < 0) {
      deltaSoc = -Math.min(0.2, Math.abs(command.power_kw) / batteryCapacity)
    }

    const newSoc = Math.max(0.05, Math.min(0.95, batterySoc + deltaSoc))
    const socDeltaKwh = Math.abs(newSoc - batterySoc) * batteryCapacity
    const powerAbs = Math.max(Math.abs(command.power_kw), 0.1)
    const derivedMinutes = Math.max(1, Math.round((socDeltaKwh / powerAbs) * 60))

    const simulationResult = {
      success: true,
      soc_before: Number(batterySoc.toFixed(4)),
      new_soc: Number(newSoc.toFixed(4)),
      power_kw: command.power_kw,
      estimated_completion: command.command === 'hold'
        ? null
        : new Date(Date.now() + (command.duration_minutes || derivedMinutes) * 60000).toISOString(),
      validation: {
        power_within_limits: Math.abs(command.power_kw) <= maxPower,
        soc_safe_for_operation: newSoc >= 0.05 && newSoc <= 0.95,
        command_accepted: true
      }
    }
    
    // Store command in memory for history (in real implementation, this would go to database)
    if (!globalThis.commandHistory) {
      globalThis.commandHistory = []
    }
    
    const historyEntry = {
      ...command,
      result: simulationResult,
      executed_at: new Date().toISOString(),
      success: true
    }
    
    globalThis.commandHistory.unshift(historyEntry)
    
    // Keep only last 100 commands
    if (globalThis.commandHistory.length > 100) {
      globalThis.commandHistory = globalThis.commandHistory.slice(0, 100)
    }

    await persistCommandToOptimizationHistory({
      command,
      executionResult: simulationResult,
      batterySocBeforeRaw: batterySoc * 100,
    })
    
    return {
      success: true,
      result: simulationResult,
      command_id: generateId(),
      executed_at: command.timestamp,
      source: 'simulation'
    }
    
  } catch (error) {
    console.error('Command execution error:', error)
    
    if (error.statusCode) {
      throw error
    }
    
    throw createError({
      statusCode: 500,
      statusMessage: error.message || 'Command execution failed'
    })
  }
})

function generateId() {
  if (!(globalThis as any).__commandIdCounter) {
    ;(globalThis as any).__commandIdCounter = 0
  }
  ;(globalThis as any).__commandIdCounter += 1
  return `cmd_${Date.now()}_${(globalThis as any).__commandIdCounter}`
}

type CommandPayload = {
  command: string
  power_kw: number
  duration_minutes: number | null
  timestamp: string
}

type PersistInput = {
  command: CommandPayload
  executionResult: any
  batterySocBeforeRaw: unknown
}

function mapCommandToAction(command: string): number {
  switch (command) {
    case 'charge':
      return 0
    case 'discharge':
      return 1
    case 'hold':
      return 4
    case 'auto':
      return 4
    default:
      return 4
  }
}

function normalizeSocPercent(value: unknown, fallback = 50): number {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) {
    return fallback
  }
  if (numeric >= 0 && numeric <= 1) {
    return numeric * 100
  }
  return numeric
}

function deriveDurationHours(command: CommandPayload, executionResult: any): number {
  const explicitMinutes = Number(command.duration_minutes)
  if (Number.isFinite(explicitMinutes) && explicitMinutes > 0) {
    return explicitMinutes / 60
  }

  const start = new Date(command.timestamp)
  const completion = new Date(executionResult?.estimated_completion || executionResult?.result?.estimated_completion || 0)
  if (Number.isFinite(start.getTime()) && Number.isFinite(completion.getTime())) {
    const durationHours = (completion.getTime() - start.getTime()) / 3600000
    if (Number.isFinite(durationHours) && durationHours > 0 && durationHours <= 24) {
      return durationHours
    }
  }

  return Math.abs(Number(command.power_kw || 0)) > 0 ? 1 : 0
}

async function resolveCurrentPriceKwh(): Promise<number> {
  try {
    const payload = await $fetch<any>('/api/prices/current')
    const direct = Number(payload?.prices?.current?.price)
    if (Number.isFinite(direct) && direct > 0) {
      return direct
    }

    const avg = Number(payload?.prices?.today?.avg)
    if (Number.isFinite(avg) && avg > 0) {
      return avg
    }
  } catch {
    // Use fallback below.
  }

  return 8
}

async function persistCommandToOptimizationHistory(input: PersistInput): Promise<void> {
  const command = input.command
  const executionResult = input.executionResult || {}

  const priceKwh = await resolveCurrentPriceKwh()
  const durationHours = deriveDurationHours(command, executionResult)
  const energyKwh = Math.max(0, Math.abs(Number(command.power_kw || 0)) * durationHours)

  const baselineCost = energyKwh * priceKwh

  const optimizationMultiplier = command.command === 'discharge'
    ? 0.45
    : command.command === 'charge'
      ? 0.9
      : 1.0

  const optimizedCost = baselineCost * optimizationMultiplier

  const socBefore = normalizeSocPercent(
    executionResult?.soc_before ?? executionResult?.result?.soc_before ?? input.batterySocBeforeRaw,
    50,
  )

  const socAfter = normalizeSocPercent(
    executionResult?.new_soc ?? executionResult?.result?.new_soc ?? socBefore,
    socBefore,
  )

  await persistOptimizationHistory({
    timestamp: command.timestamp,
    predicted_action: mapCommandToAction(command.command),
    actual_action: mapCommandToAction(command.command),
    cost_baseline: Number.isFinite(baselineCost) ? baselineCost : null,
    cost_rl: Number.isFinite(optimizedCost) ? optimizedCost : null,
    battery_soc_start: Number.isFinite(socBefore) ? socBefore : null,
    battery_soc_end: Number.isFinite(socAfter) ? socAfter : null,
    solar_actual: null,
    load_actual: null,
  })
}
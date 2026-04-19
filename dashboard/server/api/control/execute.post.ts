// Control API - Command Execution Endpoint
// POST /api/control/execute

import {
  buildDecisionSnapshot,
  buildOptimizationExecutionKey,
  type DecisionSnapshot,
  type PersistOptimizationHistoryResult,
  persistOptimizationHistory,
} from '../../utils/optimization-history'
import { recordBillingUsageEvent } from '../../utils/billing'
import { updateBatteryState } from '../../utils/battery'
import { updateBatteryControlState } from '../../utils/battery-control-state'
import {
  applyAutoStrategyDecision,
  buildStrategyWeights,
  mapRecommendationActionToExecution,
  normalizeLoadProfileType,
  normalizeOptimizationStrategy,
  type AutoStrategy,
  type LoadProfileType,
  type StrategyWeights,
} from '../../utils/auto-strategy'
import { getCommandHistory, getErrorMessage, hasStatusCode, setCommandHistory, setControlModeState, type CommandHistoryRecord } from '../../utils/control-memory'
import { normalizeDecisionSource } from '../../utils/recommendation-contract'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

type ExecutableCommand = 'charge' | 'discharge' | 'hold'

type ExecutionLineage = {
  forecast_run_id: string | null
  forecast_model_version: string | null
  optimization_run_id: string | null
}

type ExecutionPlan = {
  command: ExecutableCommand
  power_kw: number
  decisionSource: 'manual' | 'dagster' | 'ml' | 'heuristic'
  reasoning: string
  requestedCommand: string
  eventType: 'manual_command' | 'auto_transition'
  modeFrom: 'manual' | 'automatic'
  modeTo: 'manual' | 'automatic'
  optimizationStrategy: AutoStrategy
  loadProfileType: LoadProfileType
  strategyWeights: StrategyWeights
  recommendationSource: string
  decisionSnapshot: DecisionSnapshot
  lineage: ExecutionLineage
}

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const tenant = await resolveTenantContext(event, { body })
    const requestTimestamp = resolveIncomingTimestamp(body?.timestamp)
    const commandId = resolveCommandId(body, requestTimestamp)
    
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
      command_id: commandId,
      schedule_id: normalizeOptionalString(body.schedule_id),
      tenant_id: tenant.id,
      command: body.command,
      power_kw: body.power_kw || 0,
      duration_minutes: body.duration_minutes || null,
      reason: body.reason || `Dashboard command: ${body.command}`,
      user_id: body.user_id || 'dashboard',
      timestamp: requestTimestamp,
    }
    const requestedLineage: ExecutionLineage = {
      forecast_run_id: normalizeOptionalString(body?.forecast_run_id),
      forecast_model_version: normalizeOptionalString(body?.forecast_model_version),
      optimization_run_id: normalizeOptionalString(body?.optimization_run_id),
    }
    
    console.log('Executing control command:', command)
    
    // Try to execute via Python controller
    const pythonScript = 'execute_control_command.py'
    let fallbackReasonCode: string | null = null
    const pythonRunner: any = await import('../../utils/python-runner.js').catch(() => ({ execPython: null, hasPythonScript: null }))
    const execPython = pythonRunner?.execPython
    const hasPythonScript = pythonRunner?.hasPythonScript
    const pythonScriptAvailable = Boolean(execPython && hasPythonScript && hasPythonScript(pythonScript))

    const batteryStatusBefore = await $fetch<any>('/api/battery/status', {
      headers: {
        'x-tenant-id': tenant.id,
      },
      query: {
        tenantId: tenant.id,
      },
    }).catch(() => null)
    
    const executionPlan = await resolveExecutionPlan(command, tenant.id, requestedLineage)
    const executableCommand = {
      ...command,
      command: executionPlan.command,
      power_kw: executionPlan.power_kw,
      reason: executionPlan.reasoning || command.reason,
    }

    if (pythonScriptAvailable && execPython) {
      try {
        const result = await execPython(pythonScript, {
          command: executableCommand.command,
          power: executableCommand.power_kw,
          duration: executableCommand.duration_minutes,
          reason: executableCommand.reason,
          user_id: executableCommand.user_id,
        })
        
        const pythonResult = JSON.parse(result)

        const historyPersistResult = await persistCommandToOptimizationHistory({
          command: executableCommand,
          executionResult: pythonResult,
          executionSource: 'python_controller',
          batterySocBeforeRaw: batteryStatusBefore?.battery?.soc,
          decisionSource: executionPlan.decisionSource,
          eventType: executionPlan.eventType,
          modeFrom: executionPlan.modeFrom,
          modeTo: executionPlan.modeTo,
          requestedCommand: executionPlan.requestedCommand,
          decisionSnapshot: executionPlan.decisionSnapshot,
          lineage: executionPlan.lineage,
        })

        recordBillingForExecutedCommand(executableCommand, pythonResult, 'python_controller', executionPlan.requestedCommand)

        setControlModeState(tenant.id, {
          mode: executionPlan.modeTo,
          requested_command: executionPlan.requestedCommand,
          active_command: executionPlan.command,
          decision_source: executionPlan.decisionSource,
          reason: executableCommand.reason,
          updated_at: new Date().toISOString(),
        })

        await updateBatteryControlState({
          powerCommand: Number(executableCommand.power_kw || 0),
          manualMode: executionPlan.modeTo !== 'automatic',
          autoOptimization: executionPlan.modeTo === 'automatic',
        }, tenant.id)

        await persistBatterySignalForCommand(executableCommand, tenant.id)

        appendCommandHistory({
          ...executableCommand,
          requested_command: executionPlan.requestedCommand,
          resolved_command: executionPlan.command,
          decision_source: executionPlan.decisionSource,
          recommendation_source: executionPlan.recommendationSource,
          optimization_strategy: executionPlan.optimizationStrategy,
          load_profile_type: executionPlan.loadProfileType,
          strategy_weights: executionPlan.strategyWeights,
          execution_key: historyPersistResult.executionKey,
          execution_status: pythonResult?.success === false ? 'failed' : 'executed',
          is_reconciled: historyPersistResult.reconciled,
          reconciliation_note: historyPersistResult.reconciliationNote ?? null,
          forecast_run_id: executionPlan.lineage.forecast_run_id,
          forecast_model_version: executionPlan.lineage.forecast_model_version,
          optimization_run_id: executionPlan.lineage.optimization_run_id,
          decision_snapshot: executionPlan.decisionSnapshot,
          tenant_id: tenant.id,
          result: pythonResult,
          executed_at: new Date().toISOString(),
          success: true,
          event_type: executionPlan.eventType,
          mode_from: executionPlan.modeFrom,
          mode_to: executionPlan.modeTo,
        })
        
        console.log('Python controller result:', pythonResult)
        
        return {
          success: true,
          tenant: getTenantResponseMetadata(tenant),
          result: pythonResult,
          command_id: executableCommand.command_id,
          requested_command: executionPlan.requestedCommand,
          resolved_command: executionPlan.command,
          decision_source: executionPlan.decisionSource,
          executed_at: executableCommand.timestamp,
          source_metadata: {
            tenant_filter_applied: true,
            python_script: pythonScript,
            python_script_available: true,
            execution_key: historyPersistResult.executionKey,
            execution_status: pythonResult?.success === false ? 'failed' : 'executed',
            is_reconciled: historyPersistResult.reconciled,
            reconciliation_note: historyPersistResult.reconciliationNote ?? null,
            fallback_reason_code: 'none',
            decision_snapshot_version: executionPlan.decisionSnapshot.version,
            history_execution_key: historyPersistResult.executionKey,
            optimization_history_reconciled: historyPersistResult.reconciled,
          },
          decision_snapshot: executionPlan.decisionSnapshot,
          source: 'python_controller'
        }
        
      } catch (pythonError) {
        console.warn('Python controller execution failed:', getErrorMessage(pythonError, 'Python controller execution failed'))
        fallbackReasonCode = 'python_execution_failed'
      }
    } else {
      fallbackReasonCode = 'python_script_missing'
    }
    
    // Fallback simulation for development
    console.log('Using simulation mode for command execution')

    const batteryStatus = await $fetch<any>('/api/battery/status', {
      headers: {
        'x-tenant-id': tenant.id,
      },
      query: {
        tenantId: tenant.id,
      },
    }).catch(() => null)
    const batterySoc = Number(batteryStatus?.battery?.soc ?? 50) / 100
    const batteryCapacity = Number(batteryStatus?.battery?.capacity ?? 150)
    const maxPower = 5.0

    let deltaSoc = 0
    if (executableCommand.command === 'charge' && executableCommand.power_kw > 0) {
      deltaSoc = Math.min(0.2, Math.abs(executableCommand.power_kw) / batteryCapacity)
    } else if (executableCommand.command === 'discharge' && executableCommand.power_kw < 0) {
      deltaSoc = -Math.min(0.2, Math.abs(executableCommand.power_kw) / batteryCapacity)
    }

    const newSoc = Math.max(0.05, Math.min(0.95, batterySoc + deltaSoc))
    const socDeltaKwh = Math.abs(newSoc - batterySoc) * batteryCapacity
    const powerAbs = Math.max(Math.abs(executableCommand.power_kw), 0.1)
    const derivedMinutes = Math.max(1, Math.round((socDeltaKwh / powerAbs) * 60))

    const simulationResult = {
      success: true,
      soc_before: Number(batterySoc.toFixed(4)),
      new_soc: Number(newSoc.toFixed(4)),
      power_kw: executableCommand.power_kw,
      estimated_completion: executableCommand.command === 'hold'
        ? null
        : new Date(Date.now() + (executableCommand.duration_minutes || derivedMinutes) * 60000).toISOString(),
      validation: {
        power_within_limits: Math.abs(executableCommand.power_kw) <= maxPower,
        soc_safe_for_operation: newSoc >= 0.05 && newSoc <= 0.95,
        command_accepted: true
      }
    }
    
    const historyEntry: CommandHistoryRecord & {
      execution_key: string | null
      execution_status: string
      is_reconciled: boolean
      reconciliation_note: string | null
    } = {
      ...executableCommand,
      requested_command: executionPlan.requestedCommand,
      resolved_command: executionPlan.command,
      decision_source: executionPlan.decisionSource,
      recommendation_source: executionPlan.recommendationSource,
      optimization_strategy: executionPlan.optimizationStrategy,
      load_profile_type: executionPlan.loadProfileType,
      strategy_weights: executionPlan.strategyWeights,
      execution_key: null,
      execution_status: simulationResult?.success === false ? 'failed' : 'executed',
      is_reconciled: false,
      reconciliation_note: null,
      forecast_run_id: executionPlan.lineage.forecast_run_id,
      forecast_model_version: executionPlan.lineage.forecast_model_version,
      optimization_run_id: executionPlan.lineage.optimization_run_id,
      decision_snapshot: executionPlan.decisionSnapshot,
      tenant_id: tenant.id,
      result: simulationResult,
      executed_at: new Date().toISOString(),
      success: true,
      event_type: executionPlan.eventType,
      mode_from: executionPlan.modeFrom,
      mode_to: executionPlan.modeTo,
    }

    appendCommandHistory(historyEntry)

    const historyPersistResult = await persistCommandToOptimizationHistory({
      command: executableCommand,
      executionResult: simulationResult,
      executionSource: 'simulation',
      batterySocBeforeRaw: batterySoc * 100,
      decisionSource: executionPlan.decisionSource,
      eventType: executionPlan.eventType,
      modeFrom: executionPlan.modeFrom,
      modeTo: executionPlan.modeTo,
      requestedCommand: executionPlan.requestedCommand,
      decisionSnapshot: executionPlan.decisionSnapshot,
      lineage: executionPlan.lineage,
    })

    historyEntry.execution_key = historyPersistResult.executionKey
    historyEntry.is_reconciled = historyPersistResult.reconciled
    historyEntry.reconciliation_note = historyPersistResult.reconciliationNote ?? null

    recordBillingForExecutedCommand(executableCommand, simulationResult, 'simulation', executionPlan.requestedCommand)

    setControlModeState(tenant.id, {
      mode: executionPlan.modeTo,
      requested_command: executionPlan.requestedCommand,
      active_command: executionPlan.command,
      decision_source: executionPlan.decisionSource,
      reason: executableCommand.reason,
      updated_at: new Date().toISOString(),
    })

    await updateBatteryControlState({
      powerCommand: Number(executableCommand.power_kw || 0),
      manualMode: executionPlan.modeTo !== 'automatic',
      autoOptimization: executionPlan.modeTo === 'automatic',
    }, tenant.id)

    await persistBatterySignalForCommand(executableCommand, tenant.id)
    
    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      result: simulationResult,
      command_id: executableCommand.command_id,
      requested_command: executionPlan.requestedCommand,
      resolved_command: executionPlan.command,
      decision_source: executionPlan.decisionSource,
      executed_at: executableCommand.timestamp,
      source_metadata: {
        tenant_filter_applied: true,
        python_script: pythonScript,
        python_script_available: pythonScriptAvailable,
        fallback_reason_code: fallbackReasonCode || 'python_unavailable',
        decision_snapshot_version: executionPlan.decisionSnapshot.version,
        history_execution_key: historyPersistResult.executionKey,
        optimization_history_reconciled: historyPersistResult.reconciled,
      },
      decision_snapshot: executionPlan.decisionSnapshot,
      source: 'simulation'
    }
    
  } catch (error) {
    const errorData = (error as any)?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('Command execution error:', error)
    
    if (hasStatusCode(error)) {
      throw error
    }
    
    throw createError({
      statusCode: 500,
      statusMessage: getErrorMessage(error, 'Command execution failed')
    })
  }
})

function normalizeOptionalString(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null
  }
  const normalized = value.trim()
  return normalized ? normalized : null
}

function resolveIncomingTimestamp(value: unknown): string {
  if (typeof value === 'string') {
    const parsed = new Date(value)
    if (Number.isFinite(parsed.getTime())) {
      return parsed.toISOString()
    }
  }
  return new Date().toISOString()
}

function resolveCommandId(body: any, timestampIso: string): string {
  const explicit = normalizeOptionalString(body?.command_id) || normalizeOptionalString(body?.idempotency_key)
  if (explicit) {
    return explicit
  }

  if (!(globalThis as any).__commandIdCounter) {
    ;(globalThis as any).__commandIdCounter = 0
  }
  ;(globalThis as any).__commandIdCounter += 1
  const suffix = String((globalThis as any).__commandIdCounter)
  return `cmd_${Date.parse(timestampIso)}_${suffix}`
}

function toFiniteNumber(value: unknown): number | null {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : null
}

function resolvePreviousActionForTenant(tenantId: string): 'BUY' | 'SELL' | 'HOLD' | null {
  const previousEntry = getCommandHistory().find((entry) => {
    const entryTenantId = String(entry?.tenant_id || entry?.tenantId || '')
    return entryTenantId === tenantId
  })

  if (!previousEntry) {
    return null
  }

  return mapExecutionCommandToRecommendationAction(
    normalizeExecutableCommand(previousEntry.resolved_command || previousEntry.command),
  )
}

function normalizeExecutableCommand(value: unknown): ExecutableCommand {
  if (value === 'charge' || value === 'discharge') {
    return value
  }
  return 'hold'
}

function resolveSnapshotDecisionSource(value: string): string {
  return normalizeDecisionSource(value, 'heuristic_fallback')
}

function emptyExecutionLineage(): ExecutionLineage {
  return {
    forecast_run_id: null,
    forecast_model_version: null,
    optimization_run_id: null,
  }
}

function resolveExecutionLineage(value: unknown): ExecutionLineage {
  const sourceMetadata = value && typeof value === 'object' ? value as Record<string, unknown> : {}
  return {
    forecast_run_id: normalizeOptionalString(sourceMetadata.dagster_forecast_run_id),
    forecast_model_version: normalizeOptionalString(sourceMetadata.dagster_forecast_model_version),
    optimization_run_id: normalizeOptionalString(sourceMetadata.dagster_optimization_run_id),
  }
}

function preferExecutionLineage(primary: ExecutionLineage, fallback: ExecutionLineage): ExecutionLineage {
  return {
    forecast_run_id: primary.forecast_run_id || fallback.forecast_run_id,
    forecast_model_version: primary.forecast_model_version || fallback.forecast_model_version,
    optimization_run_id: primary.optimization_run_id || fallback.optimization_run_id,
  }
}

type CommandPayload = {
  command_id: string
  schedule_id: string | null
  tenant_id: string
  command: string
  power_kw: number
  duration_minutes: number | null
  reason: string
  user_id: string
  timestamp: string
}

type PersistInput = {
  command: CommandPayload
  executionResult: any
  executionSource: 'python_controller' | 'simulation'
  batterySocBeforeRaw: unknown
  decisionSource: 'manual' | 'dagster' | 'ml' | 'heuristic'
  eventType: 'manual_command' | 'auto_transition'
  modeFrom: 'manual' | 'automatic'
  modeTo: 'manual' | 'automatic'
  requestedCommand: string
  decisionSnapshot: DecisionSnapshot
  lineage: ExecutionLineage
}

type PricingContext = {
  unitPriceUahKwh: number
  source: string
  tariffWindow: 'peak' | 'offpeak' | 'shoulder' | 'unknown'
  intervalStart: string | null
  intervalEnd: string | null
  peakPrice: number | null
  offPeakPrice: number | null
  fallbackReason: string | null
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

async function resolveCurrentPriceKwh(tenantId: string): Promise<number> {
  try {
    const payload = await $fetch<any>('/api/prices/current', {
      headers: {
        'x-tenant-id': tenantId,
      },
      query: {
        tenantId,
      },
    })
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

function resolveTariffWindowFromHour(hour: number): 'peak' | 'offpeak' | 'shoulder' | 'unknown' {
  if (!Number.isInteger(hour) || hour < 0 || hour > 23) {
    return 'unknown'
  }
  if (hour >= 8 && hour <= 20) {
    return 'peak'
  }
  if (hour === 7 || hour === 21) {
    return 'shoulder'
  }
  return 'offpeak'
}

async function resolvePricingContext(commandTimestamp: string, tenantId: string): Promise<PricingContext> {
  const defaultPrice = await resolveCurrentPriceKwh(tenantId)
  const fallback: PricingContext = {
    unitPriceUahKwh: defaultPrice,
    source: 'prices_current_fallback',
    tariffWindow: resolveTariffWindowFromHour(new Date(commandTimestamp).getHours()),
    intervalStart: commandTimestamp,
    intervalEnd: new Date(new Date(commandTimestamp).getTime() + 3600000).toISOString(),
    peakPrice: null,
    offPeakPrice: null,
    fallbackReason: 'price_payload_unavailable',
  }

  try {
    const payload = await $fetch<any>('/api/prices/current', {
      headers: {
        'x-tenant-id': tenantId,
      },
      query: {
        tenantId,
      },
    })
    const basePrice = Number(payload?.prices?.current?.price)
    const todayAvg = Number(payload?.prices?.today?.avg)
    const peakPrice = Number(payload?.prices?.forecast?.peak)
    const offPeakPrice = Number(payload?.prices?.forecast?.offPeak)

    const commandTime = new Date(commandTimestamp)
    const next24h = Array.isArray(payload?.prices?.forecast?.next24h) ? payload.prices.forecast.next24h : []

    let intervalRow: any | null = null
    let bestDistance = Number.POSITIVE_INFINITY
    for (const row of next24h) {
      const ts = new Date(row?.timestamp || 0)
      if (!Number.isFinite(ts.getTime()) || !Number.isFinite(commandTime.getTime())) {
        continue
      }
      const distance = Math.abs(ts.getTime() - commandTime.getTime())
      if (distance < bestDistance) {
        bestDistance = distance
        intervalRow = row
      }
    }

    const intervalStart = intervalRow?.timestamp ? new Date(intervalRow.timestamp).toISOString() : commandTimestamp
    const intervalStartDate = new Date(intervalStart)
    const intervalEnd = new Date(intervalStartDate.getTime() + 3600000).toISOString()
    const intervalPrice = Number(intervalRow?.price)
    const unitPriceUahKwh = Number.isFinite(intervalPrice) && intervalPrice > 0
      ? intervalPrice
      : Number.isFinite(basePrice) && basePrice > 0
        ? basePrice
        : Number.isFinite(todayAvg) && todayAvg > 0
          ? todayAvg
          : defaultPrice

    return {
      unitPriceUahKwh,
      source: String(payload?.prices?.source || 'prices_current'),
      tariffWindow: resolveTariffWindowFromHour(intervalStartDate.getHours()),
      intervalStart,
      intervalEnd,
      peakPrice: Number.isFinite(peakPrice) ? peakPrice : null,
      offPeakPrice: Number.isFinite(offPeakPrice) ? offPeakPrice : null,
      fallbackReason: null,
    }
  } catch {
    return fallback
  }
}

function computeCanonicalEconomics(command: CommandPayload, energyKwh: number, pricing: PricingContext): {
  baselineCost: number
  optimizedCost: number
  economicsMethod: string
  economicsVersion: string
  fallbackReason: string | null
} {
  const baselineRate = pricing.unitPriceUahKwh
  const baselineCost = Math.max(0, energyKwh * baselineRate)

  const peakRate = Number.isFinite(pricing.peakPrice) ? Number(pricing.peakPrice) : baselineRate
  const offPeakRate = Number.isFinite(pricing.offPeakPrice) ? Number(pricing.offPeakPrice) : baselineRate

  let optimizedRate = baselineRate

  if (command.command === 'charge') {
    optimizedRate = Math.min(baselineRate, offPeakRate)
  } else if (command.command === 'discharge') {
    const spread = Math.max(0, peakRate - offPeakRate)
    optimizedRate = Math.max(0, baselineRate - spread)
  }

  const optimizedCost = Math.max(0, energyKwh * optimizedRate)
  return {
    baselineCost,
    optimizedCost,
    economicsMethod: 'tariff_interval',
    economicsVersion: 'v2',
    fallbackReason: pricing.fallbackReason,
  }
}

async function persistCommandToOptimizationHistory(input: PersistInput): Promise<PersistOptimizationHistoryResult> {
  const command = input.command
  const executionResult = input.executionResult || {}

  const pricing = await resolvePricingContext(command.timestamp, command.tenant_id)
  const durationHours = deriveDurationHours(command, executionResult)
  const energyKwh = Math.max(0, Math.abs(Number(command.power_kw || 0)) * durationHours)
  const economics = computeCanonicalEconomics(command, energyKwh, pricing)
  const realizedCostUah = command.command === 'charge' ? energyKwh * pricing.unitPriceUahKwh : 0
  const realizedRevenueUah = command.command === 'discharge' ? energyKwh * pricing.unitPriceUahKwh : 0
  const realizedNetUah = realizedRevenueUah - realizedCostUah

  const socBefore = normalizeSocPercent(
    executionResult?.soc_before ?? executionResult?.result?.soc_before ?? input.batterySocBeforeRaw,
    50,
  )

  const socAfter = normalizeSocPercent(
    executionResult?.new_soc ?? executionResult?.result?.new_soc ?? socBefore,
    socBefore,
  )

  const executionKey = buildOptimizationExecutionKey({
    commandId: command.command_id,
    scheduleId: command.schedule_id,
    tenantId: command.tenant_id,
    timestamp: command.timestamp,
    command: command.command,
    powerKw: Number(command.power_kw || 0),
    durationMinutes: command.duration_minutes,
    userId: command.user_id,
    reason: command.reason,
    source: input.executionSource,
  })

  const persistResult = await persistOptimizationHistory({
    execution_key: executionKey,
    command_id: command.command_id,
    schedule_id: command.schedule_id,
    tenant_id: command.tenant_id,
    execution_source: input.executionSource,
    timestamp: command.timestamp,
    predicted_action: mapCommandToAction(command.command),
    actual_action: mapCommandToAction(command.command),
    cost_baseline: Number.isFinite(economics.baselineCost) ? economics.baselineCost : null,
    cost_rl: Number.isFinite(economics.optimizedCost) ? economics.optimizedCost : null,
    price_uah_kwh: Number.isFinite(pricing.unitPriceUahKwh) ? pricing.unitPriceUahKwh : null,
    duration_minutes: Number.isFinite(durationHours) ? Math.round(durationHours * 60) : null,
    energy_kwh: Number.isFinite(energyKwh) ? energyKwh : null,
    economics_method: economics.economicsMethod,
    economics_version: economics.economicsVersion,
    fallback_reason: economics.fallbackReason,
    price_source: pricing.source,
    tariff_window: pricing.tariffWindow,
    interval_start: pricing.intervalStart,
    interval_end: pricing.intervalEnd,
    battery_soc_start: Number.isFinite(socBefore) ? socBefore : null,
    battery_soc_end: Number.isFinite(socAfter) ? socAfter : null,
    solar_actual: null,
    load_actual: null,
    forecast_run_id: input.lineage.forecast_run_id,
    forecast_model_version: input.lineage.forecast_model_version,
    optimization_run_id: input.lineage.optimization_run_id,
    decision_source: input.decisionSource,
    execution_status: executionResult?.success === false ? 'failed' : 'executed',
    event_type: input.eventType,
    mode_from: input.modeFrom,
    mode_to: input.modeTo,
    realized_revenue_uah: Number.isFinite(realizedRevenueUah) ? realizedRevenueUah : null,
    realized_cost_uah: Number.isFinite(realizedCostUah) ? realizedCostUah : null,
    realized_net_uah: Number.isFinite(realizedNetUah) ? realizedNetUah : null,
    decision_snapshot: input.decisionSnapshot,
  })

  if (!persistResult.ok) {
    console.warn('[control/execute] optimization_history persist failed', {
      command_id: command.command_id,
      execution_key: executionKey,
      error: persistResult.error || 'unknown',
    })
    return persistResult
  }

  console.info('[control/execute] optimization_history persist outcome', {
    command_id: command.command_id,
    execution_key: executionKey,
    inserted: persistResult.inserted,
    updated: persistResult.updated,
  })

  return persistResult
}

function recordBillingForExecutedCommand(
  command: CommandPayload,
  executionResult: any,
  source: 'python_controller' | 'simulation',
  requestedCommand: string,
): void {
  try {
    const durationHours = deriveDurationHours(command, executionResult)
    const energyKwh = Math.max(0, Math.abs(Number(command.power_kw || 0)) * durationHours)

    recordBillingUsageEvent({
      tenantId: command.tenant_id,
      feature: 'optimization_control',
      quantity: 1,
      unit: 'command',
      occurredAt: command.timestamp,
      metadata: {
        command_id: command.command_id,
        schedule_id: command.schedule_id,
        requested_command: requestedCommand,
        command: command.command,
        source,
        power_kw: command.power_kw,
        duration_minutes: command.duration_minutes,
        estimated_energy_kwh: Number(energyKwh.toFixed(6)),
      },
    })
  } catch (error) {
    console.warn('[control/execute] failed to record billing usage event', {
      command_id: command.command_id,
      tenant_id: command.tenant_id,
      error: (error as any)?.message || 'unknown',
    })
  }
}

async function resolveExecutionPlan(
  command: CommandPayload,
  tenantId: string,
  requestedLineage: ExecutionLineage,
): Promise<ExecutionPlan> {
  const modeStateByTenant = (globalThis as any).__controlModeByTenant || {}
  const previousMode = modeStateByTenant[tenantId]?.mode === 'automatic' ? 'automatic' : 'manual'

  const tenantRequest = {
    headers: {
      'x-tenant-id': tenantId,
    },
    query: {
      tenantId,
    },
  }

  const [configPayload, pricesPayload, batteryPayload] = await Promise.all([
    $fetch<any>('/api/config/current', tenantRequest).catch(() => null),
    $fetch<any>('/api/prices/current', tenantRequest).catch(() => null),
    $fetch<any>('/api/battery/status', tenantRequest).catch(() => null),
  ])

  const optimizationStrategy = normalizeOptimizationStrategy(configPayload?.data?.optimization_strategy)
  const loadProfileType = normalizeLoadProfileType(configPayload?.data?.load_profile_type)
  const strategyWeights = buildStrategyWeights(optimizationStrategy)
  const currentPrice = Number(pricesPayload?.prices?.current?.price)
  const avgPrice = Number(pricesPayload?.prices?.today?.avg)
  const batterySocPercent = Number(batteryPayload?.battery?.soc)
  const batteryHealthPercent = Number(batteryPayload?.battery?.health)
  const batteryTempC = Number(batteryPayload?.battery?.temperature)
  const previousAction = resolvePreviousActionForTenant(tenantId)
  const sharedSnapshotBase = {
    tenant_id: tenantId,
    timestamp: command.timestamp,
    current_price_uah_kwh: toFiniteNumber(currentPrice),
    avg_price_uah_kwh: toFiniteNumber(avgPrice),
    battery_soc_percent: toFiniteNumber(batterySocPercent),
    battery_health_percent: toFiniteNumber(batteryHealthPercent),
    battery_temp_c: toFiniteNumber(batteryTempC),
    estimated_load_kw: null,
    estimated_solar_kw: null,
    optimization_strategy: optimizationStrategy,
    load_profile_type: loadProfileType,
    previous_action: previousAction,
    provenance: {
      state_source: 'simulator_backed_telemetry',
      state_source_detail: 'api/battery/status',
      telemetry_classification: 'simulated_operational_telemetry',
      recommendation_contract_version: null,
    },
  }

  if (command.command !== 'auto') {
    const normalizedPower = command.command === 'hold'
      ? 0
      : command.command === 'charge'
        ? Math.abs(command.power_kw)
        : -Math.abs(command.power_kw)
    return {
      command: command.command as ExecutableCommand,
      power_kw: normalizedPower,
      decisionSource: 'manual',
      reasoning: command.reason,
      requestedCommand: command.command,
      eventType: 'manual_command',
      modeFrom: previousMode,
      modeTo: 'manual',
      optimizationStrategy,
      loadProfileType,
      strategyWeights,
      recommendationSource: 'manual_input',
      decisionSnapshot: buildDecisionSnapshot({
        ...sharedSnapshotBase,
        decision_source: 'manual_override',
        recommendation_source: 'manual_input',
        selected_action: mapExecutionCommandToRecommendationAction(command.command as ExecutableCommand),
        selected_power_kw: normalizedPower,
      }),
      lineage: requestedLineage,
    }
  }

  const fallbackPowerKw = Math.max(0.5, Math.min(5, Math.abs(Number(command.power_kw || 2.5))))
  const strategyContext = {
    optimizationStrategy,
    loadProfileType,
    currentHour: new Date().getHours(),
    currentPriceUahKwh: Number.isFinite(currentPrice) ? currentPrice : null,
    avgPriceUahKwh: Number.isFinite(avgPrice) ? avgPrice : null,
    batterySocPercent: Number.isFinite(batterySocPercent) ? batterySocPercent : null,
    fallbackPowerKw,
  }

  try {
    // Auto execution resolves against the Dagster-backed recommendation first.
    // The live ML route remains the explicit fallback when the Dagster path is unavailable.
    const dagsterRecommendation = await $fetch<any>('/api/dagster/recommendation', tenantRequest)
    const dagsterLineage = preferExecutionLineage(
      resolveExecutionLineage(dagsterRecommendation?.source_metadata),
      requestedLineage,
    )
    const mapped = mapRecommendationActionToExecution(dagsterRecommendation?.recommendation?.action || 'HOLD', fallbackPowerKw)
    const adjusted = applyAutoStrategyDecision(mapped.command, mapped.power_kw, strategyContext)
    const source = String(dagsterRecommendation?.source_metadata?.recommendation_source || '')
    const baseReason = dagsterRecommendation?.recommendation?.rationale || 'Auto execution from Dagster recommendation'
    const strategyNote = adjusted.notes.length > 0
      ? ` Strategy adjustments: ${adjusted.notes.join('; ')}.`
      : ''
    return {
      command: adjusted.command,
      power_kw: adjusted.powerKw,
      decisionSource: source.startsWith('dagster') ? 'dagster' : 'ml',
      reasoning: `${baseReason}${strategyNote}`,
      requestedCommand: 'auto',
      eventType: 'auto_transition',
      modeFrom: previousMode,
      modeTo: 'automatic',
      optimizationStrategy,
      loadProfileType,
      strategyWeights,
      recommendationSource: source || 'dagster_recommendation',
      decisionSnapshot: buildDecisionSnapshot({
        ...sharedSnapshotBase,
        decision_source: resolveSnapshotDecisionSource(dagsterRecommendation?.provenance?.decision_source || source || 'dagster_optimizer'),
        recommendation_source:
          dagsterRecommendation?.source_metadata?.recommendation_source_detail
          || dagsterRecommendation?.source_metadata?.recommendation_source
          || source
          || 'dagster_recommendation',
        selected_action: mapExecutionCommandToRecommendationAction(adjusted.command),
        selected_power_kw: adjusted.powerKw,
        fallback_reason: dagsterRecommendation?.provenance?.fallback_reason_code,
        provenance: {
          state_source: dagsterRecommendation?.provenance?.state_source || sharedSnapshotBase.provenance.state_source,
          state_source_detail: dagsterRecommendation?.provenance?.state_source_detail || sharedSnapshotBase.provenance.state_source_detail,
          telemetry_classification:
            dagsterRecommendation?.provenance?.telemetry_classification
            || sharedSnapshotBase.provenance.telemetry_classification,
          recommendation_contract_version: dagsterRecommendation?.contract?.version || null,
        },
        contract: {
          version: dagsterRecommendation?.contract?.version || null,
          normalized_action:
            dagsterRecommendation?.contract?.normalized_action
            || dagsterRecommendation?.recommendation?.normalized_action
            || null,
          compliance:
            dagsterRecommendation?.contract?.compliance
            || dagsterRecommendation?.recommendation?.policy_compliance
            || null,
        },
      }),
      lineage: dagsterLineage,
    }
  } catch {
    try {
      const mlRecommendation = await $fetch<any>('/api/ml/recommendation', tenantRequest)
      const mapped = mapRecommendationActionToExecution(mlRecommendation?.data?.action || 'HOLD', fallbackPowerKw)
      const adjusted = applyAutoStrategyDecision(mapped.command, mapped.power_kw, strategyContext)
      const baseReason = mlRecommendation?.data?.reasoning || 'Auto execution from ML recommendation'
      const strategyNote = adjusted.notes.length > 0
        ? ` Strategy adjustments: ${adjusted.notes.join('; ')}.`
        : ''
      return {
        command: adjusted.command,
        power_kw: adjusted.powerKw,
        decisionSource: 'ml',
        reasoning: `${baseReason}${strategyNote}`,
        requestedCommand: 'auto',
        eventType: 'auto_transition',
        modeFrom: previousMode,
        modeTo: 'automatic',
        optimizationStrategy,
        loadProfileType,
        strategyWeights,
        recommendationSource: 'ml_recommendation',
        decisionSnapshot: buildDecisionSnapshot({
          ...sharedSnapshotBase,
          decision_source: resolveSnapshotDecisionSource(
            mlRecommendation?.data?.provenance?.decision_source
            || mlRecommendation?.contract?.provenance?.decision_source
            || 'ml_recommendation',
          ),
          recommendation_source: 'ml_recommendation',
          selected_action: mapExecutionCommandToRecommendationAction(adjusted.command),
          selected_power_kw: adjusted.powerKw,
          fallback_reason:
            mlRecommendation?.data?.provenance?.fallback_reason_code
            || mlRecommendation?.contract?.provenance?.fallback_reason_code,
          provenance: {
            state_source:
              mlRecommendation?.data?.provenance?.state_source
              || mlRecommendation?.contract?.provenance?.state_source
              || sharedSnapshotBase.provenance.state_source,
            state_source_detail:
              mlRecommendation?.data?.provenance?.state_source_detail
              || mlRecommendation?.contract?.provenance?.state_source_detail
              || sharedSnapshotBase.provenance.state_source_detail,
            telemetry_classification:
              mlRecommendation?.data?.provenance?.telemetry_classification
              || mlRecommendation?.contract?.provenance?.telemetry_classification
              || sharedSnapshotBase.provenance.telemetry_classification,
            recommendation_contract_version: mlRecommendation?.contract?.version || null,
          },
          contract: {
            version: mlRecommendation?.contract?.version || null,
            normalized_action:
              mlRecommendation?.contract?.normalized_action
              || mlRecommendation?.data?.normalized_action
              || null,
            compliance:
              mlRecommendation?.contract?.compliance
              || mlRecommendation?.data?.policy_compliance
              || null,
          },
        }),
        lineage: emptyExecutionLineage(),
      }
    } catch {
      const pricesPayload = await $fetch<any>('/api/prices/current', tenantRequest).catch(() => null)
      const current = Number(pricesPayload?.prices?.current?.price || 0)
      const avg = Number(pricesPayload?.prices?.today?.avg || 0)
      const heuristicAction = avg > 0 && current < avg * 0.9 ? 'BUY' : avg > 0 && current > avg * 1.1 ? 'SELL' : 'HOLD'
      const mapped = mapRecommendationActionToExecution(heuristicAction, fallbackPowerKw)
      const adjusted = applyAutoStrategyDecision(mapped.command, mapped.power_kw, strategyContext)
      const strategyNote = adjusted.notes.length > 0
        ? ` Strategy adjustments: ${adjusted.notes.join('; ')}.`
        : ''
      return {
        command: adjusted.command,
        power_kw: adjusted.powerKw,
        decisionSource: 'heuristic',
        reasoning: `Auto execution from heuristic fallback (price spread threshold).${strategyNote}`,
        requestedCommand: 'auto',
        eventType: 'auto_transition',
        modeFrom: previousMode,
        modeTo: 'automatic',
        optimizationStrategy,
        loadProfileType,
        strategyWeights,
        recommendationSource: 'heuristic_fallback',
        decisionSnapshot: buildDecisionSnapshot({
          ...sharedSnapshotBase,
          decision_source: 'heuristic_fallback',
          recommendation_source: 'heuristic_fallback',
          selected_action: mapExecutionCommandToRecommendationAction(adjusted.command),
          selected_power_kw: adjusted.powerKw,
          fallback_reason: 'heuristic_price_threshold',
        }),
        lineage: emptyExecutionLineage(),
      }
    }
  }
}

async function persistBatterySignalForCommand(command: CommandPayload, tenantId: string): Promise<void> {
  try {
    const voltage = 400
    const powerKw = command.command === 'hold' ? 0 : Number(command.power_kw || 0)
    const current = voltage > 0 ? (powerKw * 1000) / voltage : 0

    await updateBatteryState({
      current: Number(current.toFixed(3)),
      temperature: Number((24 + Math.min(12, Math.abs(current) / 12)).toFixed(1)),
    }, tenantId)
  } catch (error) {
    console.warn('[control/execute] failed to persist battery command signal', {
      tenant_id: tenantId,
      command_id: command.command_id,
      error: (error as any)?.message || 'unknown',
    })
  }
}

function appendCommandHistory(entry: CommandHistoryRecord): void {
  const nextHistory = [entry, ...getCommandHistory()].slice(0, 200)
  setCommandHistory(nextHistory)
}
// Control API - Schedule Management Endpoint
// POST /api/control/schedule

import { createError, defineEventHandler, readBody } from 'h3'
import { recordBillingUsageEvent } from '../../utils/billing'
import {
  buildDecisionSnapshot,
  buildOptimizationExecutionKey,
  type DecisionSnapshot,
  persistOptimizationHistory,
} from '../../utils/optimization-history'
import { ensureScheduledCommands, getCommandHistory, getErrorMessage, hasStatusCode, setScheduledCommands, type ScheduledCommandRecord } from '../../utils/control-memory'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

type ScheduledIntent = ScheduledCommandRecord & {
  id: string
  command_id: string
  tenant_id: string
  command: string
  power_kw: number
  scheduled_time: string
  reason: string
  user_id: string
  created_at: string
  status: 'pending'
  decision_snapshot?: DecisionSnapshot | null
}

export default defineEventHandler(async (event: any) => {
  try {
    const body = await readBody(event)
    const tenant = await resolveTenantContext(event, { body })
    const pythonScript = 'create_schedule.py'
    let fallbackReasonCode: string | null = null
    
    // Validate input
    if (!body.command || body.power_kw == null || !body.scheduled_time) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Command, power_kw, and scheduled_time are required'
      })
    }
    
    if (!['charge', 'discharge', 'hold'].includes(body.command)) {
      throw createError({
        statusCode: 400, 
        statusMessage: 'Invalid command. Must be: charge, discharge, or hold'
      })
    }
    
    // Validate scheduled time is in the future
    const scheduledTime = new Date(body.scheduled_time)
    const now = new Date()
    
    if (scheduledTime <= now) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Scheduled time must be in the future'
      })
    }
    
    if (scheduledTime > new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Cannot schedule more than 7 days in advance'
      })
    }
    
    const scheduleId = resolveScheduleId(body)
    const schedule: ScheduledIntent = {
      id: scheduleId,
      command_id: normalizeOptionalString(body.command_id) || `cmd_for_${scheduleId}`,
      tenant_id: tenant.id,
      command: body.command,
      power_kw: parseFloat(body.power_kw),
      scheduled_time: scheduledTime.toISOString(),
      reason: body.reason || `Scheduled ${body.command}`,
      user_id: body.user_id || 'dashboard',
      created_at: new Date().toISOString(),
      status: 'pending'
    }
    const decisionSnapshot = await buildScheduledIntentDecisionSnapshot(schedule, tenant.id)
    schedule.decision_snapshot = decisionSnapshot
    
    console.log('Creating schedule:', schedule)
    
    // Try to schedule via Python controller
    const pythonRunner: any = await import('../../utils/python-runner.js').catch(() => ({ execPython: null, hasPythonScript: null }))
    const execPython = pythonRunner?.execPython
    const hasPythonScript = pythonRunner?.hasPythonScript
    const pythonScriptAvailable = Boolean(execPython && hasPythonScript && hasPythonScript(pythonScript))
    
    if (pythonScriptAvailable && execPython) {
      try {
        const result = await (execPython as any)(pythonScript, {
          command: schedule.command,
          power_kw: schedule.power_kw.toString(),
          scheduled_time: schedule.scheduled_time,
          reason: schedule.reason,
          user_id: schedule.user_id,
          tenant_id: tenant.id,
        })
        
        const pythonResult = JSON.parse(result)
        
        await persistScheduledIntent(schedule, 'python_controller')
        recordBillingForScheduledIntent(schedule, 'python_controller')

        return {
          success: true,
          tenant: getTenantResponseMetadata(tenant),
          schedule_id: schedule.id,
          command_id: schedule.command_id,
          scheduled_time: schedule.scheduled_time,
          result: pythonResult,
          source_metadata: {
            tenant_filter_applied: true,
            python_script: pythonScript,
            python_script_available: true,
            fallback_reason_code: 'none',
            decision_snapshot_version: decisionSnapshot.version,
          },
          decision_snapshot: decisionSnapshot,
          source: 'python_controller'
        }
        
      } catch (pythonError: any) {
        console.warn('Python controller scheduling failed:', pythonError.message)
        fallbackReasonCode = 'python_execution_failed'
      }
    } else {
      fallbackReasonCode = 'python_script_missing'
    }
    
    // Fallback to in-memory storage
    const schedules = ensureScheduledCommands()
    schedules.push(schedule)
    
    // Keep only future schedules (cleanup old ones)
    setScheduledCommands(schedules.filter(
      cmd => resolveScheduledTimeMs(cmd.scheduled_time) > Date.now() || cmd.status === 'pending'
    ))
    
    await persistScheduledIntent(schedule, 'memory_storage')
    recordBillingForScheduledIntent(schedule, 'memory_storage')

    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      schedule_id: schedule.id,
      command_id: schedule.command_id,
      scheduled_time: schedule.scheduled_time,
      message: 'Command scheduled successfully',
      source_metadata: {
        tenant_filter_applied: true,
        python_script: pythonScript,
        python_script_available: pythonScriptAvailable,
        fallback_reason_code: fallbackReasonCode || 'python_unavailable',
        decision_snapshot_version: decisionSnapshot.version,
      },
      decision_snapshot: decisionSnapshot,
      source: 'memory_storage'
    }
    
  } catch (error: any) {
    const errorData = error?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('Schedule creation error:', error)
    
    if (error.statusCode) {
      throw error
    }
    
    throw createError({
      statusCode: 500,
      statusMessage: error.message || 'Schedule creation failed'
    })
  }
})

function generateScheduleId() {
  if (!(globalThis as any).__scheduleIdCounter) {
    ;(globalThis as any).__scheduleIdCounter = 0
  }
  ;(globalThis as any).__scheduleIdCounter += 1
  return `sched_${Date.now()}_${(globalThis as any).__scheduleIdCounter}`
}

function normalizeOptionalString(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null
  }
  const normalized = value.trim()
  return normalized ? normalized : null
}

function resolveScheduleId(body: any): string {
  const explicit = normalizeOptionalString(body?.schedule_id) || normalizeOptionalString(body?.idempotency_key)
  if (explicit) {
    return explicit
  }
  return generateScheduleId()
}

function toFiniteNumber(value: unknown): number | null {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : null
}

function mapCommandToSnapshotAction(command: string): 'BUY' | 'SELL' | 'HOLD' {
  if (command === 'charge') {
    return 'BUY'
  }
  if (command === 'discharge') {
    return 'SELL'
  }
  return 'HOLD'
}

function resolvePreviousActionForTenant(tenantId: string): 'BUY' | 'SELL' | 'HOLD' | null {
  const history = getCommandHistory()
  const previousEntry = history.find(entry => {
    const entryTenantId = String(entry?.tenant_id || entry?.tenantId || '')
    return entryTenantId === tenantId
  })

  if (!previousEntry) {
    return null
  }

  return mapCommandToSnapshotAction(previousEntry.resolved_command || previousEntry.command || 'hold')
}

function resolveScheduledTimeMs(value: string | null | undefined): number {
  const parsed = new Date(value || 0).getTime()
  return Number.isFinite(parsed) ? parsed : 0
}

function mapCommandToAction(command: string): number {
  switch (command) {
    case 'charge':
      return 0
    case 'discharge':
      return 1
    case 'hold':
      return 4
    default:
      return 4
  }
}

async function buildScheduledIntentDecisionSnapshot(schedule: any, tenantId: string): Promise<DecisionSnapshot> {
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

  return buildDecisionSnapshot({
    tenant_id: tenantId,
    timestamp: schedule.created_at,
    decision_source: 'manual_override',
    recommendation_source: 'manual_input',
    selected_action: mapCommandToSnapshotAction(String(schedule.command || 'hold')),
    selected_power_kw: toFiniteNumber(schedule.power_kw),
    current_price_uah_kwh: toFiniteNumber(pricesPayload?.prices?.current?.price),
    avg_price_uah_kwh: toFiniteNumber(pricesPayload?.prices?.today?.avg),
    battery_soc_percent: toFiniteNumber(batteryPayload?.battery?.soc),
    battery_health_percent: toFiniteNumber(batteryPayload?.battery?.health),
    battery_temp_c: toFiniteNumber(batteryPayload?.battery?.temperature),
    estimated_load_kw: null,
    estimated_solar_kw: null,
    optimization_strategy: configPayload?.data?.optimization_strategy,
    load_profile_type: configPayload?.data?.load_profile_type,
    fallback_reason: null,
    previous_action: resolvePreviousActionForTenant(tenantId),
    provenance: {
      state_source: 'simulator_backed_telemetry',
      state_source_detail: 'api/battery/status',
      telemetry_classification: 'simulated_operational_telemetry',
      recommendation_contract_version: null,
    },
  })
}

async function persistScheduledIntent(schedule: any, source: 'python_controller' | 'memory_storage'): Promise<void> {
  const executionSource = source === 'python_controller' ? 'python_schedule_intent' : 'memory_schedule_intent'
  const executionKey = buildOptimizationExecutionKey({
    commandId: schedule.command_id,
    scheduleId: schedule.id,
    tenantId: schedule.tenant_id,
    timestamp: schedule.scheduled_time,
    command: schedule.command,
    powerKw: Number(schedule.power_kw || 0),
    durationMinutes: null,
    userId: schedule.user_id || 'dashboard',
    reason: schedule.reason || '',
    source: executionSource,
  })

  const result = await persistOptimizationHistory({
    execution_key: executionKey,
    command_id: schedule.command_id,
    schedule_id: schedule.id,
    tenant_id: schedule.tenant_id,
    execution_source: executionSource,
    timestamp: schedule.scheduled_time,
    predicted_action: mapCommandToAction(schedule.command),
    actual_action: null,
    cost_baseline: null,
    cost_rl: null,
    price_uah_kwh: null,
    duration_minutes: null,
    energy_kwh: null,
    economics_method: 'scheduled_intent',
    economics_version: 'v1',
    fallback_reason: 'scheduled_intent_only',
    price_source: null,
    tariff_window: null,
    interval_start: schedule.scheduled_time,
    interval_end: null,
    battery_soc_start: null,
    battery_soc_end: null,
    solar_actual: null,
    load_actual: null,
    decision_source: 'manual',
    execution_status: 'scheduled',
    event_type: 'scheduled_intent',
    mode_from: null,
    mode_to: null,
    realized_revenue_uah: null,
    realized_cost_uah: null,
    realized_net_uah: null,
    decision_snapshot: schedule.decision_snapshot || null,
  })

  if (!result.ok) {
    console.warn('[control/schedule] failed to persist scheduled intent', {
      schedule_id: schedule.id,
      command_id: schedule.command_id,
      execution_key: executionKey,
      error: result.error || 'unknown',
    })
  }
}

function recordBillingForScheduledIntent(
  schedule: any,
  source: 'python_controller' | 'memory_storage',
): void {
  try {
    recordBillingUsageEvent({
      tenantId: String(schedule.tenant_id || ''),
      feature: 'scheduled_control',
      quantity: 1,
      unit: 'command',
      occurredAt: String(schedule.created_at || new Date().toISOString()),
      metadata: {
        schedule_id: schedule.id,
        command_id: schedule.command_id,
        command: schedule.command,
        source,
        power_kw: Number(schedule.power_kw || 0),
        scheduled_time: schedule.scheduled_time,
      },
    })
  } catch (error) {
    console.warn('[control/schedule] failed to record billing usage event', {
      schedule_id: schedule?.id,
      tenant_id: schedule?.tenant_id,
      error: (error as any)?.message || 'unknown',
    })
  }
}
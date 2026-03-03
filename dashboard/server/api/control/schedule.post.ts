// Control API - Schedule Management Endpoint
// POST /api/control/schedule

import { createError, defineEventHandler, readBody } from 'h3'
import { buildOptimizationExecutionKey, persistOptimizationHistory } from '../../utils/optimization-history'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

export default defineEventHandler(async (event: any) => {
  try {
    const body = await readBody(event)
    const tenant = await resolveTenantContext(event, { body })
    
    // Validate input
    if (!body.command || !body.power_kw || !body.scheduled_time) {
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
    const schedule = {
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
    
    console.log('Creating schedule:', schedule)
    
    // Try to schedule via Python controller
    const { execPython } = await import('../../../utils/python-runner.js').catch(() => ({ execPython: null }))
    
    if (execPython) {
      try {
        const result = await (execPython as any)('create_schedule.py', {
          command: schedule.command,
          power_kw: schedule.power_kw.toString(),
          scheduled_time: schedule.scheduled_time,
          reason: schedule.reason,
          user_id: schedule.user_id,
          tenant_id: tenant.id,
        })
        
        const pythonResult = JSON.parse(result)
        
        await persistScheduledIntent(schedule, 'python_controller')

        return {
          success: true,
          tenant: getTenantResponseMetadata(tenant),
          schedule_id: schedule.id,
          command_id: schedule.command_id,
          scheduled_time: schedule.scheduled_time,
          result: pythonResult,
          source: 'python_controller'
        }
        
      } catch (pythonError: any) {
        console.warn('Python controller scheduling failed:', pythonError.message)
      }
    }
    
    // Fallback to in-memory storage
    if (!(globalThis as any).scheduledCommands) {
      ;(globalThis as any).scheduledCommands = []
    }
    
    ;(globalThis as any).scheduledCommands.push(schedule)
    
    // Keep only future schedules (cleanup old ones)
    ;(globalThis as any).scheduledCommands = (globalThis as any).scheduledCommands.filter(
      (cmd: any) => new Date(cmd.scheduled_time) > new Date() || cmd.status === 'pending'
    )
    
    await persistScheduledIntent(schedule, 'memory_storage')

    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      schedule_id: schedule.id,
      command_id: schedule.command_id,
      scheduled_time: schedule.scheduled_time,
      message: 'Command scheduled successfully',
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
// Control API - Command History Endpoint
// GET /api/control/history

import { buildOptimizationExecutionKey, persistOptimizationHistory } from '../../utils/optimization-history'
import { getTenantResponseMetadata, isRecordVisibleForTenant, resolveTenantContext, type TenantContext } from '../../utils/tenant-context'

export default defineEventHandler(async (event) => {
  try {
    const tenant = await resolveTenantContext(event)
    const query = getQuery(event)
    const limit = Math.min(parseInt(query.limit as string) || 50, 100)
    const sinceHours = Math.max(1, Math.min(parseInt(query.since_hours as string) || 24, 24 * 7))
    const sinceTs = Date.now() - sinceHours * 60 * 60 * 1000
    const pythonScript = 'get_control_history.py'
    let fallbackReasonCode: string | null = null
    
    // Try to get history from Python controller
    const pythonRunner: any = await import('../../utils/python-runner.js').catch(() => ({ execPython: null, hasPythonScript: null }))
    const execPython = pythonRunner?.execPython
    const hasPythonScript = pythonRunner?.hasPythonScript
    const pythonScriptAvailable = Boolean(execPython && hasPythonScript && hasPythonScript(pythonScript))
    
    if (pythonScriptAvailable && execPython) {
      try {
        const result = await execPython(pythonScript, {
          limit: limit.toString(),
          tenant_id: tenant.id,
        })
        const pythonHistory = JSON.parse(result)
        const normalized = normalizeHistoryEntries(
          Array.isArray(pythonHistory) ? pythonHistory : [],
          'python_controller',
          tenant,
        )
        const filtered = normalized.filter((entry: any) => {
          const ts = new Date(entry?.timestamp || 0).getTime()
          return Number.isFinite(ts) ? ts >= sinceTs : false
        }).slice(0, limit)

        await persistHistoryRows(filtered, 'python_controller_history')
        
        return {
          success: true,
          tenant: getTenantResponseMetadata(tenant),
          history: filtered,
          count: filtered.length,
          source_metadata: {
            tenant_filter_applied: true,
            python_script: pythonScript,
            python_script_available: true,
            fallback_reason_code: 'none',
          },
          source: 'python_controller'
        }
        
      } catch (pythonError) {
        console.warn('Python controller history not available:', pythonError.message)
        fallbackReasonCode = 'python_execution_failed'
      }
    } else {
      fallbackReasonCode = 'python_script_missing'
    }

    // Deterministic fallback to in-memory history.
    const history = Array.isArray(globalThis.commandHistory) ? globalThis.commandHistory : []
    
    // Apply limit
    const filteredHistory = history.filter((entry: any) => {
      const ts = new Date(entry?.timestamp || entry?.executed_at || 0).getTime()
      return Number.isFinite(ts) ? ts >= sinceTs : false
    })
    const limitedHistory = filteredHistory.slice(0, limit)
    const apiHistory = normalizeHistoryEntries(limitedHistory, 'memory_storage', tenant)

    await persistHistoryRows(apiHistory, 'memory_history')
    
    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      history: apiHistory,
      count: apiHistory.length,
      source_metadata: {
        tenant_filter_applied: true,
        python_script: pythonScript,
        python_script_available: pythonScriptAvailable,
        fallback_reason_code: fallbackReasonCode || 'python_unavailable',
      },
      source: 'memory_storage'
    }
    
  } catch (error) {
    const errorData = (error as any)?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('History endpoint error:', error)
    
    return {
      success: false,
      error: error.message,
      history: [],
      count: 0,
      source: 'error_fallback'
    }
  }
})

function normalizeOptionalString(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null
  }
  const normalized = value.trim()
  return normalized ? normalized : null
}

function normalizeTimestamp(value: unknown): string {
  if (typeof value === 'string') {
    const parsed = new Date(value)
    if (Number.isFinite(parsed.getTime())) {
      return parsed.toISOString()
    }
  }
  return new Date().toISOString()
}

function normalizeSocPercent(value: unknown, fallback = 0.5): number {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) {
    return fallback
  }
  if (numeric > 1) {
    return numeric / 100
  }
  if (numeric < 0) {
    return fallback
  }
  return numeric
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

function normalizeHistoryEntries(
  entries: any[],
  source: 'python_controller' | 'memory_storage',
  tenant: TenantContext,
): any[] {
  return entries
  .filter((entry: any) => isRecordVisibleForTenant(entry?.tenant_id ?? entry?.tenantId, tenant))
  .map((entry: any) => {
    const timestamp = normalizeTimestamp(entry?.timestamp || entry?.executed_at)
    const command = String(entry?.command || 'hold').toLowerCase()
    const powerKw = Number(entry?.power_kw ?? 0)
    const reason = String(entry?.reason || `history:${source}`)
    const userId = String(entry?.user_id || 'system')
    const commandId = normalizeOptionalString(entry?.command_id)
      || normalizeOptionalString(entry?.id)
      || buildHistoryCommandId({ timestamp, command, powerKw, userId, source })
    const scheduleId = normalizeOptionalString(entry?.schedule_id)

    const socBefore = normalizeSocPercent(entry?.result?.soc_before ?? entry?.soc_before ?? 0.5)
    const socAfter = normalizeSocPercent(entry?.result?.new_soc ?? entry?.soc_after ?? socBefore, socBefore)
    const strategyWeights = entry?.strategy_weights && typeof entry.strategy_weights === 'object'
      ? entry.strategy_weights
      : null

    return {
      command_id: commandId,
      schedule_id: scheduleId,
      tenant_id: tenant.id,
      timestamp,
      command,
      requested_command: normalizeOptionalString(entry?.requested_command) || command,
      resolved_command: normalizeOptionalString(entry?.resolved_command) || command,
      power_kw: Number.isFinite(powerKw) ? powerKw : 0,
      reason,
      user_id: userId,
      soc_before: socBefore,
      soc_after: socAfter,
      decision_source: normalizeOptionalString(entry?.decision_source),
      recommendation_source: normalizeOptionalString(entry?.recommendation_source),
      optimization_strategy: normalizeOptionalString(entry?.optimization_strategy),
      load_profile_type: normalizeOptionalString(entry?.load_profile_type),
      strategy_weights: strategyWeights,
      event_type: normalizeOptionalString(entry?.event_type),
      mode_from: normalizeOptionalString(entry?.mode_from),
      mode_to: normalizeOptionalString(entry?.mode_to),
      success: entry?.success !== false,
      estimated_completion: entry?.result?.estimated_completion ?? entry?.estimated_completion ?? null,
    }
  })
}

function buildHistoryCommandId(input: {
  timestamp: string
  command: string
  powerKw: number
  userId: string
  source: string
}): string {
  const ts = Date.parse(input.timestamp)
  const normalizedTs = Number.isFinite(ts) ? ts : Date.now()
  return `hist_${input.source}_${normalizedTs}_${input.command}_${Math.round(input.powerKw * 100)}`
}

async function persistHistoryRows(rows: any[], source: 'python_controller_history' | 'memory_history'): Promise<void> {
  for (const row of rows) {
    const executionKey = buildOptimizationExecutionKey({
      commandId: row.command_id,
      scheduleId: row.schedule_id,
      tenantId: row.tenant_id,
      timestamp: row.timestamp,
      command: row.command,
      powerKw: Number(row.power_kw || 0),
      durationMinutes: null,
      userId: row.user_id || 'system',
      reason: row.reason || '',
      source,
    })

    await persistOptimizationHistory({
      execution_key: executionKey,
      command_id: row.command_id,
      schedule_id: row.schedule_id,
      tenant_id: row.tenant_id,
      execution_source: source,
      timestamp: row.timestamp,
      predicted_action: mapCommandToAction(row.command),
      actual_action: row.success ? mapCommandToAction(row.command) : null,
      cost_baseline: null,
      cost_rl: null,
      price_uah_kwh: null,
      duration_minutes: null,
      energy_kwh: null,
      economics_method: 'history_backfill_stub',
      economics_version: 'v1',
      fallback_reason: 'missing_economics_payload',
      price_source: null,
      tariff_window: null,
      interval_start: row.timestamp,
      interval_end: row.estimated_completion,
      battery_soc_start: Number.isFinite(row.soc_before) ? row.soc_before * 100 : null,
      battery_soc_end: Number.isFinite(row.soc_after) ? row.soc_after * 100 : null,
      solar_actual: null,
      load_actual: null,
      decision_source: row.decision_source || 'manual',
      execution_status: row.success ? 'executed' : 'failed',
      event_type: row.event_type || 'history_sync',
      mode_from: row.mode_from || null,
      mode_to: row.mode_to || null,
      realized_revenue_uah: null,
      realized_cost_uah: null,
      realized_net_uah: null,
    })
  }
}

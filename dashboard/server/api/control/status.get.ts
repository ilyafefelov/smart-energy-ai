// Control API - System Status Endpoint
// GET /api/control/status

import { buildDecisionProvenance, normalizeDecisionSource } from '../../utils/recommendation-contract'
import { getCommandHistory, getControlModeState, getErrorMessage, getScheduledCommands, type CommandHistoryRecord } from '../../utils/control-memory'
import { getTenantResponseMetadata, isRecordVisibleForTenant, resolveTenantContext } from '../../utils/tenant-context'
import { getBatteryControlState } from '../../utils/battery-control-state'

type BatteryStatusPayload = {
  battery?: {
    soc?: number | null
    power?: number | null
    capacity?: number | null
    lastUpdated?: string | null
  } | null
}

function deriveCommandFromPower(powerKw: number): 'charge' | 'discharge' | 'hold' {
  if (powerKw > 0.05) return 'charge'
  if (powerKw < -0.05) return 'discharge'
  return 'hold'
}

export default defineEventHandler(async (event): Promise<Record<string, unknown>> => {
  try {
    const tenant = await resolveTenantContext(event, { requireTrustedOverride: true })
    const pythonScript = 'get_control_status.py'
    let fallbackReasonCode: string | null = null
    // Import the Python control system
    const pythonRunner: any = await import('../../utils/python-runner.js').catch(() => ({ execPython: null, hasPythonScript: null }))
    const execPython = pythonRunner?.execPython
    const hasPythonScript = pythonRunner?.hasPythonScript
    const pythonScriptAvailable = Boolean(execPython && hasPythonScript && hasPythonScript(pythonScript))
    const controlModeState = getControlModeState(tenant.id)
    const persistedControl = await getBatteryControlState(tenant.id).catch(() => null)
    const persistedModeState = persistedControl
      ? {
          mode: persistedControl.manualMode ? 'manual' : 'automatic',
          active_command: deriveCommandFromPower(Number(persistedControl.powerCommand || 0)),
          requested_command: persistedControl.manualMode ? deriveCommandFromPower(Number(persistedControl.powerCommand || 0)) : 'auto',
          decision_source: normalizeDecisionSource(persistedControl.manualMode ? 'manual_override' : 'dagster_optimizer'),
          reason: 'Persisted control state fallback',
          updated_at: persistedControl.updatedAt,
        }
      : null
    const effectiveModeState = controlModeState || persistedModeState
    
    if (pythonScriptAvailable && execPython) {
      // Try to get status from Python controller
      try {
        const result = await execPython(pythonScript)
        const pythonStatus = JSON.parse(result)
        const decisionSource = normalizeDecisionSource(
          effectiveModeState?.decision_source || pythonStatus?.decision_source || 'python_rule_engine',
          'python_rule_engine',
        )
        const provenance = buildDecisionProvenance({
          decisionSource,
          fallbackReasonCode: 'none',
          stateSource: 'simulator_backed_telemetry',
          stateSourceDetail: 'battery_control_state',
        })
        
        return {
          success: true,
          tenant: getTenantResponseMetadata(tenant),
          ...pythonStatus,
          mode: effectiveModeState?.mode || pythonStatus?.mode || 'automatic',
          active_command: effectiveModeState?.active_command || pythonStatus?.active_command || null,
          requested_command: effectiveModeState?.requested_command || pythonStatus?.requested_command || pythonStatus?.active_command || null,
          decision_source: decisionSource,
          command_reason: effectiveModeState?.reason || pythonStatus?.command_reason || null,
          last_update: effectiveModeState?.updated_at || pythonStatus?.last_update || new Date().toISOString(),
          provenance,
          source_metadata: {
            tenant_filter_applied: true,
            python_script: pythonScript,
            python_script_available: true,
            fallback_reason_code: provenance.fallback_reason_code,
            decision_source: provenance.decision_source,
            state_source: provenance.state_source,
            telemetry_classification: provenance.telemetry_classification,
            mode_state_overlay_applied: Boolean(effectiveModeState),
          },
          source: 'python_controller'
        }
      } catch (pythonError) {
        console.warn('Python controller not available:', getErrorMessage(pythonError, 'Python controller not available'))
        fallbackReasonCode = 'python_execution_failed'
      }
    } else {
      fallbackReasonCode = 'python_script_missing'
    }

    // Deterministic fallback from persisted battery state and command memory.
    const batteryStatus = await $fetch<BatteryStatusPayload>('/api/battery/status', {
      headers: {
        'x-tenant-id': tenant.id,
      },
      query: {
        tenantId: tenant.id,
      },
    }).catch(() => null)

    const battery = batteryStatus?.battery ?? {}
    const schedules = getScheduledCommands()
      .filter(cmd => isRecordVisibleForTenant(cmd?.tenant_id ?? cmd?.tenantId, tenant))
    const now = Date.now()
    const pendingSchedules = schedules.filter(cmd => {
      return cmd?.status === 'pending' && resolveScheduledTimeMs(cmd?.scheduled_time) > now
    })

    const history = getCommandHistory()
      .filter(entry => isRecordVisibleForTenant(entry?.tenant_id ?? entry?.tenantId, tenant))
    const lastCommand = history[0] || null
    const lastCommandTs = resolveCommandTimestamp(lastCommand)
    const isRecentCommand = lastCommandTs > 0 && now - lastCommandTs <= 6 * 60 * 60 * 1000
    const recentCommand = isRecentCommand ? lastCommand : null

    const activeCommand = effectiveModeState?.active_command || recentCommand?.command || null
    const requestedCommand = effectiveModeState?.requested_command || recentCommand?.requested_command || recentCommand?.command || null
    const mode = effectiveModeState?.mode || (activeCommand ? 'manual' : 'automatic')
    const decisionSource = normalizeDecisionSource(
      effectiveModeState?.decision_source || recentCommand?.decision_source || null,
      'heuristic_fallback',
    )
    const provenance = buildDecisionProvenance({
      decisionSource,
      fallbackReasonCode: fallbackReasonCode || 'python_unavailable',
      stateSource: 'simulator_backed_telemetry',
      stateSourceDetail: 'battery_status_fallback',
    })

    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      soc: Number(battery.soc ?? 50),
      power_kw: Number(battery.power ?? 0),
      mode,
      active_command: activeCommand,
      requested_command: requestedCommand,
      decision_source: provenance.decision_source,
      command_reason: effectiveModeState?.reason || recentCommand?.reason || null,
      battery_capacity_kwh: Number(battery.capacity ?? 150),
      max_power_kw: 5.0,
      last_update: effectiveModeState?.updated_at || battery.lastUpdated || new Date().toISOString(),
      estimated_completion: recentCommand?.result?.estimated_completion || null,
      scheduled_commands_count: pendingSchedules.length,
      provenance,
      source_metadata: {
        tenant_filter_applied: true,
        python_script: pythonScript,
        python_script_available: pythonScriptAvailable,
        fallback_reason_code: provenance.fallback_reason_code,
        decision_source: provenance.decision_source,
        state_source: provenance.state_source,
        telemetry_classification: provenance.telemetry_classification,
      },
      source: 'battery_status_fallback'
    }
    
  } catch (error) {
    const errorData = (error as any)?.data
    if (errorData?.error?.code === 'INVALID_TENANT' || errorData?.error?.code === 'TENANT_AUTH_REQUIRED') {
      return errorData
    }

    console.error('Status endpoint error:', error)
    
    return {
      success: false,
      error: getErrorMessage(error, 'Status endpoint error'),
      // Minimal fallback
      soc: 50,
      power_kw: 0,
      mode: 'automatic',
      active_command: null,
      battery_capacity_kwh: 10.0,
      max_power_kw: 5.0,
      last_update: new Date().toISOString(),
      source: 'error_fallback'
    }
  }
})

function resolveCommandTimestamp(command: CommandHistoryRecord | null): number {
  if (!command) {
    return 0
  }
  const rawTimestamp = command.executed_at || command.timestamp || 0
  const parsed = new Date(rawTimestamp).getTime()
  return Number.isFinite(parsed) ? parsed : 0
}

function resolveScheduledTimeMs(value: string | null | undefined): number {
  const parsed = new Date(value || 0).getTime()
  return Number.isFinite(parsed) ? parsed : 0
}
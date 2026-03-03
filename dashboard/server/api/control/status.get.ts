// Control API - System Status Endpoint
// GET /api/control/status

import { getTenantResponseMetadata, isRecordVisibleForTenant, resolveTenantContext } from '../../utils/tenant-context'
import { getBatteryControlState } from '../../utils/battery-control-state'

function deriveCommandFromPower(powerKw: number): 'charge' | 'discharge' | 'hold' {
  if (powerKw > 0.05) return 'charge'
  if (powerKw < -0.05) return 'discharge'
  return 'hold'
}

export default defineEventHandler(async (event) => {
  try {
    const tenant = await resolveTenantContext(event)
    const pythonScript = 'get_control_status.py'
    let fallbackReasonCode: string | null = null
    // Import the Python control system
    const pythonRunner: any = await import('../../utils/python-runner.js').catch(() => ({ execPython: null, hasPythonScript: null }))
    const execPython = pythonRunner?.execPython
    const hasPythonScript = pythonRunner?.hasPythonScript
    const pythonScriptAvailable = Boolean(execPython && hasPythonScript && hasPythonScript(pythonScript))
    const controlModeByTenant = (globalThis as any).__controlModeByTenant || {}
    const controlModeState = controlModeByTenant[tenant.id] || null
    const persistedControl = await getBatteryControlState(tenant.id).catch(() => null)
    const persistedModeState = persistedControl
      ? {
          mode: persistedControl.manualMode ? 'manual' : 'automatic',
          active_command: deriveCommandFromPower(Number(persistedControl.powerCommand || 0)),
          requested_command: persistedControl.manualMode ? deriveCommandFromPower(Number(persistedControl.powerCommand || 0)) : 'auto',
          decision_source: persistedControl.manualMode ? 'manual' : 'dagster',
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
        
        return {
          success: true,
          tenant: getTenantResponseMetadata(tenant),
          ...pythonStatus,
          mode: effectiveModeState?.mode || pythonStatus?.mode || 'automatic',
          active_command: effectiveModeState?.active_command || pythonStatus?.active_command || null,
          requested_command: effectiveModeState?.requested_command || pythonStatus?.requested_command || pythonStatus?.active_command || null,
          decision_source: effectiveModeState?.decision_source || pythonStatus?.decision_source || null,
          command_reason: effectiveModeState?.reason || pythonStatus?.command_reason || null,
          last_update: effectiveModeState?.updated_at || pythonStatus?.last_update || new Date().toISOString(),
          source_metadata: {
            tenant_filter_applied: true,
            python_script: pythonScript,
            python_script_available: true,
            fallback_reason_code: 'none',
            mode_state_overlay_applied: Boolean(effectiveModeState),
          },
          source: 'python_controller'
        }
      } catch (pythonError) {
        console.warn('Python controller not available:', pythonError.message)
        fallbackReasonCode = 'python_execution_failed'
      }
    } else {
      fallbackReasonCode = 'python_script_missing'
    }

    // Deterministic fallback from persisted battery state and command memory.
    const [batteryStatus] = await Promise.all([
      $fetch<any>('/api/battery/status', {
        headers: {
          'x-tenant-id': tenant.id,
        },
        query: {
          tenantId: tenant.id,
        },
      }).catch(() => null),
    ])

    const battery = batteryStatus?.battery || {}
    const schedules = (Array.isArray(globalThis.scheduledCommands) ? globalThis.scheduledCommands : [])
      .filter((cmd: any) => isRecordVisibleForTenant(cmd?.tenant_id ?? cmd?.tenantId, tenant))
    const now = Date.now()
    const pendingSchedules = schedules.filter((cmd: any) => {
      return cmd?.status === 'pending' && new Date(cmd?.scheduled_time).getTime() > now
    })

    const history = (Array.isArray(globalThis.commandHistory) ? globalThis.commandHistory : [])
      .filter((entry: any) => isRecordVisibleForTenant(entry?.tenant_id ?? entry?.tenantId, tenant))
    const lastCommand = history[0] || null
    const lastCommandTs = lastCommand ? new Date(lastCommand.executed_at || lastCommand.timestamp).getTime() : 0
    const isRecentCommand = lastCommandTs > 0 && now - lastCommandTs <= 6 * 60 * 60 * 1000

    const activeCommand = effectiveModeState?.active_command || (isRecentCommand ? (lastCommand.command || null) : null)
    const requestedCommand = effectiveModeState?.requested_command || (isRecentCommand ? (lastCommand.requested_command || lastCommand.command || null) : null)
    const mode = effectiveModeState?.mode || (activeCommand ? 'manual' : 'automatic')
    const decisionSource = effectiveModeState?.decision_source || (isRecentCommand ? (lastCommand.decision_source || null) : null)

    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      soc: Number(battery.soc ?? 50),
      power_kw: Number(battery.power ?? 0),
      mode,
      active_command: activeCommand,
      requested_command: requestedCommand,
      decision_source: decisionSource,
      command_reason: effectiveModeState?.reason || (isRecentCommand ? (lastCommand.reason || null) : null),
      battery_capacity_kwh: Number(battery.capacity ?? 150),
      max_power_kw: 5.0,
      last_update: effectiveModeState?.updated_at || battery.lastUpdated || new Date().toISOString(),
      estimated_completion: isRecentCommand ? (lastCommand.result?.estimated_completion || null) : null,
      scheduled_commands_count: pendingSchedules.length,
      source_metadata: {
        tenant_filter_applied: true,
        python_script: pythonScript,
        python_script_available: pythonScriptAvailable,
        fallback_reason_code: fallbackReasonCode || 'python_unavailable',
      },
      source: 'battery_status_fallback'
    }
    
  } catch (error) {
    const errorData = (error as any)?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('Status endpoint error:', error)
    
    return {
      success: false,
      error: error.message,
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
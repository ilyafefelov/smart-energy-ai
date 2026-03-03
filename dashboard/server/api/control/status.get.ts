// Control API - System Status Endpoint
// GET /api/control/status

import { getTenantResponseMetadata, isRecordVisibleForTenant, resolveTenantContext } from '../../utils/tenant-context'

export default defineEventHandler(async (event) => {
  try {
    const tenant = await resolveTenantContext(event)
    // Import the Python control system
    const { execPython } = await import('../../../utils/python-runner.js').catch(() => ({ execPython: null }))
    
    if (execPython) {
      // Try to get status from Python controller
      try {
        const result = await execPython('get_control_status.py', { tenant_id: tenant.id })
        const pythonStatus = JSON.parse(result)
        
        return {
          success: true,
          tenant: getTenantResponseMetadata(tenant),
          ...pythonStatus,
          source_metadata: {
            tenant_filter_applied: true,
          },
          source: 'python_controller'
        }
      } catch (pythonError) {
        console.warn('Python controller not available:', pythonError.message)
      }
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

    const activeCommand = isRecentCommand ? (lastCommand.command || null) : null
    const mode = activeCommand ? 'manual' : 'automatic'

    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      soc: Number(battery.soc ?? 50),
      power_kw: Number(battery.power ?? 0),
      mode,
      active_command: activeCommand,
      command_reason: isRecentCommand ? (lastCommand.reason || null) : null,
      battery_capacity_kwh: Number(battery.capacity ?? 150),
      max_power_kw: 5.0,
      last_update: battery.lastUpdated || new Date().toISOString(),
      estimated_completion: isRecentCommand ? (lastCommand.result?.estimated_completion || null) : null,
      scheduled_commands_count: pendingSchedules.length,
      source_metadata: {
        tenant_filter_applied: true,
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
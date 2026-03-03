// Control API - Get Scheduled Commands Endpoint
// GET /api/control/scheduled

import { getTenantResponseMetadata, isRecordVisibleForTenant, resolveTenantContext } from '../../utils/tenant-context'

export default defineEventHandler(async (event) => {
  try {
    const tenant = await resolveTenantContext(event)
    const query = getQuery(event)
    const limit = Math.min(parseInt(query.limit as string) || 20, 50)
    
    // Try to get schedules from Python controller
    const { execPython } = await import('../../../utils/python-runner.js').catch(() => ({ execPython: null }))
    
    if (execPython) {
      try {
        const result = await execPython('get_scheduled_commands.py', {
          limit: limit.toString(),
          tenant_id: tenant.id,
        })
        const pythonSchedules = JSON.parse(result)
        const scopedSchedules = (Array.isArray(pythonSchedules) ? pythonSchedules : [])
          .filter((cmd: any) => isRecordVisibleForTenant(cmd?.tenant_id ?? cmd?.tenantId, tenant))
        
        return {
          success: true,
          tenant: getTenantResponseMetadata(tenant),
          scheduled_commands: scopedSchedules,
          count: scopedSchedules.length,
          source_metadata: {
            tenant_filter_applied: true,
          },
          source: 'python_controller'
        }
        
      } catch (pythonError) {
        console.warn('Python controller schedules not available:', pythonError.message)
      }
    }
    
    // Deterministic fallback to in-memory schedules.
    const schedules = Array.isArray(globalThis.scheduledCommands) ? globalThis.scheduledCommands : []
    const scopedSchedules = schedules.filter((cmd: any) =>
      isRecordVisibleForTenant(cmd?.tenant_id ?? cmd?.tenantId, tenant),
    )
    
    // Filter to only pending and future schedules
    const now = new Date()
    const activeSchedules = scopedSchedules.filter(cmd => 
      cmd.status === 'pending' && new Date(cmd.scheduled_time) > now
    )
    
    // Sort by scheduled time
    activeSchedules.sort((a, b) => 
      new Date(a.scheduled_time).getTime() - new Date(b.scheduled_time).getTime()
    )
    
    // Apply limit
    const limitedSchedules = activeSchedules.slice(0, limit)
    
    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      scheduled_commands: limitedSchedules,
      count: limitedSchedules.length,
      source_metadata: {
        tenant_filter_applied: true,
      },
      source: 'memory_storage'
    }
    
  } catch (error) {
    const errorData = (error as any)?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('Scheduled commands endpoint error:', error)
    
    return {
      success: false,
      error: error.message,
      scheduled_commands: [],
      count: 0,
      source: 'error_fallback'
    }
  }
})

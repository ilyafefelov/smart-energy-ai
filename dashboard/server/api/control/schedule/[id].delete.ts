// Control API - Remove Scheduled Command Endpoint
// DELETE /api/control/schedule/[id]

import { createError } from 'h3'
import { ensureScheduledCommands, getErrorMessage, hasStatusCode, setScheduledCommands } from '../../../utils/control-memory'
import { getTenantResponseMetadata, isRecordVisibleForTenant, resolveTenantContext } from '../../../utils/tenant-context'

export default defineEventHandler(async (event) => {
  try {
    const tenant = await resolveTenantContext(event)
    const scheduleId = getRouterParam(event, 'id')
    const pythonScript = 'cancel_scheduled_command.py'
    let fallbackReasonCode: string | null = null
    
    if (!scheduleId) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Schedule ID is required'
      })
    }
    
    console.log('Removing scheduled command:', scheduleId)
    
    // Try to remove via Python controller
    const pythonRunner: any = await import('../../../utils/python-runner.js').catch(() => ({ execPython: null, hasPythonScript: null }))
    const execPython = pythonRunner?.execPython
    const hasPythonScript = pythonRunner?.hasPythonScript
    const pythonScriptAvailable = Boolean(execPython && hasPythonScript && hasPythonScript(pythonScript))
    
    if (pythonScriptAvailable && execPython) {
      try {
        const result = await execPython(pythonScript, {
          schedule_id: scheduleId,
          tenant_id: tenant.id,
        })
        
        const pythonResult = JSON.parse(result)
        
        if (pythonResult.success) {
          return {
            success: true,
            tenant: getTenantResponseMetadata(tenant),
            message: 'Scheduled command cancelled',
            schedule_id: scheduleId,
            source_metadata: {
              tenant_filter_applied: true,
              python_script: pythonScript,
              python_script_available: true,
              fallback_reason_code: 'none',
            },
            source: 'python_controller'
          }
        } else {
          throw new Error(pythonResult.error || 'Cancellation failed')
        }
        
      } catch (pythonError) {
        console.warn('Python controller cancellation failed:', getErrorMessage(pythonError, 'Cancellation failed'))
        fallbackReasonCode = 'python_execution_failed'
      }
    } else {
      fallbackReasonCode = 'python_script_missing'
    }
    
    // Fallback to in-memory removal
    const schedules = ensureScheduledCommands()
    const initialCount = schedules.length
    
    // Remove the schedule
    const remainingSchedules = schedules.filter(
      cmd => !(cmd.id === scheduleId && isRecordVisibleForTenant(cmd?.tenant_id ?? cmd?.tenantId, tenant))
    )
    setScheduledCommands(remainingSchedules)
    
    const finalCount = remainingSchedules.length
    
    if (initialCount === finalCount) {
      throw createError({
        statusCode: 404,
        statusMessage: 'Scheduled command not found'
      })
    }
    
    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      message: 'Scheduled command cancelled',
      schedule_id: scheduleId,
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

    console.error('Schedule removal error:', error)
    
    if (hasStatusCode(error)) {
      throw error
    }
    
    throw createError({
      statusCode: 500,
      statusMessage: getErrorMessage(error, 'Schedule removal failed')
    })
  }
})
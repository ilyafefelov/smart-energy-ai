// Control API - Remove Scheduled Command Endpoint
// DELETE /api/control/schedule/[id]

export default defineEventHandler(async (event) => {
  try {
    const scheduleId = getRouterParam(event, 'id')
    
    if (!scheduleId) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Schedule ID is required'
      })
    }
    
    console.log('Removing scheduled command:', scheduleId)
    
    // Try to remove via Python controller
    const { execPython } = await import('../../../../utils/python-runner.js').catch(() => ({ execPython: null }))
    
    if (execPython) {
      try {
        const result = await execPython('cancel_scheduled_command.py', {
          schedule_id: scheduleId
        })
        
        const pythonResult = JSON.parse(result)
        
        if (pythonResult.success) {
          return {
            success: true,
            message: 'Scheduled command cancelled',
            schedule_id: scheduleId,
            source: 'python_controller'
          }
        } else {
          throw new Error(pythonResult.error || 'Cancellation failed')
        }
        
      } catch (pythonError) {
        console.warn('Python controller cancellation failed:', pythonError.message)
      }
    }
    
    // Fallback to in-memory removal
    if (!globalThis.scheduledCommands) {
      globalThis.scheduledCommands = []
    }
    
    const initialCount = globalThis.scheduledCommands.length
    
    // Remove the schedule
    globalThis.scheduledCommands = globalThis.scheduledCommands.filter(
      cmd => cmd.id !== scheduleId
    )
    
    const finalCount = globalThis.scheduledCommands.length
    
    if (initialCount === finalCount) {
      throw createError({
        statusCode: 404,
        statusMessage: 'Scheduled command not found'
      })
    }
    
    return {
      success: true,
      message: 'Scheduled command cancelled',
      schedule_id: scheduleId,
      source: 'memory_storage'
    }
    
  } catch (error) {
    console.error('Schedule removal error:', error)
    
    if (error.statusCode) {
      throw error
    }
    
    throw createError({
      statusCode: 500,
      statusMessage: error.message || 'Schedule removal failed'
    })
  }
})
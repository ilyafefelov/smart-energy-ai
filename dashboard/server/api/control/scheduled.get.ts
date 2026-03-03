// Control API - Get Scheduled Commands Endpoint
// GET /api/control/scheduled

export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const limit = Math.min(parseInt(query.limit as string) || 20, 50)
    
    // Try to get schedules from Python controller
    const { execPython } = await import('../../../utils/python-runner.js').catch(() => ({ execPython: null }))
    
    if (execPython) {
      try {
        const result = await execPython('get_scheduled_commands.py', { limit: limit.toString() })
        const pythonSchedules = JSON.parse(result)
        
        return {
          success: true,
          scheduled_commands: pythonSchedules,
          count: pythonSchedules.length,
          source: 'python_controller'
        }
        
      } catch (pythonError) {
        console.warn('Python controller schedules not available:', pythonError.message)
      }
    }
    
    // Deterministic fallback to in-memory schedules.
    const schedules = Array.isArray(globalThis.scheduledCommands) ? globalThis.scheduledCommands : []
    
    // Filter to only pending and future schedules
    const now = new Date()
    const activeSchedules = schedules.filter(cmd => 
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
      scheduled_commands: limitedSchedules,
      count: limitedSchedules.length,
      source: 'memory_storage'
    }
    
  } catch (error) {
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

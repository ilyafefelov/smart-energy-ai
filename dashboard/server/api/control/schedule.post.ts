// Control API - Schedule Management Endpoint
// POST /api/control/schedule

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    
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
    
    const schedule = {
      id: generateScheduleId(),
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
        const result = await execPython('create_schedule.py', {
          command: schedule.command,
          power_kw: schedule.power_kw.toString(),
          scheduled_time: schedule.scheduled_time,
          reason: schedule.reason,
          user_id: schedule.user_id
        })
        
        const pythonResult = JSON.parse(result)
        
        return {
          success: true,
          schedule_id: schedule.id,
          scheduled_time: schedule.scheduled_time,
          result: pythonResult,
          source: 'python_controller'
        }
        
      } catch (pythonError) {
        console.warn('Python controller scheduling failed:', pythonError.message)
      }
    }
    
    // Fallback to in-memory storage
    if (!globalThis.scheduledCommands) {
      globalThis.scheduledCommands = []
    }
    
    globalThis.scheduledCommands.push(schedule)
    
    // Keep only future schedules (cleanup old ones)
    globalThis.scheduledCommands = globalThis.scheduledCommands.filter(
      cmd => new Date(cmd.scheduled_time) > new Date() || cmd.status === 'pending'
    )
    
    return {
      success: true,
      schedule_id: schedule.id,
      scheduled_time: schedule.scheduled_time,
      message: 'Command scheduled successfully',
      source: 'memory_storage'
    }
    
  } catch (error) {
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
  return 'sched_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6)
}
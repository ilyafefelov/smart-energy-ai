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
    
    // Fallback to in-memory schedules
    let schedules = globalThis.scheduledCommands || []
    
    if (schedules.length === 0) {
      // Generate some mock scheduled commands for demo
      schedules = generateMockSchedules()
      globalThis.scheduledCommands = schedules
    }
    
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

function generateMockSchedules() {
  const commands = ['charge', 'discharge', 'hold']
  const reasons = [
    'Scheduled during off-peak hours',
    'Peak demand response',
    'Battery maintenance cycle',
    'Cost optimization schedule',
    'Grid balancing service'
  ]
  
  const schedules = []
  const now = new Date()
  
  // Create 3-5 mock scheduled commands
  const count = Math.floor(Math.random() * 3) + 3
  
  for (let i = 0; i < count; i++) {
    // Schedule between 1 hour and 2 days from now
    const hoursAhead = Math.floor(Math.random() * 47) + 1
    const scheduledTime = new Date(now.getTime() + hoursAhead * 60 * 60 * 1000)
    
    const command = commands[Math.floor(Math.random() * commands.length)]
    
    let power_kw = 0
    if (command === 'charge') {
      power_kw = Math.round((Math.random() * 3 + 1) * 10) / 10 // 1-4kW
    } else if (command === 'discharge') {
      power_kw = Math.round((Math.random() * 3 + 1) * 10) / 10 // 1-4kW (stored as positive)
    }
    
    schedules.push({
      id: `sched_mock_${i}_${Date.now()}`,
      command: command,
      power_kw: power_kw,
      scheduled_time: scheduledTime.toISOString(),
      reason: reasons[Math.floor(Math.random() * reasons.length)],
      user_id: Math.random() > 0.5 ? 'dashboard' : 'system',
      created_at: new Date(now.getTime() - Math.random() * 60 * 60 * 1000).toISOString(), // Created up to 1 hour ago
      status: 'pending'
    })
  }
  
  return schedules
}
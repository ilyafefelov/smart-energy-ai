// Control API - Command Execution Endpoint
// POST /api/control/execute

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    
    // Validate input
    if (!body.command) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Command is required'
      })
    }
    
    if (!['charge', 'discharge', 'hold', 'auto'].includes(body.command)) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Invalid command. Must be: charge, discharge, hold, or auto'
      })
    }
    
    // Validate power for charge/discharge commands
    if (['charge', 'discharge'].includes(body.command)) {
      if (typeof body.power_kw !== 'number' || Math.abs(body.power_kw) > 10) {
        throw createError({
          statusCode: 400,
          statusMessage: 'Invalid power_kw. Must be a number between -10 and 10'
        })
      }
    }
    
    const command = {
      command: body.command,
      power_kw: body.power_kw || 0,
      duration_minutes: body.duration_minutes || null,
      reason: body.reason || `Dashboard command: ${body.command}`,
      user_id: body.user_id || 'dashboard',
      timestamp: new Date().toISOString()
    }
    
    console.log('Executing control command:', command)
    
    // Try to execute via Python controller
    const { execPython } = await import('../../../utils/python-runner.js').catch(() => ({ execPython: null }))
    
    if (execPython) {
      try {
        const result = await execPython('execute_control_command.py', {
          ...command,
          power: command.power_kw.toString(),
          command_type: command.command
        })
        
        const pythonResult = JSON.parse(result)
        
        console.log('Python controller result:', pythonResult)
        
        return {
          success: true,
          result: pythonResult,
          command_id: generateId(),
          executed_at: command.timestamp,
          source: 'python_controller'
        }
        
      } catch (pythonError) {
        console.warn('Python controller execution failed:', pythonError.message)
      }
    }
    
    // Fallback simulation for development
    console.log('Using simulation mode for command execution')
    
    // Simulate command execution
    const simulationResult = {
      success: true,
      new_soc: Math.random() * 0.8 + 0.1, // 10-90%
      power_kw: command.power_kw,
      estimated_completion: command.duration_minutes 
        ? new Date(Date.now() + command.duration_minutes * 60000).toISOString()
        : null,
      validation: {
        power_within_limits: Math.abs(command.power_kw) <= 5.0,
        soc_safe_for_operation: true,
        command_accepted: true
      }
    }
    
    // Simulate different responses based on command
    if (command.command === 'charge') {
      simulationResult.new_soc = Math.min(0.95, simulationResult.new_soc + 0.1)
      simulationResult.estimated_completion = new Date(Date.now() + 120 * 60000).toISOString() // 2 hours
    } else if (command.command === 'discharge') {
      simulationResult.new_soc = Math.max(0.05, simulationResult.new_soc - 0.1)  
      simulationResult.estimated_completion = new Date(Date.now() + 90 * 60000).toISOString() // 1.5 hours
    }
    
    // Store command in memory for history (in real implementation, this would go to database)
    if (!globalThis.commandHistory) {
      globalThis.commandHistory = []
    }
    
    const historyEntry = {
      ...command,
      result: simulationResult,
      executed_at: new Date().toISOString(),
      success: true
    }
    
    globalThis.commandHistory.unshift(historyEntry)
    
    // Keep only last 100 commands
    if (globalThis.commandHistory.length > 100) {
      globalThis.commandHistory = globalThis.commandHistory.slice(0, 100)
    }
    
    return {
      success: true,
      result: simulationResult,
      command_id: generateId(),
      executed_at: command.timestamp,
      source: 'simulation'
    }
    
  } catch (error) {
    console.error('Command execution error:', error)
    
    if (error.statusCode) {
      throw error
    }
    
    throw createError({
      statusCode: 500,
      statusMessage: error.message || 'Command execution failed'
    })
  }
})

function generateId() {
  return 'cmd_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
}
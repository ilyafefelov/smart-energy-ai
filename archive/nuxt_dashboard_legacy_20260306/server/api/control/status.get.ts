// Control API - System Status Endpoint
// GET /api/control/status

export default defineEventHandler(async (event) => {
  try {
    // Import the Python control system
    const { execPython } = await import('../../../utils/python-runner.js').catch(() => ({ execPython: null }))
    
    if (execPython) {
      // Try to get status from Python controller
      try {
        const result = await execPython('get_control_status.py')
        const pythonStatus = JSON.parse(result)
        
        return {
          success: true,
          ...pythonStatus,
          source: 'python_controller'
        }
      } catch (pythonError) {
        console.warn('Python controller not available:', pythonError.message)
      }
    }
    
    // Fallback to mock data for development/demo
    const mockStatus = {
      soc: Math.round(30 + Math.random() * 60), // 30-90%
      power_kw: Math.round((Math.random() - 0.5) * 10 * 100) / 100, // -5 to +5kW
      mode: Math.random() > 0.7 ? 'manual' : 'automatic',
      active_command: Math.random() > 0.6 ? ['charge', 'discharge', 'hold'][Math.floor(Math.random() * 3)] : null,
      command_reason: null,
      battery_capacity_kwh: 10.0,
      max_power_kw: 5.0,
      last_update: new Date().toISOString(),
      estimated_completion: null,
      scheduled_commands_count: Math.floor(Math.random() * 3)
    }
    
    // Add command reason if there's an active command
    if (mockStatus.active_command) {
      const reasons = {
        'charge': 'Low electricity prices detected',
        'discharge': 'Peak price arbitrage opportunity', 
        'hold': 'Marginal price conditions'
      }
      mockStatus.command_reason = reasons[mockStatus.active_command]
    }
    
    return {
      success: true,
      ...mockStatus,
      source: 'mock_data'
    }
    
  } catch (error) {
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
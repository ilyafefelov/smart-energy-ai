// Control API - Command History Endpoint
// GET /api/control/history

export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const limit = Math.min(parseInt(query.limit as string) || 50, 100)
    
    // Try to get history from Python controller
    const { execPython } = await import('../../../utils/python-runner.js').catch(() => ({ execPython: null }))
    
    if (execPython) {
      try {
        const result = await execPython('get_control_history.py', { limit: limit.toString() })
        const pythonHistory = JSON.parse(result)
        
        return {
          success: true,
          history: pythonHistory,
          count: pythonHistory.length,
          source: 'python_controller'
        }
        
      } catch (pythonError) {
        console.warn('Python controller history not available:', pythonError.message)
      }
    }
    
    // Fallback to in-memory history or generate mock data
    let history = globalThis.commandHistory || []
    
    if (history.length === 0) {
      // Generate some mock history for demo
      history = generateMockHistory()
      globalThis.commandHistory = history
    }
    
    // Apply limit
    const limitedHistory = history.slice(0, limit)
    
    // Transform for API response
    const apiHistory = limitedHistory.map(entry => ({
      timestamp: entry.timestamp || entry.executed_at,
      command: entry.command,
      power_kw: entry.power_kw,
      reason: entry.reason,
      user_id: entry.user_id,
      soc_before: entry.result?.soc_before || Math.random() * 0.8 + 0.1,
      soc_after: entry.result?.new_soc || Math.random() * 0.8 + 0.1,
      success: entry.success !== false,
      estimated_completion: entry.result?.estimated_completion
    }))
    
    return {
      success: true,
      history: apiHistory,
      count: apiHistory.length,
      source: 'mock_data'
    }
    
  } catch (error) {
    console.error('History endpoint error:', error)
    
    return {
      success: false,
      error: error.message,
      history: [],
      count: 0,
      source: 'error_fallback'
    }
  }
})

function generateMockHistory() {
  const commands = ['charge', 'discharge', 'hold', 'auto']
  const reasons = [
    'Manual control via dashboard',
    'Scheduled command execution',
    'Low electricity prices',
    'Peak price arbitrage',
    'Battery protection protocol',
    'User preference: max earnings',
    'Emergency backup charging',
    'Load balancing operation'
  ]
  
  const history = []
  const now = new Date()
  
  for (let i = 0; i < 20; i++) {
    const timestamp = new Date(now.getTime() - i * 15 * 60 * 1000) // 15 minutes apart
    const command = commands[Math.floor(Math.random() * commands.length)]
    
    let power_kw = 0
    if (command === 'charge') {
      power_kw = Math.round((Math.random() * 4 + 1) * 100) / 100 // 1-5kW
    } else if (command === 'discharge') {
      power_kw = -Math.round((Math.random() * 4 + 1) * 100) / 100 // -1 to -5kW
    }
    
    history.push({
      timestamp: timestamp.toISOString(),
      command: command,
      power_kw: power_kw,
      reason: reasons[Math.floor(Math.random() * reasons.length)],
      user_id: Math.random() > 0.5 ? 'dashboard' : 'system',
      success: Math.random() > 0.05, // 95% success rate
      result: {
        new_soc: Math.random() * 0.8 + 0.1,
        soc_before: Math.random() * 0.8 + 0.1
      },
      executed_at: timestamp.toISOString()
    })
  }
  
  return history
}
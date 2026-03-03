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

    // Deterministic fallback to in-memory history.
    const [batteryStatus] = await Promise.all([
      $fetch<any>('/api/battery/status').catch(() => null),
    ])

    const fallbackSoc = Number(batteryStatus?.battery?.soc ?? 50) / 100
    const history = Array.isArray(globalThis.commandHistory) ? globalThis.commandHistory : []
    
    // Apply limit
    const limitedHistory = history.slice(0, limit)
    
    // Transform for API response
    const apiHistory = limitedHistory.map((entry: any) => {
      const socBefore = Number(entry?.result?.soc_before ?? entry?.soc_before ?? fallbackSoc)
      const socAfter = Number(entry?.result?.new_soc ?? entry?.soc_after ?? socBefore)

      return {
        timestamp: entry?.timestamp || entry?.executed_at,
        command: entry?.command,
        power_kw: Number(entry?.power_kw ?? 0),
        reason: entry?.reason,
        user_id: entry?.user_id,
        soc_before: Number.isFinite(socBefore) ? socBefore : fallbackSoc,
        soc_after: Number.isFinite(socAfter) ? socAfter : (Number.isFinite(socBefore) ? socBefore : fallbackSoc),
        success: entry?.success !== false,
        estimated_completion: entry?.result?.estimated_completion ?? null,
      }
    })
    
    return {
      success: true,
      history: apiHistory,
      count: apiHistory.length,
      source: 'memory_storage'
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

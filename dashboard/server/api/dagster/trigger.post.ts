// API endpoint to trigger Dagster asset materialization from dashboard

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const assetName = body.asset || body.asset_name
    
    if (!assetName) {
      return { success: false, error: 'Asset name required' }
    }
    
    // Use subprocess to run dagster CLI
    const { execSync } = await import('child_process')
    
    const startTime = Date.now()
    
    try {
      const output = execSync(
        `python -m dagster asset materialize --select "${assetName}" -m src.assets`,
        { 
          encoding: 'utf-8',
          timeout: 120000,
          cwd: process.cwd()
        }
      )
      
      const executionTime = Date.now() - startTime
      
      return {
        success: true,
        asset: assetName,
        execution_time_ms: executionTime,
        output: output.slice(-1000), // Last 1000 chars
        timestamp: new Date().toISOString()
      }
    } catch (execError) {
      return {
        success: false,
        asset: assetName,
        error: execError.message,
        output: execError.stdout || execError.stderr
      }
    }
  } catch (error) {
    console.error('[dagster/trigger] Error:', error)
    return {
      success: false,
      error: error.message
    }
  }
})

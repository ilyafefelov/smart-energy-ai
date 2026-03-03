// API endpoint to trigger Dagster asset materialization from dashboard

const AVAILABLE_ASSETS = [
  'market_data_asset',
  'weather_asset',
  'client_state_asset',
  'feature_matrix_asset',
  'price_forecast_asset',
  'optimization_schedule_asset',
  'optimization_schedule_milp_asset',
  'accuracy_benchmark_asset',
  'engine_benchmark_asset',
  'mlflow_tracking_asset',
]

const ASSET_ALIASES: Record<string, string> = {
  weather_data_asset: 'weather_asset',
}

function normalizeAssetName(value: unknown): string {
  const raw = typeof value === 'string' ? value.trim() : ''
  if (!raw) return ''
  return ASSET_ALIASES[raw] || raw
}

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const requestedAsset = body?.asset || body?.asset_name
    const normalizedAsset = normalizeAssetName(requestedAsset)
    
    if (!normalizedAsset) {
      return { success: false, error: 'Asset name required' }
    }

    if (!AVAILABLE_ASSETS.includes(normalizedAsset)) {
      return {
        success: false,
        error: `Unknown asset: ${normalizedAsset}`,
        requested_asset: requestedAsset,
        available_assets: AVAILABLE_ASSETS,
      }
    }
    
    // Use subprocess to run dagster CLI
    const { execFileSync } = await import('child_process')
    
    const startTime = Date.now()
    
    // Get project root (parent of dashboard)
    const path = await import('path')
    const projectRoot = path.resolve(process.cwd(), '..')
    
    try {
      const output = execFileSync(
        'python',
        ['-m', 'dagster', 'asset', 'materialize', '--select', normalizedAsset, '-m', 'src.definitions'],
        {
          encoding: 'utf-8',
          timeout: 180000,
          cwd: projectRoot
        }
      )
      
      const executionTime = Date.now() - startTime
      
      return {
        success: true,
        asset: normalizedAsset,
        requested_asset: requestedAsset,
        execution_time_ms: executionTime,
        output: output.slice(-1000), // Last 1000 chars
        timestamp: new Date().toISOString()
      }
    } catch (execError) {
      const errorText = execError?.message || 'Dagster materialization command failed'
      const stdout = typeof execError?.stdout === 'string' ? execError.stdout : String(execError?.stdout || '')
      const stderr = typeof execError?.stderr === 'string' ? execError.stderr : String(execError?.stderr || '')

      return {
        success: false,
        asset: normalizedAsset,
        requested_asset: requestedAsset,
        error: errorText,
        output: (stdout || stderr).slice(-4000),
        available_assets: AVAILABLE_ASSETS,
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

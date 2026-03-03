// API endpoint to trigger Dagster asset materialization from dashboard

import { existsSync, readFileSync } from 'fs'
import { join, resolve } from 'path'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

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
    const tenant = await resolveTenantContext(event, { body })
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
    const projectRoot = resolve(process.cwd(), '..')

    const tenantConfigPath = join(projectRoot, 'energy_ml', 'configs', 'tenants', tenant.id, 'user_config.json')
    const legacyConfigPath = join(projectRoot, 'energy_ml', 'configs', 'user_config.json')
    const configPath = existsSync(tenantConfigPath) ? tenantConfigPath : legacyConfigPath
    let config: any = {}
    if (existsSync(configPath)) {
      try {
        config = JSON.parse(readFileSync(configPath, 'utf-8'))
      } catch {
        config = {}
      }
    }
    
    try {
      const output = execFileSync(
        'python',
        ['-m', 'dagster', 'asset', 'materialize', '--select', normalizedAsset, '-m', 'src.definitions'],
        {
          encoding: 'utf-8',
          timeout: 180000,
          cwd: projectRoot,
          env: {
            ...process.env,
            ENERGY_ML_CONFIG_DIR: join(projectRoot, 'energy_ml', 'configs', 'tenants', tenant.id),
            ENERGY_ML_TENANT_ID: tenant.id,
            WEATHER_LATITUDE: String(config?.latitude ?? 50.45),
            WEATHER_LONGITUDE: String(config?.longitude ?? 30.52),
            WEATHER_TIMEZONE: String(config?.timezone ?? 'Europe/Kiev'),
          },
        }
      )
      
      const executionTime = Date.now() - startTime
      
      return {
        success: true,
        tenant: getTenantResponseMetadata(tenant),
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
        tenant: getTenantResponseMetadata(tenant),
        asset: normalizedAsset,
        requested_asset: requestedAsset,
        error: errorText,
        output: (stdout || stderr).slice(-4000),
        available_assets: AVAILABLE_ASSETS,
      }
    }
  } catch (error) {
    const errorData = (error as any)?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('[dagster/trigger] Error:', error)
    return {
      success: false,
      error: (error as any).message
    }
  }
})

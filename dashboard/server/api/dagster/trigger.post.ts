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

function resolveAssetSelection(assetName: string, includeUpstream: boolean): string {
  return includeUpstream ? `*${assetName}` : assetName
}

function resolveDagsterDbConfig() {
  return {
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT || '5432'),
    user: process.env.DB_USER || 'dagster',
    password: process.env.DB_PASSWORD || 'dagster',
    database: process.env.DB_NAME || 'dagster',
  }
}

type DagsterScheduleSnapshot = {
  success: boolean
  source?: string
  asset?: string
  asset_file?: string
  dagster_home?: string
  tenant_id?: string
  selected_client_id?: string
  schedule?: Array<{
    hour: number
    action: string
    action_kw: number
    expected_profit_uah: number
    price_uah_kwh: number
  }>
  recommendation?: {
    action: string
    confidence: number
    confidence_percent: number
    rationale: string
  }
  generated_at?: string
  error?: string
}

async function persistDagsterSnapshot(snapshot: DagsterScheduleSnapshot, executionTimeMs: number) {
  let pool: any = null

  try {
    const { Pool } = await import('pg')
    pool = new Pool(resolveDagsterDbConfig())

    await pool.query(`
      CREATE TABLE IF NOT EXISTS asset_results (
        id SERIAL PRIMARY KEY,
        asset_name VARCHAR(255) NOT NULL,
        run_id VARCHAR(255),
        materialization_time TIMESTAMP DEFAULT NOW(),
        data JSONB,
        status VARCHAR(50) DEFAULT 'success',
        error_message TEXT,
        execution_time_ms INTEGER,
        UNIQUE(asset_name, run_id)
      )
    `)
    await pool.query('CREATE INDEX IF NOT EXISTS idx_asset_results_name ON asset_results(asset_name)')
    await pool.query('CREATE INDEX IF NOT EXISTS idx_asset_results_time ON asset_results(materialization_time DESC)')

    const assetName = String(snapshot.asset || 'optimization_schedule_milp_asset')
    const runId = `snapshot_${assetName}_${Date.now()}`

    await pool.query(
      `
        INSERT INTO asset_results (asset_name, run_id, materialization_time, data, status, execution_time_ms)
        VALUES ($1, $2, NOW(), $3::jsonb, 'success', $4)
        ON CONFLICT (asset_name, run_id)
        DO UPDATE SET
          data = EXCLUDED.data,
          status = EXCLUDED.status,
          execution_time_ms = EXCLUDED.execution_time_ms
      `,
      [assetName, runId, JSON.stringify(snapshot), executionTimeMs],
    )

    return {
      stored: true,
      assetName,
      runId,
    }
  } catch (error: any) {
    return {
      stored: false,
      error: error?.message || 'Failed to persist dagster snapshot',
    }
  } finally {
    if (pool) {
      await pool.end().catch(() => {})
    }
  }
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

    const includeUpstream = body?.include_upstream !== false
    const assetSelection = resolveAssetSelection(normalizedAsset, includeUpstream)
    
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
        ['-m', 'dagster', 'asset', 'materialize', '--select', assetSelection, '-m', 'src.definitions'],
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

      let snapshotPersist: any = { stored: false }
      try {
        const scheduleReaderOutput = execFileSync(
          'python',
          [
            join(projectRoot, 'scripts', 'read_dagster_schedule.py'),
            '--tenant-id',
            tenant.id,
            '--project-root',
            projectRoot,
          ],
          {
            encoding: 'utf-8',
            timeout: 30000,
            cwd: projectRoot,
            env: {
              ...process.env,
              ENERGY_ML_TENANT_ID: tenant.id,
            },
          },
        )

        const snapshot = JSON.parse((scheduleReaderOutput || '').trim()) as DagsterScheduleSnapshot
        if (snapshot?.success && Array.isArray(snapshot?.schedule) && snapshot.schedule.length > 0) {
          snapshot.tenant_id = tenant.id
          snapshotPersist = await persistDagsterSnapshot(snapshot, executionTime)
        } else {
          snapshotPersist = {
            stored: false,
            error: snapshot?.error || 'Schedule snapshot unavailable after materialization',
          }
        }
      } catch (snapshotError: any) {
        snapshotPersist = {
          stored: false,
          error: snapshotError?.message || 'Failed to create Dagster snapshot',
        }
      }
      
      return {
        success: true,
        tenant: getTenantResponseMetadata(tenant),
        asset: normalizedAsset,
        selection: assetSelection,
        include_upstream: includeUpstream,
        requested_asset: requestedAsset,
        execution_time_ms: executionTime,
        output: output.slice(-1000), // Last 1000 chars
        snapshot: snapshotPersist,
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
        selection: assetSelection,
        include_upstream: includeUpstream,
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

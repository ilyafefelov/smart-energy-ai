// API endpoint to get Dagster asset results from PostgreSQL
// Returns stored asset results for dashboard display

import {
  buildStrictDagsterTenantPredicate,
  dagsterAssetResultsHasTenantColumn,
  dagsterAssetResultsTableExists,
  resolveDagsterAssetResultsDbConfig,
} from '../../utils/dagster-asset-results'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

function buildEmptyAssetResponse(tenant: ReturnType<typeof getTenantResponseMetadata>, warning?: string) {
  return {
    success: true,
    timestamp: new Date().toISOString(),
    tenant,
    assets: [],
    total_assets: 0,
    source: 'dagster_asset_results',
    warning,
  }
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message
  }

  return ''
}

function isDagsterAssetDbUnavailable(error: unknown): boolean {
  if (!error || typeof error !== 'object') {
    return false
  }

  const candidate = error as { code?: unknown; errno?: unknown; message?: unknown; cause?: unknown }
  const code = typeof candidate.code === 'string'
    ? candidate.code
    : typeof candidate.errno === 'string'
      ? candidate.errno
      : ''
  const message = typeof candidate.message === 'string' ? candidate.message.toLowerCase() : ''
  const connectionErrorCodes = new Set(['ECONNREFUSED', 'ENOTFOUND', 'EAI_AGAIN', 'ETIMEDOUT', '3D000', '28P01'])

  if (connectionErrorCodes.has(code)) {
    return true
  }

  return message.includes('connect') || message.includes('database') || message.includes('connection terminated')
}

export default defineEventHandler(async (event) => {
  let pool: any = null

  try {
    const tenant = await resolveTenantContext(event)
    const tenantMetadata = getTenantResponseMetadata(tenant)
    const { Pool } = await import('pg')

    pool = new Pool({
      ...resolveDagsterAssetResultsDbConfig(),
    })

    if (!(await dagsterAssetResultsTableExists(pool))) {
      return buildEmptyAssetResponse(tenantMetadata, 'asset_results table not available')
    }

    const hasTenantColumn = await dagsterAssetResultsHasTenantColumn(pool)
    if (!hasTenantColumn) {
      console.warn('[dagster/assets] asset_results is missing required tenant_id enforcement')
      return buildEmptyAssetResponse(tenantMetadata, 'asset_results tenant scoping unavailable')
    }

    const tenantPredicate = buildStrictDagsterTenantPredicate()

    const result = await pool.query(`
      SELECT 
        asset_name,
        run_id,
        tenant_id,
        data,
        materialization_time,
        status,
        execution_time_ms,
        error_message
      FROM asset_results
      WHERE ${tenantPredicate}
      ORDER BY materialization_time DESC
      LIMIT 50
    `, [tenant.id])

    // Group by asset
    const assets: Record<string, {
      name: string
      last_run: string
      status: string
      execution_time_ms: number | null
      runs: Array<{ run_id: string; time: string; status: string; error: string | null }>
    }> = {}

    for (const row of result.rows) {
      if (!assets[row.asset_name]) {
        assets[row.asset_name] = {
          name: row.asset_name,
          last_run: row.materialization_time,
          status: row.status,
          execution_time_ms: row.execution_time_ms,
          runs: []
        }
      }

      assets[row.asset_name].runs.push({
        run_id: row.run_id,
        time: row.materialization_time,
        status: row.status,
        error: row.error_message
      })
    }
    
    return {
      success: true,
      timestamp: new Date().toISOString(),
      tenant: tenantMetadata,
      assets: Object.values(assets),
      total_assets: Object.keys(assets).length
    }
  } catch (error) {
    if (isDagsterAssetDbUnavailable(error)) {
      const tenant = await resolveTenantContext(event)
      const tenantMetadata = getTenantResponseMetadata(tenant)
      const message = getErrorMessage(error) || 'dagster asset results database unavailable'
      console.warn('[dagster/assets] Falling back to empty results:', message)
      return buildEmptyAssetResponse(tenantMetadata, message)
    }

    console.error('[dagster/assets] Error:', error)
    return {
      success: false,
      error: getErrorMessage(error) || 'Failed to fetch Dagster asset results'
    }
  } finally {
    if (pool) {
      await pool.end().catch(() => {})
    }
  }
})

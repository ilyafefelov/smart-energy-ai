// API endpoint to get Dagster asset results from PostgreSQL
// Returns stored asset results for dashboard display

import {
  buildStrictDagsterTenantPredicate,
  dagsterAssetResultsHasTenantColumn,
  dagsterAssetResultsTableExists,
  resolveDagsterAssetResultsDbConfig,
} from '../../utils/dagster-asset-results'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

export default defineEventHandler(async (event) => {
  let pool: any = null

  try {
    const tenant = await resolveTenantContext(event)
    const { Pool } = await import('pg')

    pool = new Pool({
      ...resolveDagsterAssetResultsDbConfig(),
    })

    if (!(await dagsterAssetResultsTableExists(pool))) {
      return {
        success: true,
        timestamp: new Date().toISOString(),
        tenant: getTenantResponseMetadata(tenant),
        assets: [],
        total_assets: 0,
      }
    }

    const hasTenantColumn = await dagsterAssetResultsHasTenantColumn(pool)
    if (!hasTenantColumn) {
      console.warn('[dagster/assets] asset_results is missing required tenant_id enforcement')
      return {
        success: true,
        timestamp: new Date().toISOString(),
        tenant: getTenantResponseMetadata(tenant),
        assets: [],
        total_assets: 0,
      }
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
      tenant: getTenantResponseMetadata(tenant),
      assets: Object.values(assets),
      total_assets: Object.keys(assets).length
    }
  } catch (error) {
    console.error('[dagster/assets] Error:', error)
    return {
      success: false,
      error: error.message
    }
  } finally {
    if (pool) {
      await pool.end().catch(() => {})
    }
  }
})

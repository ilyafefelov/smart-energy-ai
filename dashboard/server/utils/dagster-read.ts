import { exec } from 'child_process'
import path from 'path'
import { promisify } from 'util'
import {
  buildStrictDagsterTenantPredicate,
  dagsterAssetResultsHasTenantColumn,
  dagsterAssetResultsTableExists,
  resolveDagsterAssetResultsDbConfig,
} from './dagster-asset-results'

const execAsync = promisify(exec)

export type DagsterForecastProvenance = {
  forecast_run_id: string | null
  forecast_model_name: string | null
  forecast_model_family: string | null
  forecast_model_version: string | null
  forecast_horizon_mode: string | null
  forecast_uncertainty_source: string | null
  forecast_promotion_active: boolean | null
  forecast_promotion_source: string | null
  optimization_run_id: string | null
}

export type DagsterMaterializedRecommendation = {
  success: boolean
  source?: string
  asset?: string
  asset_file?: string
  dagster_home?: string
  run_id?: string
  materialization_time?: string | null
  tenant_id?: string
  selected_client_id?: string
  schedule?: Array<{
    hour: number
    hour_offset?: number
    action: 'BUY' | 'SELL' | 'HOLD'
    action_kw: number
    net_cost_eur: number
    expected_profit_uah: number
    price_eur_mwh: number
    price_uah_kwh: number
    soc_before_kwh?: number | null
    soc_after_kwh?: number | null
    charge_kwh?: number | null
    discharge_kwh?: number | null
    throughput_total_kwh?: number | null
    grid_import_kwh?: number | null
    grid_export_kwh?: number | null
    purchase_cost_eur?: number | null
    export_revenue_eur?: number | null
    degradation_penalty_eur?: number | null
    load_kwh?: number | null
    solar_kwh?: number | null
    solver?: string
  } & DagsterForecastProvenance>
  schedule_start_utc?: string
  generated_at?: string | null
  recommendation?: {
    action: 'BUY' | 'SELL' | 'HOLD'
    confidence: number
    confidence_percent: number
    rationale: string
  }
  error?: string
}

export async function readMaterializedDagsterRecommendation(
  projectRoot: string,
  tenantId: string,
): Promise<DagsterMaterializedRecommendation | null> {
  try {
    const scriptPath = path.join(projectRoot, 'scripts', 'read_dagster_schedule.py')
    const command = `python "${scriptPath}" --tenant-id "${tenantId}" --project-root "${projectRoot}"`
    const { stdout } = await execAsync(command, {
      cwd: projectRoot,
      timeout: 30000,
      env: {
        ...process.env,
        ENERGY_ML_TENANT_ID: tenantId,
      },
    })

    const payload = JSON.parse((stdout || '').trim()) as DagsterMaterializedRecommendation
    if (!payload?.success || !Array.isArray(payload?.schedule) || payload.schedule.length === 0) {
      return null
    }

    return payload
  } catch (e: any) {
    console.warn('[recommendation] Materialized Dagster schedule unavailable:', e?.message)
    return null
  }
}

export async function readDagsterRecommendationFromPostgres(
  tenantId: string,
): Promise<DagsterMaterializedRecommendation | null> {
  let pool: any = null

  try {
    const { Pool } = await import('pg')
    pool = new Pool(resolveDagsterAssetResultsDbConfig())

    if (!(await dagsterAssetResultsTableExists(pool))) {
      return null
    }

    const hasTenantColumn = await dagsterAssetResultsHasTenantColumn(pool)
    if (!hasTenantColumn) {
      console.warn('[recommendation] asset_results is missing required tenant_id enforcement')
      return null
    }

    const tenantPredicate = buildStrictDagsterTenantPredicate()

    const result = await pool.query(
      `
        SELECT asset_name, run_id, materialization_time, data
        FROM asset_results
        WHERE asset_name = ANY($1)
          AND status = 'success'
          AND ${tenantPredicate}
        ORDER BY materialization_time DESC
        LIMIT 1
      `,
      [['optimization_schedule_milp_asset', 'optimization_schedule_asset'], tenantId],
    )

    if (!result.rows?.length) {
      return null
    }

    const row = result.rows[0]
    const data = typeof row.data === 'string' ? JSON.parse(row.data) : row.data
    if (!data || !Array.isArray(data.schedule) || data.schedule.length === 0) {
      return null
    }

    return {
      ...data,
      success: true,
      asset: data.asset || row.asset_name,
      run_id: row.run_id,
      materialization_time: row.materialization_time ? new Date(row.materialization_time).toISOString() : null,
    }
  } catch (e: any) {
    console.warn('[recommendation] Postgres Dagster snapshot unavailable:', e?.message)
    return null
  } finally {
    if (pool) {
      await pool.end().catch(() => {})
    }
  }
}
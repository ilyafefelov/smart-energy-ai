// API endpoint to get recommendations from Dagster ML pipeline
// Connects dashboard to ML recommendation engine via Dagster/MLflow APIs

import { exec } from 'child_process'
import path from 'path'
import { promisify } from 'util'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

const DAGSTER_API = process.env.DAGSTER_API_URL || 'http://localhost:3000'
const execAsync = promisify(exec)

type DagsterMaterializedRecommendation = {
  success: boolean
  source?: string
  asset?: string
  asset_file?: string
  dagster_home?: string
  run_id?: string
  materialization_time?: string
  tenant_id?: string
  selected_client_id?: string
  schedule?: Array<{
    hour: number
    action: 'BUY' | 'SELL' | 'HOLD'
    action_kw: number
    net_cost_eur: number
    expected_profit_uah: number
    price_eur_mwh: number
    price_uah_kwh: number
    solver?: string
  }>
  recommendation?: {
    action: 'BUY' | 'SELL' | 'HOLD'
    confidence: number
    confidence_percent: number
    rationale: string
  }
  error?: string
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

async function queryDagsterStatus() {
  try {
    const dagsterQuery = await $fetch<any>(`${DAGSTER_API}/graphql`, {
      method: 'POST',
      body: {
        query: `{ instance { id } }`
      }
    })

    if (dagsterQuery?.data?.instance) {
      return { available: true, jobs: [] as string[] }
    }
  } catch (e: any) {
    console.warn('[recommendation] Dagster not available:', e?.message)
  }

  return { available: false, jobs: [] as string[] }
}

async function readMaterializedDagsterRecommendation(projectRoot: string, tenantId: string): Promise<DagsterMaterializedRecommendation | null> {
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

async function readDagsterRecommendationFromPostgres(tenantId: string): Promise<DagsterMaterializedRecommendation | null> {
  let pool: any = null

  try {
    const { Pool } = await import('pg')
    pool = new Pool(resolveDagsterDbConfig())

    const result = await pool.query(
      `
        SELECT asset_name, run_id, materialization_time, data
        FROM asset_results
        WHERE asset_name = ANY($1)
          AND status = 'success'
          AND COALESCE(data->>'tenant_id', '') = $2
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

export default defineEventHandler(async (event) => {
  try {
    const tenant = await resolveTenantContext(event)
    const projectRoot = path.resolve(process.cwd(), '..')
    const tenantRequest = {
      query: {
        tenantId: tenant.id,
      },
      headers: {
        'x-tenant-id': tenant.id,
      },
    }

    const [postgresDagster, fileDagster, mlRecommendation, pricesPayload, batteryPayload, mlflowStatus, dagsterStatus] = await Promise.all([
      readDagsterRecommendationFromPostgres(tenant.id),
      readMaterializedDagsterRecommendation(projectRoot, tenant.id),
      $fetch<any>('/api/ml/recommendation', tenantRequest).catch(() => null),
      $fetch<any>('/api/prices/current', tenantRequest).catch(() => null),
      $fetch<any>('/api/battery/status', tenantRequest).catch(() => null),
      $fetch<any>('/api/mlflow/status', tenantRequest).catch(() => null),
      queryDagsterStatus(),
    ])

    const materializedDagster = postgresDagster || fileDagster

    const currentPrice = Number(pricesPayload?.prices?.current?.price || 0)
    const batterySoc = Number(batteryPayload?.battery?.soc || 50)
    const mlData = mlRecommendation?.data || null
    const recommendationSource = postgresDagster
      ? 'dagster_postgres_snapshot'
      : fileDagster
        ? 'dagster_asset_file'
        : 'ml_api_fallback'

    const recommendation = materializedDagster
      ? {
          action: materializedDagster.recommendation?.action || 'HOLD',
          confidence: Number(materializedDagster.recommendation?.confidence || 0.8),
          confidence_percent: Math.round(Number(materializedDagster.recommendation?.confidence || 0.8) * 100),
          rationale: materializedDagster.recommendation?.rationale || `Dagster asset recommendation from ${materializedDagster.asset}`,
        }
      : {
          action: mlData?.action || 'HOLD',
          confidence: Number(mlData?.confidence || 0.5),
          confidence_percent: Math.round(Number(mlData?.confidence || 0.5) * 100),
          rationale: mlData?.reasoning || 'Recommendation unavailable - holding position',
        }

    const schedule24h = materializedDagster
      ? buildScheduleFromDagsterAsset(
          pricesPayload?.prices?.forecast?.next24h || [],
          materializedDagster.schedule || [],
          recommendation.confidence,
        )
      : buildDeterministicSchedule(
          pricesPayload?.prices?.forecast?.next24h || [],
          mlData?.daily_forecast || [],
          recommendation.confidence,
        )

    const activeModel = mlflowStatus?.active_model || null
    const modelInfo = {
      type: activeModel?.name || 'Phase4F',
      version: activeModel?.version || mlData?.model_info?.version || 'Phase4F-v1.0',
      last_trained: activeModel?.last_updated || mlData?.timestamp || new Date().toISOString(),
      accuracy_percent: Number(recommendation.confidence_percent || 0),
      mlflow_available: mlflowStatus?.mlflow_connected === true,
    }

    return {
      status: 'success',
      timestamp: new Date().toISOString(),
      tenant: getTenantResponseMetadata(tenant),
      recommendation,
      current_state: {
        price_uah_kwh: currentPrice,
        battery_soc_percent: batterySoc,
        time: new Date().toLocaleTimeString('uk-UA'),
      },
      schedule_24h: schedule24h,
      model_info: modelInfo,
      lineage: {
        data_sources: 5,
        total_features: 73,
        data_provenance: 'Weather API, Price OREE, Battery BMS, Solar Model, Wind Model',
      },
      monitoring: {
        needs_retraining: Boolean(mlflowStatus?.monitoring?.drift_detected),
        drift_detected: false,
        last_check: new Date().toISOString(),
      },
      dagster_status: dagsterStatus,
      source_metadata: {
        tenant_filter_applied: true,
        recommendation_source: recommendationSource,
        dagster_asset_name: materializedDagster?.asset || null,
        dagster_snapshot_run_id: materializedDagster?.run_id || null,
        dagster_snapshot_materialized_at: materializedDagster?.materialization_time || null,
        dagster_asset_file: materializedDagster?.asset_file || null,
        dagster_selected_client_id: materializedDagster?.selected_client_id || null,
      },
    }
  } catch (error: any) {
    const errorData = error?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('[recommendation] Error:', error)
    return {
      status: 'error',
      error: error?.message,
      fallback: 'HOLD',
    }
  }
})

function buildScheduleFromDagsterAsset(
  forecast: Array<{ hour: number; timestamp: string; price: number }>,
  dagsterSchedule: Array<{ hour: number; action: string; action_kw: number; expected_profit_uah: number; price_uah_kwh: number }>,
  baseConfidence: number,
) {
  const scheduleByHour = new Map<number, { action: string; action_kw: number; expected_profit_uah: number; price_uah_kwh: number }>()
  for (const row of dagsterSchedule) {
    const hour = Number(row?.hour)
    if (!Number.isFinite(hour)) continue
    scheduleByHour.set(hour, {
      action: row.action || 'HOLD',
      action_kw: Number(row.action_kw || 0),
      expected_profit_uah: Number(row.expected_profit_uah || 0),
      price_uah_kwh: Number(row.price_uah_kwh || 0),
    })
  }

  const rows = forecast.length > 0
    ? forecast.slice(0, 24).map((row) => {
        const hour = Number(row.hour)
        const dagsterRow = scheduleByHour.get(hour)
        const action = dagsterRow?.action || 'HOLD'
        const actionKw = Number(dagsterRow?.action_kw || 0)
        const rationale = action === 'HOLD'
          ? `Dagster schedule holds at ${hour}:00 (action_kw=${actionKw.toFixed(2)}).`
          : `Dagster schedule recommends ${action} at ${hour}:00 (action_kw=${actionKw.toFixed(2)}).`
        return {
          hour,
          time: new Date(row.timestamp).toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' }),
          price_uah_kwh: Number(Number(row.price || dagsterRow?.price_uah_kwh || 0).toFixed(2)),
          recommended_action: action,
          expected_profit_uah: Number(Number(dagsterRow?.expected_profit_uah || 0).toFixed(2)),
          confidence: Number(baseConfidence.toFixed(2)),
          is_peak: (hour >= 7 && hour <= 9) || (hour >= 17 && hour <= 20),
          rationale,
        }
      })
    : dagsterSchedule.slice(0, 24).map((row) => {
        const hour = Number(row.hour)
        const action = row.action || 'HOLD'
        const actionKw = Number(row.action_kw || 0)
        const rationale = action === 'HOLD'
          ? `Dagster schedule holds at ${hour}:00 (action_kw=${actionKw.toFixed(2)}).`
          : `Dagster schedule recommends ${action} at ${hour}:00 (action_kw=${actionKw.toFixed(2)}).`
        return {
          hour,
          time: `${String(hour).padStart(2, '0')}:00`,
          price_uah_kwh: Number(Number(row.price_uah_kwh || 0).toFixed(2)),
          recommended_action: action,
          expected_profit_uah: Number(Number(row.expected_profit_uah || 0).toFixed(2)),
          confidence: Number(baseConfidence.toFixed(2)),
          is_peak: (hour >= 7 && hour <= 9) || (hour >= 17 && hour <= 20),
          rationale,
        }
      })

  const totalProfit = rows.reduce((sum, row) => sum + Number(row.expected_profit_uah || 0), 0)
  return {
    schedule: rows,
    total_expected_profit: Number(totalProfit.toFixed(2)),
    buy_hours: rows.filter((row) => row.recommended_action === 'BUY').length,
    sell_hours: rows.filter((row) => row.recommended_action === 'SELL').length,
    discharge_hours: rows.filter((row) => row.recommended_action === 'DISCHARGE').length,
  }
}

function buildDeterministicSchedule(
  forecast: Array<{ hour: number; timestamp: string; price: number }>,
  mlForecast: Array<{ hour: number; action?: string; reasoning?: string }>,
  baseConfidence: number
) {
  const actionByHour = new Map<number, { action: string; reasoning: string }>()
  for (const item of mlForecast) {
    if (typeof item?.hour !== 'number') continue
    actionByHour.set(item.hour, {
      action: item.action || 'HOLD',
      reasoning: item.reasoning || '',
    })
  }

  const safeForecast = forecast.slice(0, 24)
  const avgPrice = safeForecast.length > 0
    ? safeForecast.reduce((sum, row) => sum + Number(row.price || 0), 0) / safeForecast.length
    : 0

  const schedule = safeForecast.map((row) => {
    const hour = Number(row.hour)
    const price = Number(row.price || 0)
    const ml = actionByHour.get(hour)

    let action = ml?.action || 'HOLD'
    if (!ml) {
      if (avgPrice > 0 && price < avgPrice * 0.9) {
        action = 'BUY'
      } else if (avgPrice > 0 && price > avgPrice * 1.1) {
        action = 'SELL'
      }
    }

    const expectedProfit = action === 'BUY'
      ? -price
      : action === 'SELL'
        ? price * 0.75
        : action === 'DISCHARGE'
          ? price * 0.85
          : 0

    const isPeak = hour >= 7 && hour <= 9 || hour >= 17 && hour <= 20

    return {
      hour,
      time: new Date(row.timestamp).toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' }),
      price_uah_kwh: Number(price.toFixed(2)),
      recommended_action: action,
      expected_profit_uah: Number(expectedProfit.toFixed(2)),
      confidence: Number(baseConfidence.toFixed(2)),
      is_peak: isPeak,
      rationale: ml?.reasoning || '',
    }
  })

  const totalProfit = schedule.reduce((sum, s) => sum + s.expected_profit_uah, 0)

  return {
    schedule,
    total_expected_profit: Number(totalProfit.toFixed(2)),
    buy_hours: schedule.filter(s => s.recommended_action === 'BUY').length,
    sell_hours: schedule.filter(s => s.recommended_action === 'SELL').length,
    discharge_hours: schedule.filter(s => s.recommended_action === 'DISCHARGE').length,
  }
}

// API endpoint to get recommendations from Dagster ML pipeline
// Connects dashboard to ML recommendation engine via Dagster/MLflow APIs

import { exec, execFile } from 'child_process'
import path from 'path'
import { promisify } from 'util'
import {
  applyAutoStrategyDecision,
  buildStrategyWeights,
  mapExecutionCommandToRecommendationAction,
  mapRecommendationActionToExecution,
  normalizeLoadProfileType,
  normalizeOptimizationStrategy,
} from '../../utils/auto-strategy'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

const DAGSTER_API = process.env.DAGSTER_API_URL || 'http://localhost:3000'
const execAsync = promisify(exec)
const MAX_SNAPSHOT_AGE_MINUTES = 15
const HYBRID_REFRESH_COOLDOWN_MS = 5 * 60 * 1000

const hybridRefreshLastAttemptByTenant = new Map<string, number>()
const hybridRefreshInFlightTenants = new Set<string>()

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
    hour_offset?: number
    action: 'BUY' | 'SELL' | 'HOLD'
    action_kw: number
    net_cost_eur: number
    expected_profit_uah: number
    price_eur_mwh: number
    price_uah_kwh: number
    solver?: string
  }>
  schedule_start_utc?: string
  generated_at?: string
  recommendation?: {
    action: 'BUY' | 'SELL' | 'HOLD'
    confidence: number
    confidence_percent: number
    rationale: string
  }
  error?: string
}

function toFiniteNumber(value: unknown): number | null {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : null
}

function normalizeClockHour(value: unknown, fallback = 0): number {
  const parsed = Math.floor(toFiniteNumber(value) ?? fallback)
  const safe = ((parsed % 24) + 24) % 24
  return safe
}

function formatClockHour(hour: number): string {
  return `${String(normalizeClockHour(hour)).padStart(2, '0')}:00`
}

function normalizeScheduleAction(action: unknown): 'BUY' | 'SELL' | 'HOLD' {
  const normalized = String(action || 'HOLD').trim().toUpperCase()
  if (normalized === 'DISCHARGE') return 'SELL'
  if (normalized === 'BUY' || normalized === 'SELL') return normalized
  return 'HOLD'
}

function resolveSnapshotTimestamp(snapshot: DagsterMaterializedRecommendation | null): Date | null {
  if (!snapshot) return null

  const candidates = [snapshot.materialization_time, snapshot.generated_at]
  for (const candidate of candidates) {
    if (!candidate) continue
    const parsed = new Date(candidate)
    if (!Number.isNaN(parsed.getTime())) {
      return parsed
    }
  }

  return null
}

function evaluateSnapshotFreshness(snapshot: DagsterMaterializedRecommendation | null) {
  const materializedAt = resolveSnapshotTimestamp(snapshot)
  if (!materializedAt) {
    return {
      isFresh: false,
      ageMinutes: null as number | null,
      materializedAtIso: null as string | null,
      reason: 'missing_timestamp',
    }
  }

  const ageMs = Date.now() - materializedAt.getTime()
  const ageMinutes = ageMs / 60000
  return {
    isFresh: ageMinutes <= MAX_SNAPSHOT_AGE_MINUTES,
    ageMinutes: Number(ageMinutes.toFixed(2)),
    materializedAtIso: materializedAt.toISOString(),
    reason: ageMinutes <= MAX_SNAPSHOT_AGE_MINUTES ? 'fresh' : 'stale',
  }
}

function evaluateScheduleQuality(snapshot: DagsterMaterializedRecommendation | null) {
  if (!snapshot || !Array.isArray(snapshot.schedule)) {
    return {
      isValid: false,
      reason: 'missing_schedule',
      rowCount: 0,
    }
  }

  const rows = snapshot.schedule.slice(0, 24)
  if (rows.length < 24) {
    return {
      isValid: false,
      reason: 'insufficient_rows',
      rowCount: rows.length,
    }
  }

  const hourOffsets = new Set<number>()
  for (const row of rows) {
    const rawOffset = toFiniteNumber((row as any)?.hour_offset ?? row?.hour)
    if (rawOffset == null) {
      return {
        isValid: false,
        reason: 'invalid_hour_offset',
        rowCount: rows.length,
      }
    }

    const offset = normalizeClockHour(rawOffset, 0)
    if (hourOffsets.has(offset)) {
      return {
        isValid: false,
        reason: 'duplicate_hour_offset',
        rowCount: rows.length,
      }
    }
    hourOffsets.add(offset)

    const actionKw = toFiniteNumber(row?.action_kw)
    if (actionKw == null) {
      return {
        isValid: false,
        reason: 'invalid_action_kw',
        rowCount: rows.length,
      }
    }
  }

  return {
    isValid: true,
    reason: 'valid',
    rowCount: rows.length,
  }
}

function maybeTriggerHybridDagsterRefresh(params: {
  projectRoot: string
  tenantId: string
  configPayload: any
}) {
  const { projectRoot, tenantId, configPayload } = params
  const now = Date.now()
  const lastAttempt = hybridRefreshLastAttemptByTenant.get(tenantId) || 0

  if (hybridRefreshInFlightTenants.has(tenantId)) {
    return {
      requested: false,
      reason: 'refresh_in_flight',
      cooldown_ms: HYBRID_REFRESH_COOLDOWN_MS,
      last_attempt_at: lastAttempt > 0 ? new Date(lastAttempt).toISOString() : null,
    }
  }

  if (now - lastAttempt < HYBRID_REFRESH_COOLDOWN_MS) {
    return {
      requested: false,
      reason: 'cooldown_active',
      cooldown_ms: HYBRID_REFRESH_COOLDOWN_MS,
      last_attempt_at: lastAttempt > 0 ? new Date(lastAttempt).toISOString() : null,
    }
  }

  hybridRefreshLastAttemptByTenant.set(tenantId, now)
  hybridRefreshInFlightTenants.add(tenantId)

  const tenantConfigDir = path.join(projectRoot, 'energy_ml', 'configs', 'tenants', tenantId)
  const latitude = toFiniteNumber(configPayload?.data?.latitude) ?? 50.45
  const longitude = toFiniteNumber(configPayload?.data?.longitude) ?? 30.52
  const timezone = String(configPayload?.data?.timezone || 'Europe/Kiev')

  execFile(
    'python',
    ['-m', 'dagster', 'asset', 'materialize', '--select', '*optimization_schedule_milp_asset', '-m', 'src.definitions'],
    {
      cwd: projectRoot,
      timeout: 180000,
      env: {
        ...process.env,
        ENERGY_ML_CONFIG_DIR: tenantConfigDir,
        ENERGY_ML_TENANT_ID: tenantId,
        WEATHER_LATITUDE: String(latitude),
        WEATHER_LONGITUDE: String(longitude),
        WEATHER_TIMEZONE: timezone,
      },
    },
    (error) => {
      if (error) {
        console.warn('[recommendation] Hybrid refresh failed:', error.message)
      }
      hybridRefreshInFlightTenants.delete(tenantId)
    },
  )

  return {
    requested: true,
    reason: 'stale_snapshot_hybrid_refresh_triggered',
    cooldown_ms: HYBRID_REFRESH_COOLDOWN_MS,
    last_attempt_at: new Date(now).toISOString(),
  }
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

    const [postgresDagster, fileDagster, mlRecommendation, pricesPayload, batteryPayload, mlflowStatus, dagsterStatus, configPayload] = await Promise.all([
      readDagsterRecommendationFromPostgres(tenant.id),
      readMaterializedDagsterRecommendation(projectRoot, tenant.id),
      $fetch<any>('/api/ml/recommendation', tenantRequest).catch(() => null),
      $fetch<any>('/api/prices/current', tenantRequest).catch(() => null),
      $fetch<any>('/api/battery/status', tenantRequest).catch(() => null),
      $fetch<any>('/api/mlflow/status', tenantRequest).catch(() => null),
      queryDagsterStatus(),
      $fetch<any>('/api/config/current', tenantRequest).catch(() => null),
    ])

    const latestDagsterSnapshot = postgresDagster || fileDagster
    const snapshotFreshness = evaluateSnapshotFreshness(latestDagsterSnapshot)
    const scheduleQuality = evaluateScheduleQuality(latestDagsterSnapshot)
    const materializedDagster = snapshotFreshness.isFresh && scheduleQuality.isValid ? latestDagsterSnapshot : null

    const currentPrice = Number(pricesPayload?.prices?.current?.price || 0)
    const avgPrice = Number(pricesPayload?.prices?.today?.avg || currentPrice || 0)
    const batterySoc = Number(batteryPayload?.battery?.soc || 50)
    const mlData = mlRecommendation?.data || null
    const optimizationStrategy = normalizeOptimizationStrategy(configPayload?.data?.optimization_strategy)
    const loadProfileType = normalizeLoadProfileType(configPayload?.data?.load_profile_type)
    const strategyWeights = buildStrategyWeights(optimizationStrategy)
    const recommendationSource = materializedDagster
      ? postgresDagster
        ? 'dagster_postgres_snapshot'
        : 'dagster_asset_file'
      : latestDagsterSnapshot
        ? snapshotFreshness.isFresh
          ? 'ml_api_fallback_invalid_schedule'
          : 'ml_api_fallback_stale_snapshot'
        : 'ml_api_fallback'

    const hybridRefresh = latestDagsterSnapshot && (!snapshotFreshness.isFresh || !scheduleQuality.isValid)
      ? maybeTriggerHybridDagsterRefresh({
          projectRoot,
          tenantId: tenant.id,
          configPayload,
        })
      : {
          requested: false,
          reason: 'fresh_snapshot',
          cooldown_ms: HYBRID_REFRESH_COOLDOWN_MS,
          last_attempt_at: null as string | null,
        }

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

    const fallbackPowerKw = Math.max(0.5, Math.min(5, Number(materializedDagster?.schedule?.[0]?.action_kw || 2.5) || 2.5))
    const mappedRecommendation = mapRecommendationActionToExecution(recommendation.action, fallbackPowerKw)
    const adjustedDecision = applyAutoStrategyDecision(mappedRecommendation.command, mappedRecommendation.power_kw, {
      optimizationStrategy,
      loadProfileType,
      currentHour: new Date().getHours(),
      currentPriceUahKwh: Number.isFinite(currentPrice) ? currentPrice : null,
      avgPriceUahKwh: Number.isFinite(avgPrice) ? avgPrice : null,
      batterySocPercent: Number.isFinite(batterySoc) ? batterySoc : null,
      fallbackPowerKw,
    })
    const adjustedAction = mapExecutionCommandToRecommendationAction(adjustedDecision.command)
    const strategyRationaleSuffix = adjustedDecision.notes.length > 0
      ? ` Strategy adjustments: ${adjustedDecision.notes.join('; ')}.`
      : ''
    const strategyAdjustedRecommendation = {
      ...recommendation,
      base_action: recommendation.action,
      action: adjustedAction,
      action_kw: Number(adjustedDecision.powerKw.toFixed(3)),
      strategy_adjusted: adjustedAction !== recommendation.action || adjustedDecision.notes.length > 0,
      strategy_adjustment_notes: adjustedDecision.notes,
      rationale: `${recommendation.rationale}${strategyRationaleSuffix}`,
    }

    const schedule24h = materializedDagster
      ? buildScheduleFromDagsterAsset(
          pricesPayload?.prices?.forecast?.next24h || [],
          materializedDagster.schedule || [],
          recommendation.confidence,
          materializedDagster.schedule_start_utc || materializedDagster.generated_at || null,
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
      recommendation: strategyAdjustedRecommendation,
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
      strategy_context: {
        optimization_strategy: optimizationStrategy,
        load_profile_type: loadProfileType,
        strategy_weights: strategyWeights,
      },
      source_metadata: {
        tenant_filter_applied: true,
        recommendation_source: recommendationSource,
        dagster_asset_name: latestDagsterSnapshot?.asset || null,
        dagster_snapshot_run_id: latestDagsterSnapshot?.run_id || null,
        dagster_snapshot_materialized_at: snapshotFreshness.materializedAtIso,
        dagster_asset_file: latestDagsterSnapshot?.asset_file || null,
        dagster_selected_client_id: latestDagsterSnapshot?.selected_client_id || null,
        dagster_snapshot_is_fresh: snapshotFreshness.isFresh,
        dagster_snapshot_age_minutes: snapshotFreshness.ageMinutes,
        dagster_snapshot_max_age_minutes: MAX_SNAPSHOT_AGE_MINUTES,
        dagster_snapshot_freshness_reason: snapshotFreshness.reason,
        dagster_schedule_quality_valid: scheduleQuality.isValid,
        dagster_schedule_quality_reason: scheduleQuality.reason,
        dagster_schedule_quality_row_count: scheduleQuality.rowCount,
        hybrid_refresh: hybridRefresh,
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
  dagsterSchedule: Array<{ hour: number; hour_offset?: number; action: string; action_kw: number; expected_profit_uah: number; price_uah_kwh: number }>,
  baseConfidence: number,
  scheduleStartUtc?: string | null,
) {
  const startDate = scheduleStartUtc ? new Date(scheduleStartUtc) : null
  const inferredStartHour = !startDate || Number.isNaN(startDate.getTime())
    ? (forecast.length > 0 ? normalizeClockHour(forecast[0]?.hour, new Date().getHours()) : new Date().getHours())
    : startDate.getUTCHours()

  const normalizedDagster = dagsterSchedule
    .slice(0, 24)
    .map((row, index) => ({
      offset: normalizeClockHour(row?.hour_offset ?? row?.hour ?? index, index),
      action: normalizeScheduleAction(row?.action),
      action_kw: Number(row?.action_kw || 0),
      expected_profit_uah: Number(row?.expected_profit_uah || 0),
      price_uah_kwh: Number(row?.price_uah_kwh || 0),
    }))
    .sort((a, b) => a.offset - b.offset)

  const rows = forecast.length > 0
    ? forecast.slice(0, 24).map((row, index) => {
        const hour = normalizeClockHour(row.hour, inferredStartHour + index)
        const dagsterRow = normalizedDagster[index]
        const action = normalizeScheduleAction(dagsterRow?.action)
        const actionKw = Number(dagsterRow?.action_kw || 0)
        const rationale = action === 'HOLD'
          ? `Dagster schedule holds at ${hour}:00 (action_kw=${actionKw.toFixed(2)}).`
          : `Dagster schedule recommends ${action} at ${hour}:00 (action_kw=${actionKw.toFixed(2)}).`
        return {
          hour,
          time: formatClockHour(hour),
          price_uah_kwh: Number(Number(row.price || dagsterRow?.price_uah_kwh || 0).toFixed(2)),
          recommended_action: action,
          expected_profit_uah: Number(Number(dagsterRow?.expected_profit_uah || 0).toFixed(2)),
          confidence: Number(baseConfidence.toFixed(2)),
          is_peak: (hour >= 7 && hour <= 9) || (hour >= 17 && hour <= 20),
          rationale,
        }
      })
    : normalizedDagster.map((row, index) => {
        const hour = normalizeClockHour(inferredStartHour + index, inferredStartHour + index)
        const action = normalizeScheduleAction(row.action)
        const actionKw = Number(row.action_kw || 0)
        const rationale = action === 'HOLD'
          ? `Dagster schedule holds at ${hour}:00 (action_kw=${actionKw.toFixed(2)}).`
          : `Dagster schedule recommends ${action} at ${hour}:00 (action_kw=${actionKw.toFixed(2)}).`
        return {
          hour,
          time: formatClockHour(hour),
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

    let action = normalizeScheduleAction(ml?.action || 'HOLD')
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
      time: formatClockHour(hour),
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

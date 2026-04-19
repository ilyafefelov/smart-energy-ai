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
import {
  buildStrictDagsterTenantPredicate,
  dagsterAssetResultsHasTenantColumn,
  dagsterAssetResultsTableExists,
  resolveDagsterAssetResultsDbConfig,
} from '../../utils/dagster-asset-results'
import {
  evaluateScheduleQuality,
  evaluateSnapshotFreshness,
  selectDagsterSnapshotCandidate,
} from '../../utils/dagster-snapshot'
import {
  assessDagsterScheduleRowPolicy,
  formatClockHour,
  normalizeClockHour,
  normalizeScheduleAction,
} from '../../utils/dagster-schedule-policy'
import { assessStage2MarketPolicy, inferReserveFloorPercent, inferSitePowerKw } from '../../utils/market-policy'
import {
  type BatteryPayload,
  buildDecisionProvenance,
  buildNormalizedAction,
  type ConfigPayload,
  type MlflowStatusPayload,
  normalizeDecisionSource,
  normalizeServingMetadata,
  type PricesPayload,
  resolveTenantLocationConfig,
  toFiniteNumber,
  type ServingContract,
} from '../../utils/recommendation-contract'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

const DAGSTER_API = process.env.DAGSTER_API_URL || 'http://localhost:3000'
const execAsync = promisify(exec)
const MAX_SNAPSHOT_AGE_MINUTES = 15
const HYBRID_REFRESH_COOLDOWN_MS = 5 * 60 * 1000

const hybridRefreshLastAttemptByTenant = new Map<string, number>()
const hybridRefreshInFlightTenants = new Set<string>()

type DagsterForecastProvenance = {
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
  generated_at?: string
  recommendation?: {
    action: 'BUY' | 'SELL' | 'HOLD'
    confidence: number
    confidence_percent: number
    rationale: string
  }
  error?: string
}

type MlRecommendationPayload = {
  serving?: unknown
  data?: {
    action?: string | null
    confidence?: number | null
    reasoning?: string | null
    daily_forecast?: Array<{ hour: number; action?: string; reasoning?: string }> | null
    model_info?: {
      version?: string | null
    } | null
    provenance?: {
      decision_source?: string | null
      state_source?: string | null
      state_source_detail?: string | null
    } | null
  } | null
}

function toNullableText(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const normalized = value.trim()
  return normalized.length > 0 ? normalized : null
}

function toNullableBoolean(value: unknown): boolean | null {
  if (typeof value === 'boolean') return value
  if (value == null) return null
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase()
    if (normalized === 'true') return true
    if (normalized === 'false') return false
  }
  return Boolean(value)
}

function resolveDagsterForecastProvenance(value: unknown): DagsterForecastProvenance {
  const row = value && typeof value === 'object' ? value as Record<string, unknown> : {}
  return {
    forecast_run_id: toNullableText(row.forecast_run_id),
    forecast_model_name: toNullableText(row.forecast_model_name),
    forecast_model_family: toNullableText(row.forecast_model_family),
    forecast_model_version: toNullableText(row.forecast_model_version),
    forecast_horizon_mode: toNullableText(row.forecast_horizon_mode),
    forecast_uncertainty_source: toNullableText(row.forecast_uncertainty_source),
    forecast_promotion_active: toNullableBoolean(row.forecast_promotion_active),
    forecast_promotion_source: toNullableText(row.forecast_promotion_source),
    optimization_run_id: toNullableText(row.optimization_run_id),
  }
}

function summarizeDagsterForecastProvenance(rows: Array<Record<string, unknown>> | null | undefined): DagsterForecastProvenance {
  for (const row of rows || []) {
    const provenance = resolveDagsterForecastProvenance(row)
    if (
      provenance.forecast_run_id != null
      || provenance.forecast_model_name != null
      || provenance.forecast_model_family != null
      || provenance.forecast_model_version != null
      || provenance.forecast_horizon_mode != null
      || provenance.forecast_uncertainty_source != null
      || provenance.forecast_promotion_active != null
      || provenance.forecast_promotion_source != null
      || provenance.optimization_run_id != null
    ) {
      return provenance
    }
  }

  return {
    forecast_run_id: null,
    forecast_model_name: null,
    forecast_model_family: null,
    forecast_model_version: null,
    forecast_horizon_mode: null,
    forecast_uncertainty_source: null,
    forecast_promotion_active: null,
    forecast_promotion_source: null,
    optimization_run_id: null,
  }
}

function maybeTriggerHybridDagsterRefresh(params: {
  projectRoot: string
  tenantId: string
  configPayload: ConfigPayload | null
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
  const tenantLocation = resolveTenantLocationConfig(configPayload?.data)

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
        WEATHER_LATITUDE: String(tenantLocation.latitude),
        WEATHER_LONGITUDE: String(tenantLocation.longitude),
        WEATHER_TIMEZONE: tenantLocation.timezone,
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

export default defineEventHandler(async (event): Promise<Record<string, unknown>> => {
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

    const [postgresDagster, fileDagster, mlRecommendation, pricesPayload, batteryPayload, mlflowStatus, dagsterStatus, configPayload]: [
      DagsterMaterializedRecommendation | null,
      DagsterMaterializedRecommendation | null,
      MlRecommendationPayload | null,
      PricesPayload | null,
      BatteryPayload | null,
      MlflowStatusPayload | null,
      Awaited<ReturnType<typeof queryDagsterStatus>>,
      ConfigPayload | null,
    ] = await Promise.all([
      readDagsterRecommendationFromPostgres(tenant.id),
      readMaterializedDagsterRecommendation(projectRoot, tenant.id),
      // Fetch the live ML bridge eagerly for fallback and enrichment. A fresh Dagster snapshot remains the decision authority.
      $fetch<MlRecommendationPayload>('/api/ml/recommendation', tenantRequest).catch(() => null),
      $fetch<PricesPayload>('/api/prices/current', tenantRequest).catch(() => null),
      $fetch<BatteryPayload>('/api/battery/status', tenantRequest).catch(() => null),
      $fetch<MlflowStatusPayload>('/api/mlflow/status', tenantRequest).catch(() => null),
      queryDagsterStatus(),
      $fetch<ConfigPayload>('/api/config/current', tenantRequest).catch(() => null),
    ])

    const dagsterSnapshotCandidates = selectDagsterSnapshotCandidate(
      postgresDagster,
      fileDagster,
      MAX_SNAPSHOT_AGE_MINUTES,
    )
    const selectedDagsterCandidate = dagsterSnapshotCandidates.selected
    const activeDagsterCandidate = selectedDagsterCandidate || dagsterSnapshotCandidates.latest
    const materializedDagster = selectedDagsterCandidate?.snapshot || null
    const activeDagsterSnapshot = activeDagsterCandidate?.snapshot || null
    const snapshotFreshness = activeDagsterCandidate?.freshness || evaluateSnapshotFreshness(null, MAX_SNAPSHOT_AGE_MINUTES)
    const scheduleQuality = activeDagsterCandidate?.quality || evaluateScheduleQuality(null)
    const serving = normalizeServingMetadata(mlRecommendation?.serving)

    const currentPrice = Number(pricesPayload?.prices?.current?.price || 0)
    const avgPrice = Number(pricesPayload?.prices?.today?.avg || currentPrice || 0)
    const batterySoc = Number(batteryPayload?.battery?.soc || 50)
    const tenantLocation = resolveTenantLocationConfig(configPayload?.data)
    const mlData = mlRecommendation?.data || null
    const optimizationStrategy = normalizeOptimizationStrategy(configPayload?.data?.optimization_strategy)
    const loadProfileType = normalizeLoadProfileType(configPayload?.data?.load_profile_type)
    const strategyWeights = buildStrategyWeights(optimizationStrategy)
    const recommendationSourceDetail = materializedDagster
      ? selectedDagsterCandidate?.sourceDetail || 'dagster_asset_file'
      : activeDagsterCandidate
        ? snapshotFreshness.isFresh
          ? 'ml_api_fallback_invalid_schedule'
          : 'ml_api_fallback_stale_snapshot'
        : 'ml_api_fallback'

    const hybridRefresh = activeDagsterCandidate && !selectedDagsterCandidate
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
    const fallbackReasonCode = materializedDagster
      ? 'none'
      : activeDagsterCandidate
        ? !snapshotFreshness.isFresh
          ? 'dagster_snapshot_stale'
          : `dagster_schedule_${scheduleQuality.reason}`
        : mlData
          ? 'dagster_snapshot_missing'
          : 'dagster_and_ml_unavailable'
    const fallbackDecisionSource = mlData
      ? normalizeDecisionSource(mlData?.provenance?.decision_source || 'python_rule_engine', 'python_rule_engine')
      : 'heuristic_fallback'
    const provenance = buildDecisionProvenance({
      decisionSource: materializedDagster ? 'dagster_optimizer' : fallbackDecisionSource,
      fallbackReasonCode,
      stateSource: mlData?.provenance?.state_source || batteryPayload?.source_metadata?.state_source || 'simulator_backed_telemetry',
      stateSourceDetail:
        mlData?.provenance?.state_source_detail
        || batteryPayload?.source_metadata?.state_source_detail
        || batteryPayload?.source
        || 'api/battery/status',
    })

    const recommendation = materializedDagster
      ? {
          action: materializedDagster.recommendation?.action || 'HOLD',
          confidence: Number(materializedDagster.recommendation?.confidence || 0.8),
          confidence_percent: Math.round(Number(materializedDagster.recommendation?.confidence || 0.8) * 100),
          rationale: materializedDagster.recommendation?.rationale || `Dagster asset recommendation from ${materializedDagster.asset}`,
          decision_source: provenance.decision_source,
          fallback_reason_code: provenance.fallback_reason_code,
        }
      : {
          action: mlData?.action || 'HOLD',
          confidence: Number(mlData?.confidence || 0.5),
          confidence_percent: Math.round(Number(mlData?.confidence || 0.5) * 100),
          rationale: mlData?.reasoning || 'Recommendation unavailable - holding position',
          decision_source: provenance.decision_source,
          fallback_reason_code: provenance.fallback_reason_code,
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
    const policyCompliance = assessStage2MarketPolicy({
      action: strategyAdjustedRecommendation.action,
      powerKw: strategyAdjustedRecommendation.action_kw,
      batterySocPercent: Number.isFinite(batterySoc) ? batterySoc : null,
      batteryCapacityKwh: configPayload?.data?.battery_capacity_kwh ?? batteryPayload?.battery?.capacity,
      reserveFloorPercent: inferReserveFloorPercent(configPayload?.data || null),
      sitePowerKw: inferSitePowerKw(configPayload?.data || null),
      marketRegimeOverride: configPayload?.data?.market_regime_override,
      timestamp: new Date().toISOString(),
      timezone: tenantLocation.timezone,
    })
    const policyAdjustedRecommendation = {
      ...strategyAdjustedRecommendation,
      action: policyCompliance.adjusted_action,
      action_kw: policyCompliance.adjusted_power_kw ?? strategyAdjustedRecommendation.action_kw,
      strategy_adjusted: strategyAdjustedRecommendation.strategy_adjusted || policyCompliance.veto_applied,
      strategy_adjustment_notes: [
        ...strategyAdjustedRecommendation.strategy_adjustment_notes,
        ...policyCompliance.explanations,
      ],
      rationale: `${strategyAdjustedRecommendation.rationale}${policyCompliance.reasoning_suffix}`,
    }
    const contract = {
      version: 'learned_policy_migration_v1',
      normalized_action: buildNormalizedAction({
        action: policyAdjustedRecommendation.action,
        baseAction: policyAdjustedRecommendation.base_action,
        confidence: policyAdjustedRecommendation.confidence,
        powerKw: policyAdjustedRecommendation.action_kw,
        strategyAdjusted: policyAdjustedRecommendation.strategy_adjusted,
        strategyAdjustmentNotes: policyAdjustedRecommendation.strategy_adjustment_notes,
        powerSource: policyCompliance.veto_applied ? 'stage2_market_policy' : 'strategy_adjusted_schedule',
      }),
      provenance,
      strategy_context: {
        optimization_strategy: optimizationStrategy,
        load_profile_type: loadProfileType,
        strategy_weights: strategyWeights,
      },
      compliance: policyCompliance,
    }

    const schedule24h = materializedDagster
      ? buildScheduleFromDagsterAsset(
          pricesPayload?.prices?.forecast?.next24h || [],
          materializedDagster.schedule || [],
          recommendation.confidence,
          materializedDagster.schedule_start_utc || materializedDagster.generated_at || null,
          configPayload?.data || null,
        )
      : buildDeterministicSchedule(
          pricesPayload?.prices?.forecast?.next24h || [],
          mlData?.daily_forecast || [],
          recommendation.confidence,
          configPayload?.data || null,
        )

    const dagsterForecastProvenance = materializedDagster
      ? summarizeDagsterForecastProvenance(materializedDagster.schedule as Array<Record<string, unknown>> | undefined)
      : summarizeDagsterForecastProvenance(undefined)

    const activeModel = mlflowStatus?.active_model || null
    const modelInfo = {
      type: materializedDagster ? 'dagster_schedule' : provenance.decision_source,
      version:
        typeof serving.model_info?.resolved_model_uri === 'string'
          ? serving.model_info.resolved_model_uri
          : mlData?.model_info?.version || contract.version,
      last_trained: serving.active_mode === 'learned_policy' ? activeModel?.last_updated || null : null,
      accuracy_percent: Number(recommendation.confidence_percent || 0),
      mlflow_available: mlflowStatus?.mlflow_connected === true,
      registry_metadata_authoritative: false,
      serving_mode: serving.active_mode,
      requested_serving_mode: serving.requested_mode,
      serving_adapter: serving.adapter,
      resolved_model_uri: typeof serving.model_info?.resolved_model_uri === 'string'
        ? serving.model_info.resolved_model_uri
        : null,
    }

    return {
      status: 'success',
      timestamp: new Date().toISOString(),
      tenant: getTenantResponseMetadata(tenant),
      recommendation: {
        ...policyAdjustedRecommendation,
        normalized_action: contract.normalized_action,
        policy_compliance: policyCompliance,
      },
      contract,
      current_state: {
        price_uah_kwh: currentPrice,
        battery_soc_percent: batterySoc,
        time: new Date().toLocaleTimeString('uk-UA'),
      },
      schedule_24h: schedule24h,
      model_info: modelInfo,
      serving,
      provenance,
      lineage: {
        data_sources: 5,
        total_features: 73,
        data_provenance: 'OREE prices, Open-Meteo weather, simulator-backed battery telemetry, and config-derived load and renewable estimates',
      },
      monitoring: {
        needs_retraining: Boolean(mlflowStatus?.monitoring?.drift_detected),
        drift_detected: false,
        last_check: new Date().toISOString(),
        mlflow_role: mlflowStatus?.service_role || 'registry_and_experiment_diagnostics',
      },
      dagster_status: dagsterStatus,
      strategy_context: {
        optimization_strategy: optimizationStrategy,
        load_profile_type: loadProfileType,
        strategy_weights: strategyWeights,
      },
      source_metadata: {
        tenant_filter_applied: true,
        recommendation_source: provenance.decision_source,
        recommendation_source_detail: recommendationSourceDetail,
        contract_version: contract.version,
        dagster_asset_name: activeDagsterSnapshot?.asset || null,
        dagster_snapshot_run_id: activeDagsterSnapshot?.run_id || null,
        dagster_snapshot_materialized_at: snapshotFreshness.materializedAtIso,
        dagster_asset_file: activeDagsterSnapshot?.asset_file || null,
        dagster_selected_client_id: activeDagsterSnapshot?.selected_client_id || null,
        dagster_forecast_run_id: dagsterForecastProvenance.forecast_run_id,
        dagster_forecast_model_name: dagsterForecastProvenance.forecast_model_name,
        dagster_forecast_model_family: dagsterForecastProvenance.forecast_model_family,
        dagster_forecast_model_version: dagsterForecastProvenance.forecast_model_version,
        dagster_forecast_horizon_mode: dagsterForecastProvenance.forecast_horizon_mode,
        dagster_forecast_uncertainty_source: dagsterForecastProvenance.forecast_uncertainty_source,
        dagster_forecast_promotion_active: dagsterForecastProvenance.forecast_promotion_active,
        dagster_forecast_promotion_source: dagsterForecastProvenance.forecast_promotion_source,
        dagster_optimization_run_id: dagsterForecastProvenance.optimization_run_id,
        dagster_snapshot_is_fresh: snapshotFreshness.isFresh,
        dagster_snapshot_age_minutes: snapshotFreshness.ageMinutes,
        dagster_snapshot_max_age_minutes: MAX_SNAPSHOT_AGE_MINUTES,
        dagster_snapshot_freshness_reason: snapshotFreshness.reason,
        dagster_schedule_quality_valid: scheduleQuality.isValid,
        dagster_schedule_quality_reason: scheduleQuality.reason,
        dagster_schedule_quality_row_count: scheduleQuality.rowCount,
        fallback_reason_code: provenance.fallback_reason_code,
        fallback_used: provenance.fallback_used,
        state_source: provenance.state_source,
        state_source_detail: provenance.state_source_detail,
        telemetry_classification: provenance.telemetry_classification,
        market_regime: policyCompliance.market_regime,
        policy_rule_hits: policyCompliance.rule_hits,
        policy_veto_applied: policyCompliance.veto_applied,
        hybrid_refresh: hybridRefresh,
        serving_requested_mode: serving.requested_mode,
        serving_active_mode: serving.active_mode,
        serving_adapter: serving.adapter,
        serving_fallback_used: serving.fallback_used,
        serving_fallback_reason_code: serving.fallback_reason_code,
        serving_resolved_model_uri: typeof serving.model_info?.resolved_model_uri === 'string'
          ? serving.model_info.resolved_model_uri
          : null,
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
  dagsterSchedule: Array<{
    hour: number
    hour_offset?: number
    action: string
    action_kw: number
    expected_profit_uah: number
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
  } & DagsterForecastProvenance>,
  baseConfidence: number,
  scheduleStartUtc?: string | null,
  configData?: Record<string, any> | null,
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
      soc_before_kwh: toFiniteNumber((row as any)?.soc_before_kwh),
      soc_after_kwh: toFiniteNumber((row as any)?.soc_after_kwh),
      charge_kwh: toFiniteNumber((row as any)?.charge_kwh),
      discharge_kwh: toFiniteNumber((row as any)?.discharge_kwh),
      throughput_total_kwh: toFiniteNumber((row as any)?.throughput_total_kwh),
      grid_import_kwh: toFiniteNumber((row as any)?.grid_import_kwh),
      grid_export_kwh: toFiniteNumber((row as any)?.grid_export_kwh),
      purchase_cost_eur: toFiniteNumber((row as any)?.purchase_cost_eur),
      export_revenue_eur: toFiniteNumber((row as any)?.export_revenue_eur),
      degradation_penalty_eur: toFiniteNumber((row as any)?.degradation_penalty_eur),
      load_kwh: toFiniteNumber((row as any)?.load_kwh),
      solar_kwh: toFiniteNumber((row as any)?.solar_kwh),
      ...resolveDagsterForecastProvenance(row),
    }))
    .sort((a, b) => a.offset - b.offset)

  const rows = forecast.length > 0
    ? forecast.slice(0, 24).map((row, index) => {
        const hour = normalizeClockHour(row.hour, inferredStartHour + index)
        const dagsterRow = normalizedDagster[index]
        const assessment = assessDagsterScheduleRowPolicy(dagsterRow || { hour_offset: hour }, {
          config: configData,
          batteryCapacityKwh: configData?.battery_capacity_kwh,
          scheduleStartUtc,
        })
        const requestedAction = assessment.requestedAction
        const requestedActionKw = Number(assessment.requestedPowerKw || 0)
        const action = assessment.policyCompliance.adjusted_action
        const adjustedActionKw = Number(assessment.policyCompliance.adjusted_power_kw ?? requestedActionKw)
        const requestedProfit = Number(dagsterRow?.expected_profit_uah || 0)
        const adjustedProfit = action === requestedAction ? requestedProfit : 0
        const rationale = action === requestedAction
          ? (
              action === 'HOLD'
                ? `Dagster schedule holds at ${hour}:00 (action_kw=${requestedActionKw.toFixed(2)}).${assessment.policyCompliance.reasoning_suffix}`
                : `Dagster schedule recommends ${action} at ${hour}:00 (action_kw=${requestedActionKw.toFixed(2)}).${assessment.policyCompliance.reasoning_suffix}`
            )
          : `Dagster schedule requested ${requestedAction} at ${hour}:00 (action_kw=${requestedActionKw.toFixed(2)}), adjusted to ${action}.${assessment.policyCompliance.reasoning_suffix}`
        return {
          hour,
          hour_offset: dagsterRow?.offset ?? index,
          time: formatClockHour(hour),
          price_uah_kwh: Number(Number(row.price || dagsterRow?.price_uah_kwh || 0).toFixed(2)),
          recommended_action: action,
          requested_action: requestedAction,
          action_kw: Number(adjustedActionKw.toFixed(2)),
          requested_action_kw: Number(requestedActionKw.toFixed(2)),
          expected_profit_uah: Number(adjustedProfit.toFixed(2)),
          requested_profit_uah: Number(requestedProfit.toFixed(2)),
          confidence: Number(baseConfidence.toFixed(2)),
          is_peak: (hour >= 7 && hour <= 9) || (hour >= 17 && hour <= 20),
          rationale,
          market_regime: assessment.policyCompliance.market_regime,
          policy_compliance: assessment.policyCompliance,
          soc_before_kwh: dagsterRow?.soc_before_kwh ?? null,
          soc_after_kwh: dagsterRow?.soc_after_kwh ?? null,
          grid_export_kwh: dagsterRow?.grid_export_kwh ?? null,
          grid_import_kwh: dagsterRow?.grid_import_kwh ?? null,
          forecast_run_id: dagsterRow?.forecast_run_id ?? null,
          forecast_model_name: dagsterRow?.forecast_model_name ?? null,
          forecast_model_family: dagsterRow?.forecast_model_family ?? null,
          forecast_model_version: dagsterRow?.forecast_model_version ?? null,
          forecast_horizon_mode: dagsterRow?.forecast_horizon_mode ?? null,
          forecast_uncertainty_source: dagsterRow?.forecast_uncertainty_source ?? null,
          forecast_promotion_active: dagsterRow?.forecast_promotion_active ?? null,
          forecast_promotion_source: dagsterRow?.forecast_promotion_source ?? null,
          optimization_run_id: dagsterRow?.optimization_run_id ?? null,
        }
      })
    : normalizedDagster.map((row, index) => {
        const hour = normalizeClockHour(inferredStartHour + index, inferredStartHour + index)
        const assessment = assessDagsterScheduleRowPolicy(row, {
          config: configData,
          batteryCapacityKwh: configData?.battery_capacity_kwh,
          scheduleStartUtc,
        })
        const requestedAction = assessment.requestedAction
        const requestedActionKw = Number(assessment.requestedPowerKw || 0)
        const action = assessment.policyCompliance.adjusted_action
        const adjustedActionKw = Number(assessment.policyCompliance.adjusted_power_kw ?? requestedActionKw)
        const requestedProfit = Number(row.expected_profit_uah || 0)
        const adjustedProfit = action === requestedAction ? requestedProfit : 0
        const rationale = action === requestedAction
          ? (
              action === 'HOLD'
                ? `Dagster schedule holds at ${hour}:00 (action_kw=${requestedActionKw.toFixed(2)}).${assessment.policyCompliance.reasoning_suffix}`
                : `Dagster schedule recommends ${action} at ${hour}:00 (action_kw=${requestedActionKw.toFixed(2)}).${assessment.policyCompliance.reasoning_suffix}`
            )
          : `Dagster schedule requested ${requestedAction} at ${hour}:00 (action_kw=${requestedActionKw.toFixed(2)}), adjusted to ${action}.${assessment.policyCompliance.reasoning_suffix}`
        return {
          hour,
          hour_offset: row.offset,
          time: formatClockHour(hour),
          price_uah_kwh: Number(Number(row.price_uah_kwh || 0).toFixed(2)),
          recommended_action: action,
          requested_action: requestedAction,
          action_kw: Number(adjustedActionKw.toFixed(2)),
          requested_action_kw: Number(requestedActionKw.toFixed(2)),
          expected_profit_uah: Number(adjustedProfit.toFixed(2)),
          requested_profit_uah: Number(requestedProfit.toFixed(2)),
          confidence: Number(baseConfidence.toFixed(2)),
          is_peak: (hour >= 7 && hour <= 9) || (hour >= 17 && hour <= 20),
          rationale,
          market_regime: assessment.policyCompliance.market_regime,
          policy_compliance: assessment.policyCompliance,
          soc_before_kwh: row.soc_before_kwh ?? null,
          soc_after_kwh: row.soc_after_kwh ?? null,
          grid_export_kwh: row.grid_export_kwh ?? null,
          grid_import_kwh: row.grid_import_kwh ?? null,
          forecast_run_id: row.forecast_run_id ?? null,
          forecast_model_name: row.forecast_model_name ?? null,
          forecast_model_family: row.forecast_model_family ?? null,
          forecast_model_version: row.forecast_model_version ?? null,
          forecast_horizon_mode: row.forecast_horizon_mode ?? null,
          forecast_uncertainty_source: row.forecast_uncertainty_source ?? null,
          forecast_promotion_active: row.forecast_promotion_active ?? null,
          forecast_promotion_source: row.forecast_promotion_source ?? null,
          optimization_run_id: row.optimization_run_id ?? null,
        }
      })

  const totalProfit = rows.reduce((sum, row) => sum + Number(row.expected_profit_uah || 0), 0)
  return {
    schedule: rows,
    total_expected_profit: Number(totalProfit.toFixed(2)),
    buy_hours: rows.filter((row) => row.recommended_action === 'BUY').length,
    sell_hours: rows.filter((row) => row.recommended_action === 'SELL').length,
    discharge_hours: rows.filter((row) => row.recommended_action === 'SELL').length,
  }
}

function buildDeterministicSchedule(
  forecast: Array<{ hour: number; timestamp: string; price: number }>,
  mlForecast: Array<{ hour: number; action?: string; reasoning?: string }>,
  baseConfidence: number,
  configData?: Record<string, any> | null,
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

  const schedule = safeForecast.map((row, index) => {
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
        : 0

    const requestedAction = action
    const tenantLocation = resolveTenantLocationConfig(configData)
    const policyCompliance = assessStage2MarketPolicy({
      action: requestedAction,
      batteryCapacityKwh: configData?.battery_capacity_kwh,
      reserveFloorPercent: inferReserveFloorPercent(configData || null),
      sitePowerKw: inferSitePowerKw(configData || null),
      marketRegimeOverride: configData?.market_regime_override,
      timestamp: row.timestamp,
      timezone: tenantLocation.timezone,
    })

    const adjustedAction = policyCompliance.adjusted_action
    const adjustedProfit = adjustedAction === requestedAction ? expectedProfit : 0

    const isPeak = hour >= 7 && hour <= 9 || hour >= 17 && hour <= 20

    return {
      hour,
      hour_offset: index,
      time: formatClockHour(hour),
      price_uah_kwh: Number(price.toFixed(2)),
      recommended_action: adjustedAction,
      requested_action: requestedAction,
      action_kw: Number(policyCompliance.adjusted_power_kw || 0),
      requested_action_kw: Number(policyCompliance.adjusted_power_kw || 0),
      expected_profit_uah: Number(adjustedProfit.toFixed(2)),
      requested_profit_uah: Number(expectedProfit.toFixed(2)),
      confidence: Number(baseConfidence.toFixed(2)),
      is_peak: isPeak,
      rationale: policyCompliance.veto_applied
        ? `${ml?.reasoning || ''}${ml?.reasoning ? ' ' : ''}${policyCompliance.reasoning_suffix}`.trim()
        : (ml?.reasoning || ''),
      market_regime: policyCompliance.market_regime,
      policy_compliance: policyCompliance,
    }
  })

  const totalProfit = schedule.reduce((sum, s) => sum + s.expected_profit_uah, 0)

  return {
    schedule,
    total_expected_profit: Number(totalProfit.toFixed(2)),
    buy_hours: schedule.filter(s => s.recommended_action === 'BUY').length,
    sell_hours: schedule.filter(s => s.recommended_action === 'SELL').length,
    discharge_hours: schedule.filter(s => s.recommended_action === 'SELL').length,
  }
}

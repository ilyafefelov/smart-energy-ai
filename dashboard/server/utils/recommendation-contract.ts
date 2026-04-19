export type CanonicalDecisionSource =
  | 'dagster_optimizer'
  | 'python_rule_engine'
  | 'ml_recommendation'
  | 'heuristic_fallback'
  | 'manual_override'

export type CanonicalStateSource = 'simulator_backed_telemetry' | 'config_fallback'

export type CanonicalRecommendationAction = 'BUY' | 'SELL' | 'HOLD'
export type CanonicalExecutionCommand = 'charge' | 'discharge' | 'hold'

export type ServingContract = {
  requested_mode: string
  active_mode: string
  adapter: string
  fallback_used: boolean
  fallback_reason_code: string
  model_info: Record<string, any> | null
}

export type PriceForecastPoint = {
  hour: number
  timestamp: string
  price: number
}

export type PricesPayload = {
  success?: boolean
  prices?: {
    current?: {
      price?: number | null
    } | null
    today?: {
      avg?: number | null
    } | null
    forecast?: {
      next24h?: PriceForecastPoint[] | null
    } | null
  } | null
}

export type BatteryPayload = {
  battery?: {
    soc?: number | null
    capacity?: number | null
    health?: number | null
  } | null
  source_metadata?: {
    state_source?: string | null
    state_source_detail?: string | null
  } | null
  source?: string | null
}

export type MlflowStatusPayload = {
  active_model?: {
    last_updated?: string | null
  } | null
  mlflow_connected?: boolean | null
  monitoring?: {
    drift_detected?: boolean | null
  } | null
  service_role?: string | null
}

export type ConfigPayload = {
  data?: Record<string, any> | null
}

export type TenantLocationConfig = {
  latitude: number
  longitude: number
  timezone: string
}

type DecisionProvenanceInput = {
  decisionSource: unknown
  fallbackReasonCode?: unknown
  stateSource?: unknown
  stateSourceDetail?: unknown
}

type NormalizedActionInput = {
  action: unknown
  confidence?: unknown
  powerKw?: unknown
  baseAction?: unknown
  strategyAdjusted?: unknown
  strategyAdjustmentNotes?: unknown
  powerSource?: unknown
}

const DECISION_SOURCE_MAP: Record<string, CanonicalDecisionSource> = {
  dagster: 'dagster_optimizer',
  dagster_asset_file: 'dagster_optimizer',
  dagster_optimizer: 'dagster_optimizer',
  dagster_postgres_snapshot: 'dagster_optimizer',
  heuristic: 'heuristic_fallback',
  heuristic_fallback: 'heuristic_fallback',
  manual: 'manual_override',
  manual_input: 'manual_override',
  manual_override: 'manual_override',
  ml: 'ml_recommendation',
  ml_recommendation: 'ml_recommendation',
  python: 'python_rule_engine',
  python_controller: 'python_rule_engine',
  python_rule_engine: 'python_rule_engine',
  rule_engine: 'python_rule_engine',
}

const STATE_SOURCE_MAP: Record<string, CanonicalStateSource> = {
  'api/battery/status': 'simulator_backed_telemetry',
  battery_status_fallback: 'simulator_backed_telemetry',
  simulator: 'simulator_backed_telemetry',
  simulator_backed: 'simulator_backed_telemetry',
  simulator_backed_telemetry: 'simulator_backed_telemetry',
  synthetic: 'config_fallback',
  config: 'config_fallback',
  config_fallback: 'config_fallback',
  fallback: 'config_fallback',
}

const FALLBACK_REASON_MAP: Record<string, string> = {
  '': 'none',
  none: 'none',
  fresh_snapshot: 'none',
  missing_timestamp: 'dagster_snapshot_missing_timestamp',
  stale_snapshot_hybrid_refresh_triggered: 'dagster_snapshot_stale',
  invalid_schedule: 'dagster_schedule_invalid',
  missing_schedule: 'dagster_schedule_missing',
  insufficient_rows: 'dagster_schedule_insufficient_rows',
  invalid_action_kw: 'dagster_schedule_invalid_action_kw',
  invalid_hour_offset: 'dagster_schedule_invalid_hour_offset',
  duplicate_hour_offset: 'dagster_schedule_duplicate_hour_offset',
  python_script_missing: 'python_script_missing',
  python_execution_failed: 'python_execution_failed',
  python_unavailable: 'python_unavailable',
}

const DEFAULT_TENANT_LATITUDE = 50.45
const DEFAULT_TENANT_LONGITUDE = 30.52
const DEFAULT_TENANT_TIMEZONE = 'Europe/Kiev'

export function normalizeDecisionSource(
  value: unknown,
  fallback: CanonicalDecisionSource = 'heuristic_fallback',
): CanonicalDecisionSource {
  const normalized = String(value || '').trim().toLowerCase()
  return DECISION_SOURCE_MAP[normalized] || fallback
}

export function normalizeStateSource(
  value: unknown,
  fallback: CanonicalStateSource = 'config_fallback',
): CanonicalStateSource {
  const normalized = String(value || '').trim().toLowerCase()
  return STATE_SOURCE_MAP[normalized] || fallback
}

export function normalizeFallbackReasonCode(value: unknown): string {
  const normalized = String(value || '').trim().toLowerCase()
  return FALLBACK_REASON_MAP[normalized] || normalized || 'none'
}

export function resolveTenantLocationConfig(
  configData: Record<string, any> | null | undefined,
): TenantLocationConfig {
  return {
    latitude: toFiniteNumber(configData?.latitude) ?? DEFAULT_TENANT_LATITUDE,
    longitude: toFiniteNumber(configData?.longitude) ?? DEFAULT_TENANT_LONGITUDE,
    timezone: String(configData?.timezone || DEFAULT_TENANT_TIMEZONE),
  }
}

export function sanitizeTimezone(timezone: string | null | undefined): string {
  if (!timezone || typeof timezone !== 'string') return DEFAULT_TENANT_TIMEZONE
  const normalized = timezone.trim()
  if (!normalized) return DEFAULT_TENANT_TIMEZONE
  return normalized.replace(/[^A-Za-z0-9_\-/+]/g, '') || DEFAULT_TENANT_TIMEZONE
}

export function normalizeRecommendationAction(
  value: unknown,
  fallback: CanonicalRecommendationAction = 'HOLD',
): CanonicalRecommendationAction {
  const normalized = String(value || '').trim().toUpperCase()
  if (normalized === 'BUY' || normalized === 'CHARGE') return 'BUY'
  if (normalized === 'SELL' || normalized === 'DISCHARGE') return 'SELL'
  return fallback
}

export function mapRecommendationActionToExecutionCommand(
  action: CanonicalRecommendationAction,
): CanonicalExecutionCommand {
  if (action === 'BUY') return 'charge'
  if (action === 'SELL') return 'discharge'
  return 'hold'
}

export function toFiniteNumber(value: unknown): number | null {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : null
}

export function normalizeServingMetadata(value: unknown): ServingContract {
  const serving = value && typeof value === 'object' ? value as Record<string, any> : {}
  const modelInfo = serving.model_info && typeof serving.model_info === 'object'
    ? serving.model_info as Record<string, any>
    : null

  return {
    requested_mode: typeof serving.requested_mode === 'string' ? serving.requested_mode : 'incumbent',
    active_mode: typeof serving.active_mode === 'string' ? serving.active_mode : 'incumbent',
    adapter: typeof serving.adapter === 'string' ? serving.adapter : 'PredictionService',
    fallback_used: Boolean(serving.fallback_used),
    fallback_reason_code: typeof serving.fallback_reason_code === 'string' ? serving.fallback_reason_code : 'none',
    model_info: modelInfo,
  }
}

export function buildNormalizedAction(input: NormalizedActionInput) {
  const action = normalizeRecommendationAction(input.action)
  const baseAction = normalizeRecommendationAction(input.baseAction ?? input.action)
  const executionCommand = mapRecommendationActionToExecutionCommand(action)
  const confidenceValue = Number(input.confidence)
  const confidence = Number.isFinite(confidenceValue)
    ? Math.max(0, Math.min(1, confidenceValue))
    : null
  const powerValue = Number(input.powerKw)
  const powerKw = executionCommand === 'hold'
    ? 0
    : Number.isFinite(powerValue)
      ? Number(powerValue.toFixed(3))
      : null

  return {
    action,
    base_action: baseAction,
    execution_command: executionCommand,
    power_kw: powerKw,
    power_source: String(
      input.powerSource
      || (executionCommand === 'hold' ? 'hold_zero' : powerKw == null ? 'not_provided' : 'provided'),
    ),
    confidence,
    confidence_percent: confidence == null ? null : Math.round(confidence * 100),
    strategy_adjusted: Boolean(input.strategyAdjusted),
    strategy_adjustment_notes: Array.isArray(input.strategyAdjustmentNotes)
      ? input.strategyAdjustmentNotes.map((note) => String(note))
      : [],
  }
}

export function buildDecisionProvenance(input: DecisionProvenanceInput) {
  const stateSource = normalizeStateSource(input.stateSource)
  const fallbackReasonCode = normalizeFallbackReasonCode(input.fallbackReasonCode)

  return {
    decision_source: normalizeDecisionSource(input.decisionSource),
    fallback_reason_code: fallbackReasonCode,
    fallback_used: fallbackReasonCode !== 'none',
    state_source: stateSource,
    state_source_detail: input.stateSourceDetail ? String(input.stateSourceDetail) : null,
    telemetry_classification:
      stateSource === 'simulator_backed_telemetry'
        ? 'simulated_operational_telemetry'
        : 'fabricated_training_scaffolding',
  }
}
import { Pool } from 'pg'
import { createHash } from 'node:crypto'

export const DECISION_SNAPSHOT_VERSION = 'decision_snapshot_v1' as const

export type DecisionSnapshotAction = 'BUY' | 'SELL' | 'HOLD'

export type DecisionSnapshotNormalizedAction = {
  action: DecisionSnapshotAction | null
  base_action: DecisionSnapshotAction | null
  execution_command: string | null
  power_kw: number | null
  power_source: string | null
  confidence: number | null
  confidence_percent: number | null
  strategy_adjusted: boolean | null
  strategy_adjustment_notes: string[]
}

export type DecisionSnapshotPolicyCompliance = {
  policy_version: string | null
  market_regime: string | null
  reserve_floor_percent: number | null
  export_targeted: boolean | null
  export_allowed: boolean | null
  veto_applied: boolean | null
  adjusted_action: DecisionSnapshotAction | null
  adjusted_power_kw: number | null
  rule_hits: string[]
  explanations: string[]
}

export type DecisionSnapshotContract = {
  version: string | null
  normalized_action: DecisionSnapshotNormalizedAction | null
  policy_compliance: DecisionSnapshotPolicyCompliance | null
}

export type DecisionSnapshot = {
  version: typeof DECISION_SNAPSHOT_VERSION
  tenant_id: string | null
  timestamp: string
  decision_source: string | null
  recommendation_source: string | null
  selected_action: DecisionSnapshotAction | null
  selected_power_kw: number | null
  current_price_uah_kwh: number | null
  avg_price_uah_kwh: number | null
  battery_soc_percent: number | null
  battery_health_percent: number | null
  battery_temp_c: number | null
  estimated_load_kw: number | null
  estimated_solar_kw: number | null
  optimization_strategy: string | null
  load_profile_type: string | null
  fallback_reason: string | null
  previous_action: DecisionSnapshotAction | null
  provenance: {
    state_source: string | null
    state_source_detail: string | null
    telemetry_classification: string | null
    recommendation_contract_version: string | null
  }
  contract: DecisionSnapshotContract
}

export type DecisionSnapshotInput = {
  tenant_id?: unknown
  timestamp?: unknown
  decision_source?: unknown
  recommendation_source?: unknown
  selected_action?: unknown
  selected_power_kw?: unknown
  current_price_uah_kwh?: unknown
  avg_price_uah_kwh?: unknown
  battery_soc_percent?: unknown
  battery_health_percent?: unknown
  battery_temp_c?: unknown
  estimated_load_kw?: unknown
  estimated_solar_kw?: unknown
  optimization_strategy?: unknown
  load_profile_type?: unknown
  fallback_reason?: unknown
  previous_action?: unknown
  provenance?: {
    state_source?: unknown
    state_source_detail?: unknown
    telemetry_classification?: unknown
    recommendation_contract_version?: unknown
  } | null
  contract?: {
    version?: unknown
    normalized_action?: {
      action?: unknown
      base_action?: unknown
      execution_command?: unknown
      power_kw?: unknown
      power_source?: unknown
      confidence?: unknown
      confidence_percent?: unknown
      strategy_adjusted?: unknown
      strategy_adjustment_notes?: unknown
    } | null
    compliance?: {
      policy_version?: unknown
      market_regime?: unknown
      reserve_floor_percent?: unknown
      export_targeted?: unknown
      export_allowed?: unknown
      veto_applied?: unknown
      adjusted_action?: unknown
      adjusted_power_kw?: unknown
      rule_hits?: unknown
      explanations?: unknown
    } | null
    policy_compliance?: {
      policy_version?: unknown
      market_regime?: unknown
      reserve_floor_percent?: unknown
      export_targeted?: unknown
      export_allowed?: unknown
      veto_applied?: unknown
      adjusted_action?: unknown
      adjusted_power_kw?: unknown
      rule_hits?: unknown
      explanations?: unknown
    } | null
  } | null
}

export type OptimizationHistoryInsert = {
  execution_key: string
  command_id: string | null
  schedule_id: string | null
  tenant_id: string | null
  execution_source: string
  timestamp: string
  predicted_action: number
  actual_action: number | null
  cost_baseline: number | null
  cost_rl: number | null
  price_uah_kwh: number | null
  duration_minutes: number | null
  energy_kwh: number | null
  economics_method: string | null
  economics_version: string | null
  fallback_reason: string | null
  price_source: string | null
  tariff_window: string | null
  interval_start: string | null
  interval_end: string | null
  battery_soc_start: number | null
  battery_soc_end: number | null
  solar_actual: number | null
  load_actual: number | null
  forecast_run_id?: string | null
  forecast_model_version?: string | null
  optimization_run_id?: string | null
  decision_source?: string | null
  execution_status?: string | null
  event_type?: string | null
  mode_from?: string | null
  mode_to?: string | null
  realized_revenue_uah?: number | null
  realized_cost_uah?: number | null
  realized_net_uah?: number | null
  decision_snapshot?: DecisionSnapshot | null
  is_reconciled?: boolean
  reconciled_at?: string | null
  reconciliation_note?: string | null
}

export type PersistOptimizationHistoryResult = {
  ok: boolean
  inserted: boolean
  updated: boolean
  reconciled: boolean
  executionKey: string
  reconciliationNote?: string | null
  error?: string
}

type OptimizationHistoryStoredRow = OptimizationHistoryInsert

export type OptimizationHistoryInitializationResult = {
  available: boolean
  initialized: boolean
  degraded: boolean
  reason?: string
}

type ExecutionKeyInput = {
  commandId: string | null
  scheduleId: string | null
  tenantId: string | null
  timestamp: string
  command: string
  powerKw: number
  durationMinutes: number | null
  userId: string
  reason: string
  source: string
}

type DbConfig = {
  host: string
  port: number
  user: string
  password: string
  database: string
}

let pool: any | null = null
let initPromise: Promise<any | null> | null = null
let schemaInitializationPromise: Promise<OptimizationHistoryInitializationResult> | null = null
let schemaInitialized = false
let unavailableReason: string | null = null
let loggedUnavailableMode = false

const EXECUTION_STATUS_PRIORITY: Record<string, number> = {
  pending: 1,
  scheduled: 1,
  executing: 2,
  failed: 3,
  executed: 4,
}

function getNestedErrors(error: unknown): unknown[] {
  if (!error || typeof error !== 'object') {
    return []
  }

  const candidate = error as { errors?: unknown }
  return Array.isArray(candidate.errors) ? candidate.errors : []
}

function getErrorMessage(error: unknown): string {
  const nestedErrors = getNestedErrors(error)
  if (nestedErrors.length > 0) {
    const nestedMessages = nestedErrors
      .map((nestedError) => getErrorMessage(nestedError))
      .filter(Boolean)

    if (nestedMessages.length > 0) {
      return nestedMessages.join('; ')
    }
  }

  if (error instanceof Error && error.message) {
    return error.message
  }

  return String(error || '')
}

function isOptimizationDbUnavailable(error: unknown): boolean {
  const nestedErrors = getNestedErrors(error)
  if (nestedErrors.length > 0) {
    return nestedErrors.some((nestedError) => isOptimizationDbUnavailable(nestedError))
  }

  if (!error || typeof error !== 'object') {
    return false
  }

  const candidate = error as { code?: unknown; errno?: unknown; message?: unknown }
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

async function resetOptimizationPool(): Promise<void> {
  const currentPool = pool
  pool = null

  if (currentPool) {
    await currentPool.end().catch(() => {})
  }
}

async function markOptimizationHistoryUnavailable(reason: string): Promise<void> {
  unavailableReason = reason
  schemaInitialized = false
  await resetOptimizationPool()

  if (!loggedUnavailableMode) {
    console.warn('[optimization-history] Degraded mode enabled:', reason)
    loggedUnavailableMode = true
  }
}

function normalizeNullableText(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null
  }
  const normalized = value.trim()
  return normalized ? normalized : null
}

function normalizeFiniteNumber(value: unknown): number | null {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : null
}

function normalizeNullableBoolean(value: unknown): boolean | null {
  if (typeof value === 'boolean') {
    return value
  }

  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase()
    if (normalized === 'true') {
      return true
    }
    if (normalized === 'false') {
      return false
    }
  }

  return null
}

function normalizeInteger(value: unknown): number | null {
  const numeric = Number(value)
  return Number.isInteger(numeric) ? numeric : null
}

function normalizeStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return []
  }

  return value
    .map((item) => normalizeNullableText(item))
    .filter((item): item is string => Boolean(item))
}

function normalizeTimestamp(value: unknown, fallback = new Date().toISOString()): string {
  if (typeof value === 'string') {
    const parsed = new Date(value)
    if (Number.isFinite(parsed.getTime())) {
      return parsed.toISOString()
    }
  }

  return fallback
}

function preferDefined<T>(...values: Array<T | null | undefined>): T | null {
  for (const value of values) {
    if (value !== null && value !== undefined) {
      return value
    }
  }

  return null
}

function normalizeSnapshotAction(value: unknown): DecisionSnapshotAction | null {
  const normalized = String(value || '').trim().toUpperCase()
  if (normalized === 'BUY' || normalized === 'CHARGE') {
    return 'BUY'
  }
  if (normalized === 'SELL' || normalized === 'DISCHARGE') {
    return 'SELL'
  }
  if (normalized === 'HOLD' || normalized === 'AUTO') {
    return 'HOLD'
  }
  return null
}

function normalizeDecisionSnapshotNormalizedAction(value: DecisionSnapshotInput['contract'] extends infer T ? any : never): DecisionSnapshotNormalizedAction | null {
  const normalized: DecisionSnapshotNormalizedAction = {
    action: normalizeSnapshotAction(value?.action),
    base_action: normalizeSnapshotAction(value?.base_action),
    execution_command: normalizeNullableText(value?.execution_command),
    power_kw: normalizeFiniteNumber(value?.power_kw),
    power_source: normalizeNullableText(value?.power_source),
    confidence: normalizeFiniteNumber(value?.confidence),
    confidence_percent: normalizeInteger(value?.confidence_percent),
    strategy_adjusted: normalizeNullableBoolean(value?.strategy_adjusted),
    strategy_adjustment_notes: normalizeStringArray(value?.strategy_adjustment_notes),
  }

  const hasData = normalized.action
    || normalized.base_action
    || normalized.execution_command
    || normalized.power_kw !== null
    || normalized.power_source
    || normalized.confidence !== null
    || normalized.confidence_percent !== null
    || normalized.strategy_adjusted !== null
    || normalized.strategy_adjustment_notes.length > 0

  return hasData ? normalized : null
}

function normalizeDecisionSnapshotPolicyCompliance(value: DecisionSnapshotInput['contract'] extends infer T ? any : never): DecisionSnapshotPolicyCompliance | null {
  const normalized: DecisionSnapshotPolicyCompliance = {
    policy_version: normalizeNullableText(value?.policy_version),
    market_regime: normalizeNullableText(value?.market_regime),
    reserve_floor_percent: normalizeFiniteNumber(value?.reserve_floor_percent),
    export_targeted: normalizeNullableBoolean(value?.export_targeted),
    export_allowed: normalizeNullableBoolean(value?.export_allowed),
    veto_applied: normalizeNullableBoolean(value?.veto_applied),
    adjusted_action: normalizeSnapshotAction(value?.adjusted_action),
    adjusted_power_kw: normalizeFiniteNumber(value?.adjusted_power_kw),
    rule_hits: normalizeStringArray(value?.rule_hits),
    explanations: normalizeStringArray(value?.explanations),
  }

  const hasData = normalized.policy_version
    || normalized.market_regime
    || normalized.reserve_floor_percent !== null
    || normalized.export_targeted !== null
    || normalized.export_allowed !== null
    || normalized.veto_applied !== null
    || normalized.adjusted_action
    || normalized.adjusted_power_kw !== null
    || normalized.rule_hits.length > 0
    || normalized.explanations.length > 0

  return hasData ? normalized : null
}

function countSnapshotCompleteness(snapshot: DecisionSnapshot | null | undefined): number {
  if (!snapshot) {
    return 0
  }

  const values = [
    snapshot.tenant_id,
    snapshot.decision_source,
    snapshot.recommendation_source,
    snapshot.selected_action,
    snapshot.selected_power_kw,
    snapshot.current_price_uah_kwh,
    snapshot.avg_price_uah_kwh,
    snapshot.battery_soc_percent,
    snapshot.battery_health_percent,
    snapshot.battery_temp_c,
    snapshot.estimated_load_kw,
    snapshot.estimated_solar_kw,
    snapshot.optimization_strategy,
    snapshot.load_profile_type,
    snapshot.fallback_reason,
    snapshot.previous_action,
    snapshot.provenance.state_source,
    snapshot.provenance.state_source_detail,
    snapshot.provenance.telemetry_classification,
    snapshot.provenance.recommendation_contract_version,
    snapshot.contract.version,
    snapshot.contract.normalized_action?.action,
    snapshot.contract.normalized_action?.base_action,
    snapshot.contract.normalized_action?.execution_command,
    snapshot.contract.normalized_action?.power_kw,
    snapshot.contract.normalized_action?.power_source,
    snapshot.contract.normalized_action?.confidence,
    snapshot.contract.normalized_action?.confidence_percent,
    snapshot.contract.normalized_action?.strategy_adjusted,
    snapshot.contract.policy_compliance?.policy_version,
    snapshot.contract.policy_compliance?.market_regime,
    snapshot.contract.policy_compliance?.reserve_floor_percent,
    snapshot.contract.policy_compliance?.export_targeted,
    snapshot.contract.policy_compliance?.export_allowed,
    snapshot.contract.policy_compliance?.veto_applied,
    snapshot.contract.policy_compliance?.adjusted_action,
    snapshot.contract.policy_compliance?.adjusted_power_kw,
  ]

  return values.reduce<number>((count, value) => (value !== null && value !== undefined ? count + 1 : count), 0)
}

function normalizeExecutionStatus(value: unknown): string | null {
  const normalized = normalizeNullableText(value)?.toLowerCase()
  return normalized || null
}

function pickExecutionStatus(existing: unknown, incoming: unknown): string | null {
  const normalizedExisting = normalizeExecutionStatus(existing)
  const normalizedIncoming = normalizeExecutionStatus(incoming)

  if (!normalizedExisting) {
    return normalizedIncoming
  }
  if (!normalizedIncoming) {
    return normalizedExisting
  }

  return (EXECUTION_STATUS_PRIORITY[normalizedIncoming] || 0) >= (EXECUTION_STATUS_PRIORITY[normalizedExisting] || 0)
    ? normalizedIncoming
    : normalizedExisting
}

export function mapDecisionSnapshotActionToOptimizationAction(action: DecisionSnapshotAction | null): number {
  if (action === 'BUY') {
    return 0
  }
  if (action === 'SELL') {
    return 1
  }
  return 4
}

export function buildDecisionSnapshot(input: DecisionSnapshotInput): DecisionSnapshot {
  const normalizedAction = normalizeDecisionSnapshotNormalizedAction(input.contract?.normalized_action)
  const policyCompliance = normalizeDecisionSnapshotPolicyCompliance(
    input.contract?.policy_compliance || input.contract?.compliance,
  )

  return {
    version: DECISION_SNAPSHOT_VERSION,
    tenant_id: normalizeNullableText(input.tenant_id),
    timestamp: normalizeTimestamp(input.timestamp),
    decision_source: normalizeNullableText(input.decision_source),
    recommendation_source: normalizeNullableText(input.recommendation_source),
    selected_action: normalizeSnapshotAction(input.selected_action),
    selected_power_kw: normalizeFiniteNumber(input.selected_power_kw),
    current_price_uah_kwh: normalizeFiniteNumber(input.current_price_uah_kwh),
    avg_price_uah_kwh: normalizeFiniteNumber(input.avg_price_uah_kwh),
    battery_soc_percent: normalizeFiniteNumber(input.battery_soc_percent),
    battery_health_percent: normalizeFiniteNumber(input.battery_health_percent),
    battery_temp_c: normalizeFiniteNumber(input.battery_temp_c),
    estimated_load_kw: normalizeFiniteNumber(input.estimated_load_kw),
    estimated_solar_kw: normalizeFiniteNumber(input.estimated_solar_kw),
    optimization_strategy: normalizeNullableText(input.optimization_strategy),
    load_profile_type: normalizeNullableText(input.load_profile_type),
    fallback_reason: normalizeNullableText(input.fallback_reason),
    previous_action: normalizeSnapshotAction(input.previous_action),
    provenance: {
      state_source: normalizeNullableText(input.provenance?.state_source),
      state_source_detail: normalizeNullableText(input.provenance?.state_source_detail),
      telemetry_classification: normalizeNullableText(input.provenance?.telemetry_classification),
      recommendation_contract_version: normalizeNullableText(input.provenance?.recommendation_contract_version),
    },
    contract: {
      version: normalizeNullableText(input.contract?.version),
      normalized_action: normalizedAction,
      policy_compliance: policyCompliance,
    },
  }
}

export function mergeDecisionSnapshots(
  existing: DecisionSnapshot | null | undefined,
  incoming: DecisionSnapshot | null | undefined,
): DecisionSnapshot | null {
  if (!existing && !incoming) {
    return null
  }
  if (!existing) {
    return incoming || null
  }
  if (!incoming) {
    return existing
  }

  return countSnapshotCompleteness(incoming) >= countSnapshotCompleteness(existing) ? incoming : existing
}

function normalizeOptimizationHistoryEntry(entry: OptimizationHistoryInsert): OptimizationHistoryInsert {
  const decisionSnapshot = entry.decision_snapshot ? buildDecisionSnapshot(entry.decision_snapshot) : null
  const selectedAction = decisionSnapshot?.selected_action || null

  return {
    execution_key: entry.execution_key,
    command_id: normalizeNullableText(entry.command_id),
    schedule_id: normalizeNullableText(entry.schedule_id),
    tenant_id: normalizeNullableText(entry.tenant_id) || decisionSnapshot?.tenant_id || null,
    execution_source: normalizeNullableText(entry.execution_source) || 'unknown',
    timestamp: normalizeTimestamp(entry.timestamp),
    predicted_action:
      normalizeInteger(entry.predicted_action)
      ?? mapDecisionSnapshotActionToOptimizationAction(selectedAction),
    actual_action: normalizeInteger(entry.actual_action),
    cost_baseline: normalizeFiniteNumber(entry.cost_baseline),
    cost_rl: normalizeFiniteNumber(entry.cost_rl),
    price_uah_kwh: normalizeFiniteNumber(entry.price_uah_kwh),
    duration_minutes: normalizeInteger(entry.duration_minutes),
    energy_kwh: normalizeFiniteNumber(entry.energy_kwh),
    economics_method: normalizeNullableText(entry.economics_method),
    economics_version: normalizeNullableText(entry.economics_version),
    fallback_reason: normalizeNullableText(entry.fallback_reason) || decisionSnapshot?.fallback_reason || null,
    price_source: normalizeNullableText(entry.price_source),
    tariff_window: normalizeNullableText(entry.tariff_window),
    interval_start: normalizeNullableText(entry.interval_start),
    interval_end: normalizeNullableText(entry.interval_end),
    battery_soc_start: normalizeFiniteNumber(entry.battery_soc_start),
    battery_soc_end: normalizeFiniteNumber(entry.battery_soc_end),
    solar_actual: normalizeFiniteNumber(entry.solar_actual),
    load_actual: normalizeFiniteNumber(entry.load_actual),
    forecast_run_id: normalizeNullableText(entry.forecast_run_id),
    forecast_model_version: normalizeNullableText(entry.forecast_model_version),
    optimization_run_id: normalizeNullableText(entry.optimization_run_id),
    decision_source: normalizeNullableText(entry.decision_source) || decisionSnapshot?.decision_source || null,
    execution_status: normalizeExecutionStatus(entry.execution_status),
    event_type: normalizeNullableText(entry.event_type),
    mode_from: normalizeNullableText(entry.mode_from),
    mode_to: normalizeNullableText(entry.mode_to),
    realized_revenue_uah: normalizeFiniteNumber(entry.realized_revenue_uah),
    realized_cost_uah: normalizeFiniteNumber(entry.realized_cost_uah),
    realized_net_uah: normalizeFiniteNumber(entry.realized_net_uah),
    decision_snapshot: decisionSnapshot,
    is_reconciled: Boolean(entry.is_reconciled),
    reconciled_at: normalizeNullableText(entry.reconciled_at),
    reconciliation_note: normalizeNullableText(entry.reconciliation_note),
  }
}

export function reconcileOptimizationHistoryEntry(
  existing: OptimizationHistoryStoredRow | null,
  incoming: OptimizationHistoryInsert,
  reconciledAtIso = new Date().toISOString(),
): { entry: OptimizationHistoryInsert; reconciled: boolean; reconciliationNote: string | null } {
  const normalizedIncoming = normalizeOptimizationHistoryEntry(incoming)
  if (!existing) {
    return {
      entry: normalizedIncoming,
      reconciled: false,
      reconciliationNote: normalizedIncoming.reconciliation_note ?? null,
    }
  }

  const normalizedExisting = normalizeOptimizationHistoryEntry(existing)
  const mergedSnapshot = mergeDecisionSnapshots(normalizedExisting.decision_snapshot, normalizedIncoming.decision_snapshot)
  const reconciliationReasons: string[] = []

  if (normalizedExisting.execution_status === 'scheduled' && normalizedIncoming.execution_status && normalizedIncoming.execution_status !== 'scheduled') {
    reconciliationReasons.push('scheduled_intent_reconciled')
  }
  if (normalizedExisting.actual_action == null && normalizedIncoming.actual_action != null) {
    reconciliationReasons.push('actual_action_backfilled')
  }
  if (normalizedExisting.realized_net_uah == null && normalizedIncoming.realized_net_uah != null) {
    reconciliationReasons.push('realized_economics_backfilled')
  }
  if (!normalizedExisting.decision_snapshot && Boolean(mergedSnapshot)) {
    reconciliationReasons.push('decision_snapshot_attached')
  }

  const reconciled = reconciliationReasons.length > 0
  const reconciliationNote = preferDefined(
    normalizeNullableText(normalizedIncoming.reconciliation_note),
    normalizeNullableText(normalizedExisting.reconciliation_note),
    reconciled ? reconciliationReasons.join('; ') : null,
  )

  return {
    entry: {
      execution_key: normalizedIncoming.execution_key,
      command_id: preferDefined(normalizedIncoming.command_id, normalizedExisting.command_id),
      schedule_id: preferDefined(normalizedIncoming.schedule_id, normalizedExisting.schedule_id),
      tenant_id: preferDefined(normalizedIncoming.tenant_id, normalizedExisting.tenant_id),
      execution_source: normalizedIncoming.execution_source,
      timestamp: preferDefined(normalizedExisting.timestamp, normalizedIncoming.timestamp) || normalizedIncoming.timestamp,
      predicted_action: preferDefined(
        normalizeInteger(normalizedIncoming.predicted_action),
        normalizeInteger(normalizedExisting.predicted_action),
        mapDecisionSnapshotActionToOptimizationAction(mergedSnapshot?.selected_action || null),
      ) ?? 4,
      actual_action: preferDefined(normalizedIncoming.actual_action, normalizedExisting.actual_action),
      cost_baseline: preferDefined(normalizedIncoming.cost_baseline, normalizedExisting.cost_baseline),
      cost_rl: preferDefined(normalizedIncoming.cost_rl, normalizedExisting.cost_rl),
      price_uah_kwh: preferDefined(normalizedIncoming.price_uah_kwh, normalizedExisting.price_uah_kwh),
      duration_minutes: preferDefined(normalizedIncoming.duration_minutes, normalizedExisting.duration_minutes),
      energy_kwh: preferDefined(normalizedIncoming.energy_kwh, normalizedExisting.energy_kwh),
      economics_method: preferDefined(normalizedIncoming.economics_method, normalizedExisting.economics_method),
      economics_version: preferDefined(normalizedIncoming.economics_version, normalizedExisting.economics_version),
      fallback_reason: preferDefined(normalizedIncoming.fallback_reason, normalizedExisting.fallback_reason),
      price_source: preferDefined(normalizedIncoming.price_source, normalizedExisting.price_source),
      tariff_window: preferDefined(normalizedIncoming.tariff_window, normalizedExisting.tariff_window),
      interval_start: preferDefined(normalizedIncoming.interval_start, normalizedExisting.interval_start),
      interval_end: preferDefined(normalizedIncoming.interval_end, normalizedExisting.interval_end),
      battery_soc_start: preferDefined(normalizedIncoming.battery_soc_start, normalizedExisting.battery_soc_start),
      battery_soc_end: preferDefined(normalizedIncoming.battery_soc_end, normalizedExisting.battery_soc_end),
      solar_actual: preferDefined(normalizedIncoming.solar_actual, normalizedExisting.solar_actual),
      load_actual: preferDefined(normalizedIncoming.load_actual, normalizedExisting.load_actual),
      forecast_run_id: preferDefined(normalizedIncoming.forecast_run_id, normalizedExisting.forecast_run_id),
      forecast_model_version: preferDefined(normalizedIncoming.forecast_model_version, normalizedExisting.forecast_model_version),
      optimization_run_id: preferDefined(normalizedIncoming.optimization_run_id, normalizedExisting.optimization_run_id),
      decision_source: preferDefined(normalizedIncoming.decision_source, normalizedExisting.decision_source),
      execution_status: pickExecutionStatus(normalizedExisting.execution_status, normalizedIncoming.execution_status),
      event_type: preferDefined(normalizedIncoming.event_type, normalizedExisting.event_type),
      mode_from: preferDefined(normalizedIncoming.mode_from, normalizedExisting.mode_from),
      mode_to: preferDefined(normalizedIncoming.mode_to, normalizedExisting.mode_to),
      realized_revenue_uah: preferDefined(normalizedIncoming.realized_revenue_uah, normalizedExisting.realized_revenue_uah),
      realized_cost_uah: preferDefined(normalizedIncoming.realized_cost_uah, normalizedExisting.realized_cost_uah),
      realized_net_uah: preferDefined(normalizedIncoming.realized_net_uah, normalizedExisting.realized_net_uah),
      decision_snapshot: mergedSnapshot,
      is_reconciled: Boolean(normalizedExisting.is_reconciled || normalizedIncoming.is_reconciled || reconciled),
      reconciled_at:
        normalizedExisting.is_reconciled || normalizedIncoming.is_reconciled || reconciled
          ? preferDefined(normalizedIncoming.reconciled_at, normalizedExisting.reconciled_at, reconciledAtIso)
          : null,
      reconciliation_note: reconciliationNote,
    },
    reconciled,
    reconciliationNote,
  }
}

export function buildOptimizationExecutionKey(input: ExecutionKeyInput): string {
  const scheduleId = normalizeNullableText(input.scheduleId)
  const commandId = normalizeNullableText(input.commandId)
  const tenantId = normalizeNullableText(input.tenantId) || ''
  const canonicalPayload = scheduleId
    ? ['schedule', tenantId, scheduleId].join('|')
    : commandId
      ? ['command', tenantId, commandId].join('|')
      : [
          'derived',
          tenantId,
          input.timestamp,
          input.command,
          Number(input.powerKw).toFixed(6),
          input.durationMinutes == null ? '' : String(Math.round(input.durationMinutes)),
          input.userId,
          input.reason,
          input.source,
        ].join('|')

  const digest = createHash('sha256').update(canonicalPayload).digest('hex')
  return `exec_${digest.slice(0, 40)}`
}

function sanitizeDbIdentifier(value: string): string {
  return value.replace(/[^a-zA-Z0-9_]/g, '')
}

export function resolveOptimizationDbConfig(): DbConfig {
  const database = process.env.APP_DB_NAME || process.env.OPTIMIZATION_DB_NAME || 'smart_energy_ai'

  const databaseUrl = process.env.DATABASE_URL
  if (databaseUrl?.startsWith('postgres://') || databaseUrl?.startsWith('postgresql://')) {
    try {
      const parsed = new URL(databaseUrl)
      return {
        host: parsed.hostname || process.env.DB_HOST || 'localhost',
        port: Number(parsed.port || process.env.DB_PORT || 5432),
        user: decodeURIComponent(parsed.username || process.env.DB_USER || 'dagster'),
        password: decodeURIComponent(parsed.password || process.env.DB_PASSWORD || 'dagster'),
        database: sanitizeDbIdentifier(database),
      }
    } catch {
      // Fall through to env defaults.
    }
  }

  return {
    host: process.env.APP_DB_HOST || process.env.DB_HOST || 'localhost',
    port: Number(process.env.APP_DB_PORT || process.env.DB_PORT || 5432),
    user: process.env.APP_DB_USER || process.env.DB_USER || 'dagster',
    password: process.env.APP_DB_PASSWORD || process.env.DB_PASSWORD || 'dagster',
    database: sanitizeDbIdentifier(database),
  }
}

async function ensureSchema(optimizationPool: any): Promise<void> {
  await optimizationPool.query(`
    CREATE TABLE IF NOT EXISTS optimization_history (
      id SERIAL PRIMARY KEY,
      execution_key VARCHAR(64) NOT NULL,
      command_id VARCHAR(128),
      schedule_id VARCHAR(128),
      tenant_id VARCHAR(128),
      execution_source VARCHAR(64) NOT NULL DEFAULT 'unknown',
      timestamp TIMESTAMP NOT NULL,
      predicted_action INTEGER NOT NULL,
      actual_action INTEGER,
      cost_baseline DOUBLE PRECISION,
      cost_rl DOUBLE PRECISION,
      price_uah_kwh DOUBLE PRECISION,
      duration_minutes INTEGER,
      energy_kwh DOUBLE PRECISION,
      economics_method VARCHAR(64),
      economics_version VARCHAR(64),
      fallback_reason TEXT,
      price_source VARCHAR(64),
      tariff_window VARCHAR(32),
      interval_start TIMESTAMP,
      interval_end TIMESTAMP,
      battery_soc_start DOUBLE PRECISION,
      battery_soc_end DOUBLE PRECISION,
      solar_actual DOUBLE PRECISION,
      load_actual DOUBLE PRECISION,
      forecast_run_id VARCHAR(128),
      forecast_model_version VARCHAR(128),
      optimization_run_id VARCHAR(128),
      decision_source VARCHAR(32),
      execution_status VARCHAR(32),
      event_type VARCHAR(32),
      mode_from VARCHAR(32),
      mode_to VARCHAR(32),
      realized_revenue_uah DOUBLE PRECISION,
      realized_cost_uah DOUBLE PRECISION,
      realized_net_uah DOUBLE PRECISION,
      decision_snapshot JSONB,
      is_reconciled BOOLEAN NOT NULL DEFAULT FALSE,
      reconciled_at TIMESTAMP,
      reconciliation_note TEXT,
      created_at TIMESTAMP DEFAULT NOW(),
      updated_at TIMESTAMP DEFAULT NOW()
    )
  `)

  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS execution_key VARCHAR(64)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS command_id VARCHAR(128)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS schedule_id VARCHAR(128)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(128)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS execution_source VARCHAR(64)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ALTER COLUMN execution_source SET DEFAULT 'unknown'`)
  await optimizationPool.query(`UPDATE optimization_history SET execution_source = 'unknown' WHERE execution_source IS NULL`)
  await optimizationPool.query(`ALTER TABLE optimization_history ALTER COLUMN execution_source SET NOT NULL`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS price_uah_kwh DOUBLE PRECISION`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS duration_minutes INTEGER`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS energy_kwh DOUBLE PRECISION`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS economics_method VARCHAR(64)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS economics_version VARCHAR(64)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS fallback_reason TEXT`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS price_source VARCHAR(64)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS tariff_window VARCHAR(32)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS interval_start TIMESTAMP`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS interval_end TIMESTAMP`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS forecast_run_id VARCHAR(128)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS forecast_model_version VARCHAR(128)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS optimization_run_id VARCHAR(128)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS decision_source VARCHAR(32)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS execution_status VARCHAR(32)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS event_type VARCHAR(32)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS mode_from VARCHAR(32)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS mode_to VARCHAR(32)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS realized_revenue_uah DOUBLE PRECISION`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS realized_cost_uah DOUBLE PRECISION`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS realized_net_uah DOUBLE PRECISION`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS decision_snapshot JSONB`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS is_reconciled BOOLEAN NOT NULL DEFAULT FALSE`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS reconciled_at TIMESTAMP`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS reconciliation_note TEXT`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()`)
  await optimizationPool.query(`
    UPDATE optimization_history
    SET
      forecast_run_id = COALESCE(forecast_run_id, NULLIF(BTRIM(decision_snapshot ->> 'forecast_run_id'), '')),
      forecast_model_version = COALESCE(forecast_model_version, NULLIF(BTRIM(decision_snapshot ->> 'forecast_model_version'), '')),
      optimization_run_id = COALESCE(optimization_run_id, NULLIF(BTRIM(decision_snapshot ->> 'optimization_run_id'), ''))
    WHERE decision_snapshot IS NOT NULL
  `)
  await optimizationPool.query(`
    UPDATE optimization_history
    SET execution_key = CONCAT(
      'legacy_',
      id,
      '_',
      TO_CHAR(COALESCE(timestamp, NOW()), 'YYYYMMDDHH24MISS')
    )
    WHERE execution_key IS NULL
  `)
  await optimizationPool.query(`ALTER TABLE optimization_history ALTER COLUMN execution_key SET NOT NULL`)

  await optimizationPool.query(
    'CREATE INDEX IF NOT EXISTS idx_optimization_history_timestamp ON optimization_history(timestamp DESC)',
  )
  await optimizationPool.query(
    'CREATE UNIQUE INDEX IF NOT EXISTS uq_optimization_history_execution_key ON optimization_history(execution_key)',
  )
  await optimizationPool.query(
    'CREATE INDEX IF NOT EXISTS idx_optimization_history_command_id ON optimization_history(command_id)',
  )
  await optimizationPool.query(
    'CREATE INDEX IF NOT EXISTS idx_optimization_history_schedule_id ON optimization_history(schedule_id)',
  )
  await optimizationPool.query(
    'CREATE INDEX IF NOT EXISTS idx_optimization_history_tenant_id ON optimization_history(tenant_id)',
  )
  await optimizationPool.query(
    'CREATE INDEX IF NOT EXISTS idx_optimization_history_tenant_timestamp ON optimization_history(tenant_id, timestamp DESC)',
  )
}

async function getOptimizationPool(): Promise<any | null> {
  if (pool) {
    return pool
  }

  if (initPromise) {
    return initPromise
  }

  initPromise = (async () => {
    try {
      const config = resolveOptimizationDbConfig()

      const poolConfig = {
        host: config.host,
        port: config.port,
        user: config.user,
        password: config.password,
        database: config.database,
      }

      const createdPool = new Pool(poolConfig)
      pool = createdPool
      return createdPool
    } catch (error) {
      await markOptimizationHistoryUnavailable(getErrorMessage(error) || 'failed to initialize optimization database pool')
      return null
    } finally {
      initPromise = null
    }
  })()

  return initPromise
}

export async function initializeOptimizationHistory(): Promise<OptimizationHistoryInitializationResult> {
  if (schemaInitialized) {
    return {
      available: true,
      initialized: true,
      degraded: false,
    }
  }

  if (schemaInitializationPromise) {
    return schemaInitializationPromise
  }

  schemaInitializationPromise = (async () => {
    const optimizationPool = await getOptimizationPool()
    if (!optimizationPool) {
      return {
        available: false,
        initialized: false,
        degraded: true,
        reason: unavailableReason || 'optimization pool unavailable',
      }
    }

    try {
      await ensureSchema(optimizationPool)
      schemaInitialized = true
      unavailableReason = null
      loggedUnavailableMode = false

      return {
        available: true,
        initialized: true,
        degraded: false,
      }
    } catch (error) {
      if (isOptimizationDbUnavailable(error)) {
        const reason = getErrorMessage(error) || 'optimization history database unavailable'
        await markOptimizationHistoryUnavailable(reason)
        return {
          available: false,
          initialized: false,
          degraded: true,
          reason,
        }
      }

      throw error
    }
  })()

  try {
    return await schemaInitializationPromise
  } finally {
    schemaInitializationPromise = null
  }
}

export async function persistOptimizationHistory(
  entry: OptimizationHistoryInsert,
): Promise<PersistOptimizationHistoryResult> {
  if (!schemaInitialized) {
    return {
      ok: false,
      inserted: false,
      updated: false,
      reconciled: false,
      executionKey: entry.execution_key,
      error: unavailableReason || 'optimization history schema not initialized',
    }
  }

  const optimizationPool = await getOptimizationPool()
  if (!optimizationPool) {
    return {
      ok: false,
      inserted: false,
      updated: false,
      reconciled: false,
      executionKey: entry.execution_key,
      error: unavailableReason || 'optimization pool unavailable',
    }
  }

  try {
    const existingResult = await optimizationPool.query(
      `
      SELECT
        execution_key,
        command_id,
        schedule_id,
        tenant_id,
        execution_source,
        timestamp,
        predicted_action,
        actual_action,
        cost_baseline,
        cost_rl,
        price_uah_kwh,
        duration_minutes,
        energy_kwh,
        economics_method,
        economics_version,
        fallback_reason,
        price_source,
        tariff_window,
        interval_start,
        interval_end,
        battery_soc_start,
        battery_soc_end,
        solar_actual,
        load_actual,
        forecast_run_id,
        forecast_model_version,
        optimization_run_id,
        decision_source,
        execution_status,
        event_type,
        mode_from,
        mode_to,
        realized_revenue_uah,
        realized_cost_uah,
        realized_net_uah,
        decision_snapshot,
        is_reconciled,
        reconciled_at,
        reconciliation_note
      FROM optimization_history
      WHERE execution_key = $1
      LIMIT 1
      `,
      [entry.execution_key],
    )
    const existingEntry = existingResult.rows?.[0] as OptimizationHistoryStoredRow | undefined
    const reconciliation = reconcileOptimizationHistoryEntry(existingEntry || null, entry)
    const mergedEntry = reconciliation.entry

    const result = await optimizationPool.query(
      `
      INSERT INTO optimization_history (
        execution_key,
        command_id,
        schedule_id,
        tenant_id,
        execution_source,
        timestamp,
        predicted_action,
        actual_action,
        cost_baseline,
        cost_rl,
        price_uah_kwh,
        duration_minutes,
        energy_kwh,
        economics_method,
        economics_version,
        fallback_reason,
        price_source,
        tariff_window,
        interval_start,
        interval_end,
        battery_soc_start,
        battery_soc_end,
        solar_actual,
        load_actual,
        forecast_run_id,
        forecast_model_version,
        optimization_run_id,
        decision_source,
        execution_status,
        event_type,
        mode_from,
        mode_to,
        realized_revenue_uah,
        realized_cost_uah,
        realized_net_uah,
        decision_snapshot,
        is_reconciled,
        reconciled_at,
        reconciliation_note,
        updated_at
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39, NOW())
      ON CONFLICT (execution_key)
      DO UPDATE SET
        command_id = EXCLUDED.command_id,
        schedule_id = EXCLUDED.schedule_id,
        tenant_id = EXCLUDED.tenant_id,
        execution_source = EXCLUDED.execution_source,
        timestamp = EXCLUDED.timestamp,
        predicted_action = EXCLUDED.predicted_action,
        actual_action = EXCLUDED.actual_action,
        cost_baseline = EXCLUDED.cost_baseline,
        cost_rl = EXCLUDED.cost_rl,
        price_uah_kwh = EXCLUDED.price_uah_kwh,
        duration_minutes = EXCLUDED.duration_minutes,
        energy_kwh = EXCLUDED.energy_kwh,
        economics_method = EXCLUDED.economics_method,
        economics_version = EXCLUDED.economics_version,
        fallback_reason = EXCLUDED.fallback_reason,
        price_source = EXCLUDED.price_source,
        tariff_window = EXCLUDED.tariff_window,
        interval_start = EXCLUDED.interval_start,
        interval_end = EXCLUDED.interval_end,
        battery_soc_start = EXCLUDED.battery_soc_start,
        battery_soc_end = EXCLUDED.battery_soc_end,
        solar_actual = EXCLUDED.solar_actual,
        load_actual = EXCLUDED.load_actual,
        forecast_run_id = EXCLUDED.forecast_run_id,
        forecast_model_version = EXCLUDED.forecast_model_version,
        optimization_run_id = EXCLUDED.optimization_run_id,
        decision_source = EXCLUDED.decision_source,
        execution_status = EXCLUDED.execution_status,
        event_type = EXCLUDED.event_type,
        mode_from = EXCLUDED.mode_from,
        mode_to = EXCLUDED.mode_to,
        realized_revenue_uah = EXCLUDED.realized_revenue_uah,
        realized_cost_uah = EXCLUDED.realized_cost_uah,
        realized_net_uah = EXCLUDED.realized_net_uah,
        decision_snapshot = EXCLUDED.decision_snapshot,
        is_reconciled = EXCLUDED.is_reconciled,
        reconciled_at = EXCLUDED.reconciled_at,
        reconciliation_note = EXCLUDED.reconciliation_note,
        updated_at = NOW()
      RETURNING (xmax = 0) AS inserted
      `,
      [
        mergedEntry.execution_key,
        mergedEntry.command_id,
        mergedEntry.schedule_id,
        mergedEntry.tenant_id,
        mergedEntry.execution_source,
        mergedEntry.timestamp,
        mergedEntry.predicted_action,
        mergedEntry.actual_action,
        mergedEntry.cost_baseline,
        mergedEntry.cost_rl,
        mergedEntry.price_uah_kwh,
        mergedEntry.duration_minutes,
        mergedEntry.energy_kwh,
        mergedEntry.economics_method,
        mergedEntry.economics_version,
        mergedEntry.fallback_reason,
        mergedEntry.price_source,
        mergedEntry.tariff_window,
        mergedEntry.interval_start,
        mergedEntry.interval_end,
        mergedEntry.battery_soc_start,
        mergedEntry.battery_soc_end,
        mergedEntry.solar_actual,
        mergedEntry.load_actual,
        mergedEntry.forecast_run_id ?? null,
        mergedEntry.forecast_model_version ?? null,
        mergedEntry.optimization_run_id ?? null,
        mergedEntry.decision_source ?? null,
        mergedEntry.execution_status ?? null,
        mergedEntry.event_type ?? null,
        mergedEntry.mode_from ?? null,
        mergedEntry.mode_to ?? null,
        mergedEntry.realized_revenue_uah ?? null,
        mergedEntry.realized_cost_uah ?? null,
        mergedEntry.realized_net_uah ?? null,
        mergedEntry.decision_snapshot ?? null,
        mergedEntry.is_reconciled ?? false,
        mergedEntry.reconciled_at ?? null,
        mergedEntry.reconciliation_note ?? null,
      ],
    )
    const inserted = Boolean(result.rows?.[0]?.inserted)
    console.info('[optimization-history] persisted row', {
      execution_key: mergedEntry.execution_key,
      command_id: mergedEntry.command_id,
      schedule_id: mergedEntry.schedule_id,
      tenant_id: mergedEntry.tenant_id,
      execution_source: mergedEntry.execution_source,
      inserted,
      updated: !inserted,
      reconciled: reconciliation.reconciled,
    })

    return {
      ok: true,
      inserted,
      updated: !inserted,
      reconciled: reconciliation.reconciled,
      executionKey: mergedEntry.execution_key,
      reconciliationNote: reconciliation.reconciliationNote,
    }
  } catch (error) {
    if (isOptimizationDbUnavailable(error)) {
      await markOptimizationHistoryUnavailable(getErrorMessage(error) || 'optimization history database unavailable')
    }

    console.warn('[optimization-history] Failed to persist row:', error)
    return {
      ok: false,
      inserted: false,
      updated: false,
      reconciled: false,
      executionKey: entry.execution_key,
      error: getErrorMessage(error),
    }
  }
}

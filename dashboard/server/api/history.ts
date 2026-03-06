import { existsSync, readFileSync } from 'fs'
import { join, resolve } from 'path'
import { eventHandler } from 'h3'
import {
  buildStrictDagsterTenantPredicate,
  dagsterAssetResultsHasTenantColumn,
  dagsterAssetResultsTableExists,
  resolveDagsterAssetResultsDbConfig,
} from '../utils/dagster-asset-results'
import { resolveOptimizationDbConfig } from '../utils/optimization-history'
import { getTenantResponseMetadata, resolveTenantContext } from '../utils/tenant-context'

const round = (value: number, digits = 2) => Number(value.toFixed(digits))
const asNumber = (value: unknown, fallback = 0) => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function toDateKey(value: string | Date): string {
  const parsed = new Date(value)
  if (!Number.isFinite(parsed.getTime())) return ''
  const y = parsed.getFullYear()
  const m = String(parsed.getMonth() + 1).padStart(2, '0')
  const d = String(parsed.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function readJsonIfExists(filePath: string): any | null {
  if (!existsSync(filePath)) return null
  try {
    return JSON.parse(readFileSync(filePath, 'utf-8'))
  } catch {
    return null
  }
}

type HistoryRow = {
  date: string
  cost_baseline: number
  cost_optimized: number
  savings: number
  realized_revenue_uah?: number
  realized_cost_uah?: number
  realized_net_uah?: number
  auto_transitions?: number
  battery_actions: number
  price_min: number
  price_max: number
  tenant_id?: string | null
  reconciled_rows?: number
  heuristic_rows?: number
}

async function fetchAppDbHistory(limitDays: number, tenantId: string): Promise<Array<Partial<HistoryRow> & { date: string }> | null> {
  try {
    const { Pool } = await import('pg')
    const config = resolveOptimizationDbConfig()
    const pool = new Pool(config)

    try {
      const tableCheck = await pool.query(`SELECT to_regclass('public.optimization_history') AS table_name`)
      if (!tableCheck.rows?.[0]?.table_name) return null

      const tenantColumnCheck = await pool.query(
        `
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'optimization_history'
          AND column_name = 'tenant_id'
        LIMIT 1
        `,
      )

      if (tenantColumnCheck.rowCount === 0) {
        return null
      }

      const result = await pool.query(
        `
        SELECT
          DATE(timestamp) AS day,
          SUM(COALESCE(cost_baseline, 0)) AS baseline_cost,
          SUM(COALESCE(cost_rl, 0)) AS optimized_cost,
          SUM(COALESCE(realized_revenue_uah, 0)) AS realized_revenue_uah,
          SUM(COALESCE(realized_cost_uah, 0)) AS realized_cost_uah,
          SUM(COALESCE(realized_net_uah, 0)) AS realized_net_uah,
          SUM(CASE WHEN COALESCE(event_type, '') = 'auto_transition' THEN 1 ELSE 0 END) AS auto_transitions,
          SUM(CASE WHEN predicted_action IN (0, 1) THEN 1 ELSE 0 END) AS battery_actions,
          SUM(CASE WHEN COALESCE(is_reconciled, FALSE) THEN 1 ELSE 0 END) AS reconciled_rows,
          SUM(CASE WHEN COALESCE(economics_method, '') = 'heuristic_multiplier' THEN 1 ELSE 0 END) AS heuristic_rows
        FROM optimization_history
        WHERE timestamp >= NOW() - INTERVAL '45 days'
          AND tenant_id = $2
        GROUP BY DATE(timestamp)
        ORDER BY day DESC
        LIMIT $1
        `,
        [limitDays, tenantId],
      )

      if (!result.rows?.length) return null

      return result.rows.map((row: any) => ({
        date: toDateKey(row.day),
        cost_baseline: asNumber(row.baseline_cost, 0),
        cost_optimized: asNumber(row.optimized_cost, 0),
        savings: asNumber(row.baseline_cost, 0) - asNumber(row.optimized_cost, 0),
        realized_revenue_uah: asNumber(row.realized_revenue_uah, 0),
        realized_cost_uah: asNumber(row.realized_cost_uah, 0),
        realized_net_uah: asNumber(row.realized_net_uah, 0),
        auto_transitions: asNumber(row.auto_transitions, 0),
        battery_actions: asNumber(row.battery_actions, 0),
        reconciled_rows: asNumber(row.reconciled_rows, 0),
        heuristic_rows: asNumber(row.heuristic_rows, 0),
      }))
    } finally {
      await pool.end().catch(() => {})
    }
  } catch {
    return null
  }
}

function toCanonicalRowsFromDagsterData(data: any): Array<Partial<HistoryRow> & { date: string }> {
  const candidateArrays = [
    data?.history,
    data?.rows,
    data?.daily,
    data?.data,
    data?.metrics,
  ].filter((value) => Array.isArray(value)) as any[]

  for (const arr of candidateArrays) {
    const rows = arr
      .map((entry: any) => {
        const date = toDateKey(entry?.date || entry?.timestamp || entry?.day || '')
        const baseline = asNumber(entry?.cost_baseline ?? entry?.baseline_cost ?? entry?.baseline, NaN)
        const optimized = asNumber(entry?.cost_optimized ?? entry?.optimized_cost ?? entry?.cost_rl ?? entry?.optimized, NaN)

        if (!date || !Number.isFinite(baseline) || !Number.isFinite(optimized)) return null

        return {
          date,
          cost_baseline: baseline,
          cost_optimized: optimized,
          savings: asNumber(entry?.savings, baseline - optimized),
          battery_actions: asNumber(entry?.battery_actions, 0),
          tenant_id: typeof entry?.tenant_id === 'string'
            ? entry.tenant_id.trim().toLowerCase()
            : typeof entry?.tenantId === 'string'
              ? entry.tenantId.trim().toLowerCase()
              : null,
        }
      })
      .filter(Boolean) as Array<Partial<HistoryRow> & { date: string }>

    if (rows.length > 0) {
      return rows
    }
  }

  return []
}

async function fetchDagsterAssetHistory(
  limitDays: number,
  tenantId: string,
): Promise<Array<Partial<HistoryRow> & { date: string }> | null> {
  try {
    const { Pool } = await import('pg')
    const pool = new Pool(resolveDagsterAssetResultsDbConfig())

    try {
      if (!(await dagsterAssetResultsTableExists(pool))) return null

      const hasTenantColumn = await dagsterAssetResultsHasTenantColumn(pool)
      if (!hasTenantColumn) {
        console.warn('[history] asset_results is missing required tenant_id enforcement')
        return null
      }

      const tenantPredicate = buildStrictDagsterTenantPredicate()

      const result = await pool.query(
        `
        SELECT materialization_time, data
        FROM asset_results
        WHERE status = 'success'
          AND data IS NOT NULL
          AND ${tenantPredicate}
        ORDER BY materialization_time DESC
        LIMIT 80
        `,
        [tenantId],
      )

      if (!result.rows?.length) return null

      const merged = new Map<string, Partial<HistoryRow> & { date: string }>()
      for (const row of result.rows) {
        const parsedRows = toCanonicalRowsFromDagsterData(row.data)
        for (const parsed of parsedRows) {
          if (parsed.tenant_id && parsed.tenant_id !== tenantId) {
            continue
          }
          if (!merged.has(parsed.date)) {
            merged.set(parsed.date, parsed)
          }
        }
      }

      const output = Array.from(merged.values())
        .sort((a, b) => (a.date > b.date ? -1 : a.date < b.date ? 1 : 0))
        .slice(0, limitDays)

      return output.length > 0 ? output : null
    } finally {
      await pool.end().catch(() => {})
    }
  } catch {
    return null
  }
}

function buildRowsFromPpoValidation(
  ppo: any,
  limitDays: number,
): Array<Partial<HistoryRow> & { date: string }> | null {
  const dailyBaseline = asNumber(ppo?.daily_baseline, NaN)
  const dailyOptimized = asNumber(ppo?.daily_optimized, NaN)
  const dailySavings = asNumber(ppo?.daily_savings, dailyBaseline - dailyOptimized)
  if (!Number.isFinite(dailyBaseline) || !Number.isFinite(dailyOptimized) || dailyBaseline <= 0) {
    return null
  }

  const rows: Array<Partial<HistoryRow> & { date: string }> = []
  for (let i = 0; i < limitDays; i += 1) {
    const date = new Date()
    date.setHours(0, 0, 0, 0)
    date.setDate(date.getDate() - i)
    rows.push({
      date: toDateKey(date),
      cost_baseline: dailyBaseline,
      cost_optimized: dailyOptimized,
      savings: dailySavings,
      battery_actions: 0,
    })
  }

  return rows
}

function resolveProjectRoot(): string {
  const cwd = process.cwd()
  if (existsSync(join(cwd, 'ml_integration_api.py'))) return cwd
  return resolve(cwd, '..')
}

export default eventHandler(async (event) => {
  // GET /api/history - Legacy optimization history mapped to backend telemetry.
  try {
    const tenant = await resolveTenantContext(event)
    const limitDays = 7
    const projectRoot = resolveProjectRoot()
    const analyticsPath = join(projectRoot, 'energy_ml', 'outputs', 'analytics_cache.json')
    const latestResultsPath = join(projectRoot, 'energy_ml', 'outputs', 'latest_ml_results.json')
    const ppoValidationPath = join(projectRoot, 'data', 'results', 'ppo_validation_feb2026.json')

    const tenantRequest = {
      headers: {
        'x-tenant-id': tenant.id,
      },
      query: {
        tenantId: tenant.id,
      },
    }

    const [controlHistoryPayload, pricesPayload] = await Promise.all([
      $fetch<any>('/api/control/history', {
        ...tenantRequest,
        query: {
          ...tenantRequest.query,
          limit: 400,
        },
      }).catch(() => null),
      $fetch<any>('/api/prices/current', tenantRequest).catch(() => null),
    ])

    const analytics = readJsonIfExists(analyticsPath)
    const latestResults = readJsonIfExists(latestResultsPath)
    const ppoValidation = readJsonIfExists(ppoValidationPath)

    const todayMinPriceKwh = asNumber(pricesPayload?.prices?.today?.min, 0)
    const todayMaxPriceKwh = asNumber(pricesPayload?.prices?.today?.max, todayMinPriceKwh)

    const actionBuckets = new Map<string, number>()

    const entries = Array.isArray(controlHistoryPayload?.history)
      ? controlHistoryPayload.history
      : []

    for (const entry of entries) {
      const key = toDateKey(entry?.timestamp || entry?.executed_at || '')
      if (!key) continue
      const command = String(entry?.command || '').toLowerCase()
      const isAction = command === 'charge' || command === 'discharge'

      const currentActions = actionBuckets.get(key) || 0
      actionBuckets.set(key, currentActions + (isAction ? 1 : 0))
    }

    const appDbRows = await fetchAppDbHistory(limitDays, tenant.id)
    const dagsterRows = appDbRows ? null : await fetchDagsterAssetHistory(limitDays, tenant.id)
    const ppoRows = appDbRows || dagsterRows ? null : buildRowsFromPpoValidation(ppoValidation, limitDays)

    const fallbackDailySavings = asNumber(
      analytics?.cost_analytics?.net_savings,
      latestResults?.validation_metrics?.historical_daily_profit_uah,
    )
    const fallbackImprovementPct = asNumber(
      ppoValidation?.improvement_pct,
      asNumber(latestResults?.model_performance?.ensemble_accuracy, 0.5) * 100,
    )
    const fallbackImprovementFactor = Math.max(0.05, Math.min(0.95, fallbackImprovementPct / 100))

    const selectedRows = appDbRows || dagsterRows || ppoRows
    const economicsSource = appDbRows
      ? 'optimization_history_db'
      : dagsterRows
        ? 'dagster_asset_results'
        : ppoRows
          ? 'ppo_validation_artifact'
          : 'analytics_cache_fallback'

    const totalReconciledRows = (selectedRows || []).reduce(
      (sum, row) => sum + asNumber((row as any)?.reconciled_rows, 0),
      0,
    )
    const totalHeuristicRows = (selectedRows || []).reduce(
      (sum, row) => sum + asNumber((row as any)?.heuristic_rows, 0),
      0,
    )
    const totalRealizedRevenueUah = (selectedRows || []).reduce(
      (sum, row) => sum + asNumber((row as any)?.realized_revenue_uah, 0),
      0,
    )
    const totalRealizedCostUah = (selectedRows || []).reduce(
      (sum, row) => sum + asNumber((row as any)?.realized_cost_uah, 0),
      0,
    )
    const totalRealizedNetUah = (selectedRows || []).reduce(
      (sum, row) => sum + asNumber((row as any)?.realized_net_uah, 0),
      0,
    )
    const totalAutoTransitions = (selectedRows || []).reduce(
      (sum, row) => sum + asNumber((row as any)?.auto_transitions, 0),
      0,
    )

    const fallbackReasonCode = appDbRows
      ? 'none'
      : dagsterRows
        ? 'optimization_history_unavailable_or_empty'
        : ppoRows
          ? 'optimization_history_and_dagster_unavailable_or_empty'
          : 'all_canonical_sources_unavailable'

    const rows: HistoryRow[] = []
    for (let i = 0; i < limitDays; i += 1) {
      const date = new Date()
      date.setHours(0, 0, 0, 0)
      date.setDate(date.getDate() - i)
      const dateKey = toDateKey(date)

      const sourceRow = selectedRows?.find((row) => row.date === dateKey)
      const sourceBaseline = asNumber(sourceRow?.cost_baseline, NaN)
      const sourceOptimized = asNumber(sourceRow?.cost_optimized, NaN)
      const sourceSavings = asNumber(sourceRow?.savings, sourceBaseline - sourceOptimized)

      const hasCanonical = Number.isFinite(sourceBaseline) && Number.isFinite(sourceOptimized) && sourceBaseline > 0

      const baselineCost = hasCanonical
        ? sourceBaseline
        : fallbackDailySavings / fallbackImprovementFactor

      const optimizedCost = hasCanonical
        ? sourceOptimized
        : baselineCost - fallbackDailySavings

      const savings = hasCanonical
        ? sourceSavings
        : Math.max(0, fallbackDailySavings)

      const actionCount = asNumber(sourceRow?.battery_actions, actionBuckets.get(dateKey) || 0)
      const realizedRevenueUah = asNumber(sourceRow?.realized_revenue_uah, 0)
      const realizedCostUah = asNumber(sourceRow?.realized_cost_uah, 0)
      const realizedNetUah = asNumber(sourceRow?.realized_net_uah, realizedRevenueUah - realizedCostUah)
      const autoTransitions = asNumber(sourceRow?.auto_transitions, 0)

      rows.push({
        date: dateKey,
        cost_baseline: round(baselineCost),
        cost_optimized: round(optimizedCost),
        savings: round(savings),
        realized_revenue_uah: round(realizedRevenueUah),
        realized_cost_uah: round(realizedCostUah),
        realized_net_uah: round(realizedNetUah),
        auto_transitions: Math.round(autoTransitions),
        battery_actions: Math.round(actionCount),
        price_min: round(todayMinPriceKwh * 1000),
        price_max: round(todayMaxPriceKwh * 1000),
      })
    }

    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      timestamp: new Date().toISOString(),
      data: rows,
      source: {
        backend_priority: [
          'optimization_history_db',
          'dagster.asset_results',
          'data/results/ppo_validation_feb2026.json',
          'energy_ml/outputs/*.json',
        ],
        economics_source: economicsSource,
        fallback_reason_code: fallbackReasonCode,
        control_history_source: controlHistoryPayload?.source || 'unavailable',
        prices_source: pricesPayload?.prices?.source || 'unavailable',
        reconciliation: {
          reconciled_rows: totalReconciledRows,
          heuristic_rows_remaining: totalHeuristicRows,
          realized_revenue_uah: round(totalRealizedRevenueUah),
          realized_cost_uah: round(totalRealizedCostUah),
          realized_net_uah: round(totalRealizedNetUah),
          auto_transitions: Math.round(totalAutoTransitions),
        },
        tenant_filter_applied: true,
      },
    }
  } catch (error: any) {
    const errorData = error?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('[history] Failed to build backend-derived history:', error)
    return {
      success: false,
      timestamp: new Date().toISOString(),
      error: error?.message || 'Failed to fetch history data',
      data: [],
    }
  }
})

import { existsSync, readFileSync } from 'fs'
import { join, resolve } from 'path'

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
  battery_actions: number
  price_min: number
  price_max: number
}

type AppDbConfig = {
  host: string
  port: number
  user: string
  password: string
  database: string
}

function resolveAppDbConfig(): AppDbConfig {
  const url = process.env.DATABASE_URL
  if (url?.startsWith('postgres://') || url?.startsWith('postgresql://')) {
    try {
      const parsed = new URL(url)
      return {
        host: parsed.hostname || 'localhost',
        port: Number(parsed.port || 5432),
        user: decodeURIComponent(parsed.username || 'energy_user'),
        password: decodeURIComponent(parsed.password || 'dev_password'),
        database: parsed.pathname.replace(/^\//, '') || 'smart_energy_ai',
      }
    } catch {
      // Fall through to env defaults.
    }
  }

  return {
    host: process.env.APP_DB_HOST || 'localhost',
    port: Number(process.env.APP_DB_PORT || 5432),
    user: process.env.APP_DB_USER || 'energy_user',
    password: process.env.APP_DB_PASSWORD || 'dev_password',
    database: process.env.APP_DB_NAME || 'smart_energy_ai',
  }
}

async function fetchAppDbHistory(limitDays: number): Promise<Array<Partial<HistoryRow> & { date: string }> | null> {
  try {
    const { Pool } = await import('pg')
    const config = resolveAppDbConfig()
    const pool = new Pool(config)

    try {
      const tableCheck = await pool.query(`SELECT to_regclass('public.optimization_history') AS table_name`)
      if (!tableCheck.rows?.[0]?.table_name) return null

      const result = await pool.query(
        `
        SELECT
          DATE(timestamp) AS day,
          SUM(COALESCE(cost_baseline, 0)) AS baseline_cost,
          SUM(COALESCE(cost_rl, 0)) AS optimized_cost,
          SUM(CASE WHEN predicted_action IN (0, 1) THEN 1 ELSE 0 END) AS battery_actions
        FROM optimization_history
        WHERE timestamp >= NOW() - INTERVAL '45 days'
        GROUP BY DATE(timestamp)
        ORDER BY day DESC
        LIMIT $1
        `,
        [limitDays],
      )

      if (!result.rows?.length) return null

      return result.rows.map((row: any) => ({
        date: toDateKey(row.day),
        cost_baseline: asNumber(row.baseline_cost, 0),
        cost_optimized: asNumber(row.optimized_cost, 0),
        savings: asNumber(row.baseline_cost, 0) - asNumber(row.optimized_cost, 0),
        battery_actions: asNumber(row.battery_actions, 0),
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
        }
      })
      .filter(Boolean) as Array<Partial<HistoryRow> & { date: string }>

    if (rows.length > 0) {
      return rows
    }
  }

  return []
}

async function fetchDagsterAssetHistory(limitDays: number): Promise<Array<Partial<HistoryRow> & { date: string }> | null> {
  try {
    const { Pool } = await import('pg')
    const pool = new Pool({
      host: process.env.DB_HOST || 'localhost',
      port: Number(process.env.DB_PORT || 5432),
      user: process.env.DB_USER || 'dagster',
      password: process.env.DB_PASSWORD || 'dagster',
      database: process.env.DB_NAME || 'dagster',
    })

    try {
      const tableCheck = await pool.query(`SELECT to_regclass('public.asset_results') AS table_name`)
      if (!tableCheck.rows?.[0]?.table_name) return null

      const result = await pool.query(
        `
        SELECT materialization_time, data
        FROM asset_results
        WHERE status = 'success'
          AND data IS NOT NULL
        ORDER BY materialization_time DESC
        LIMIT 80
        `,
      )

      if (!result.rows?.length) return null

      const merged = new Map<string, Partial<HistoryRow> & { date: string }>()
      for (const row of result.rows) {
        const parsedRows = toCanonicalRowsFromDagsterData(row.data)
        for (const parsed of parsedRows) {
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

export default defineEventHandler(async () => {
  // GET /api/history - Legacy optimization history mapped to backend telemetry.
  try {
    const limitDays = 7
    const projectRoot = resolveProjectRoot()
    const analyticsPath = join(projectRoot, 'energy_ml', 'outputs', 'analytics_cache.json')
    const latestResultsPath = join(projectRoot, 'energy_ml', 'outputs', 'latest_ml_results.json')
    const ppoValidationPath = join(projectRoot, 'data', 'results', 'ppo_validation_feb2026.json')

    const [controlHistoryPayload, pricesPayload] = await Promise.all([
      $fetch<any>('/api/control/history?limit=400').catch(() => null),
      $fetch<any>('/api/prices/current').catch(() => null),
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

    const appDbRows = await fetchAppDbHistory(limitDays)
    const dagsterRows = appDbRows ? null : await fetchDagsterAssetHistory(limitDays)
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

      rows.push({
        date: dateKey,
        cost_baseline: round(baselineCost),
        cost_optimized: round(optimizedCost),
        savings: round(savings),
        battery_actions: Math.round(actionCount),
        price_min: round(todayMinPriceKwh * 1000),
        price_max: round(todayMaxPriceKwh * 1000),
      })
    }

    return {
      success: true,
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
        control_history_source: controlHistoryPayload?.source || 'unavailable',
        prices_source: pricesPayload?.prices?.source || 'unavailable',
      },
    }
  } catch (error: any) {
    console.error('[history] Failed to build backend-derived history:', error)
    return {
      success: false,
      timestamp: new Date().toISOString(),
      error: error?.message || 'Failed to fetch history data',
      data: [],
    }
  }
})

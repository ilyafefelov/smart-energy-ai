import { existsSync, readFileSync } from 'fs'
import { join, resolve } from 'path'
import { getTenantResponseMetadata, resolveTenantContext } from '../utils/tenant-context'

const round = (value: number, digits = 2) => Number(value.toFixed(digits))
const asNumber = (value: unknown, fallback = 0) => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function resolveProjectRoot(): string {
  const cwd = process.cwd()
  if (existsSync(join(cwd, 'ml_integration_api.py'))) return cwd
  return resolve(cwd, '..')
}

function readJsonIfExists(filePath: string): any | null {
  if (!existsSync(filePath)) return null
  try {
    return JSON.parse(readFileSync(filePath, 'utf-8'))
  } catch {
    return null
  }
}

export default defineEventHandler(async (event) => {
  // GET /api/metrics - Legacy metrics contract mapped to backend data sources.
  try {
    const tenant = await resolveTenantContext(event)
    const tenantRequest = {
      headers: {
        'x-tenant-id': tenant.id,
      },
      query: {
        tenantId: tenant.id,
      },
    }

    const projectRoot = resolveProjectRoot()
    const analyticsPath = join(projectRoot, 'energy_ml', 'outputs', 'analytics_cache.json')
    const ppoValidationPath = join(projectRoot, 'data', 'results', 'ppo_validation_feb2026.json')

    const [historyPayload, pricesPayload, mlRecommendation, batteryStatus] = await Promise.all([
      $fetch<any>('/api/history', tenantRequest).catch(() => null),
      $fetch<any>('/api/prices', tenantRequest).catch(() => null),
      $fetch<any>('/api/ml/recommendation', tenantRequest).catch(() => null),
      $fetch<any>('/api/battery/status', tenantRequest).catch(() => null),
    ])

    const analytics = readJsonIfExists(analyticsPath)
    const ppoValidation = readJsonIfExists(ppoValidationPath)

    const rows = Array.isArray(historyPayload?.data) ? historyPayload.data : []
    const ppoDays = Math.max(1, Math.round(asNumber(ppoValidation?.days_analyzed, 7)))
    const days = Math.max(1, rows.length || ppoDays)

    let baselineTotal = rows.reduce((sum: number, row: any) => sum + asNumber(row?.cost_baseline), 0)
    let optimizedTotal = rows.reduce((sum: number, row: any) => sum + asNumber(row?.cost_optimized), 0)
    let savingsTotal = rows.reduce((sum: number, row: any) => sum + asNumber(row?.savings), 0)

    const ppoBaselineTotal = asNumber(ppoValidation?.baseline_total, 0)
    const ppoOptimizedTotal = asNumber(ppoValidation?.optimized_total, 0)
    const ppoSavingsTotal = asNumber(
      ppoValidation?.daily_savings,
      asNumber(ppoValidation?.daily_baseline, 0) - asNumber(ppoValidation?.daily_optimized, 0),
    ) * ppoDays

    if ((baselineTotal <= 0 || optimizedTotal <= 0) && ppoBaselineTotal > 0 && ppoOptimizedTotal > 0) {
      baselineTotal = ppoBaselineTotal
      optimizedTotal = ppoOptimizedTotal
      savingsTotal = ppoSavingsTotal > 0 ? ppoSavingsTotal : ppoBaselineTotal - ppoOptimizedTotal
    }

    if (savingsTotal <= 0) {
      const fallbackDaily = asNumber(analytics?.cost_analytics?.net_savings, 0)
      savingsTotal = fallbackDaily * days
    }
    if (optimizedTotal <= 0) {
      optimizedTotal = savingsTotal * 1.35
    }
    if (baselineTotal <= 0) {
      baselineTotal = optimizedTotal + savingsTotal
    }

    const baselineDaily = baselineTotal / days
    const optimizedDaily = optimizedTotal / days
    const savingsDaily = savingsTotal / days
    const savingsPct = baselineTotal > 0 ? (savingsTotal / baselineTotal) * 100 : 0

    const monthlyFromMl = asNumber(mlRecommendation?.data?.savings_estimate?.monthly_uah, 0)
    const annualFromMl = asNumber(mlRecommendation?.data?.savings_estimate?.annual_uah, 0)

    const monthlyForecast = monthlyFromMl > 0 ? monthlyFromMl : savingsDaily * 30
    const quarterlyForecast = monthlyForecast * 3
    const annualForecast = annualFromMl > 0 ? annualFromMl : monthlyForecast * 12

    const batteryArbitrage = Math.max(0, asNumber(analytics?.cost_analytics?.daily_arbitrage_profit, 0) * days)
    const loadShifting = Math.max(0, asNumber(analytics?.cost_analytics?.peak_avoidance_savings, 0) * days)
    const demandResponse = Math.max(0, savingsTotal - batteryArbitrage - loadShifting)

    const batteryCapacity = asNumber(batteryStatus?.battery?.capacity, 150)
    const capexEstimate = batteryCapacity * 8000
    const paybackMonths = monthlyForecast > 0 ? capexEstimate / monthlyForecast : null
    const annualRoi = capexEstimate > 0 ? (annualForecast / capexEstimate) * 100 : 0
    const confidence = asNumber(mlRecommendation?.data?.confidence, 0)

    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      timestamp: new Date().toISOString(),
      period: `${days}-days`,
      baseline: {
        total: round(baselineTotal),
        daily_avg: round(baselineDaily),
        unit: 'UAH',
      },
      optimized: {
        total: round(optimizedTotal),
        daily_avg: round(optimizedDaily),
        unit: 'UAH',
      },
      savings: {
        total: round(savingsTotal),
        daily_avg: round(savingsDaily),
        percentage: round(savingsPct, 1),
        unit: 'UAH',
      },
      breakdown: {
        battery_arbitrage: round(batteryArbitrage),
        load_shifting: round(loadShifting),
        demand_response: round(demandResponse),
      },
      forecast: {
        monthly: round(monthlyForecast),
        quarterly: round(quarterlyForecast),
        annual: round(annualForecast),
        unit: 'UAH',
      },
      roi: {
        payback_months: paybackMonths == null ? null : round(paybackMonths, 1),
        annual_roi: round(annualRoi, 1),
        confidence: confidence >= 0.8 ? 'HIGH' : confidence >= 0.6 ? 'MEDIUM' : 'LOW',
      },
      source: {
        backend_priority: [
          '/api/history',
          'data/results/ppo_validation_feb2026.json',
          'energy_ml/outputs/analytics_cache.json',
          '/api/ml/recommendation',
          '/api/battery/status',
          '/api/prices',
        ],
        history_source: historyPayload?.source || 'unavailable',
        economics_source: historyPayload?.source?.economics_source || (ppoBaselineTotal > 0 ? 'ppo_validation_artifact' : 'analytics_cache_fallback'),
        fallback_reason_code: historyPayload?.source?.fallback_reason_code || 'unknown',
        reconciliation: historyPayload?.source?.reconciliation || {
          reconciled_rows: 0,
          heuristic_rows_remaining: 0,
        },
        prices_source: pricesPayload?.source || 'unavailable',
        tenant_filter_applied: true,
      },
    }
  } catch (error: any) {
    const errorData = error?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('[metrics] Failed to build backend-derived metrics:', error)
    return {
      success: false,
      timestamp: new Date().toISOString(),
      error: error?.message || 'Failed to fetch metrics data',
    }
  }
})

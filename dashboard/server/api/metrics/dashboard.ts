// server/api/metrics/dashboard.ts - Dashboard metrics with standardized response

import fs from 'fs'
import path from 'path'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

type RetrainingArtifacts = {
  trainingStatus: string
  lastTrainedAt: string | null
  latestMetrics: Record<string, unknown> | null
}

type DashboardTenantRequest = {
  headers: {
    'x-tenant-id': string
  }
  query: {
    tenantId: string
  }
}

type DashboardBaseMetricsPayload = {
  savings?: {
    daily_avg?: unknown
  } | null
  forecast?: {
    monthly?: unknown
  } | null
  breakdown?: {
    battery_arbitrage?: unknown
    load_shifting?: unknown
    demand_response?: unknown
  } | null
  realized?: {
    revenue_total?: unknown
    cost_total?: unknown
    net_total?: unknown
    net_daily_avg?: unknown
    auto_transitions?: unknown
  } | null
} | null

type DashboardPricePayload = {
  prices?: {
    today?: {
      avg?: unknown
    } | null
    forecast?: {
      peak?: unknown
      offPeak?: unknown
    } | null
  } | null
} | null

type DashboardBatteryPayload = {
  battery?: {
    health?: unknown
    availableToCharge?: unknown
  } | null
} | null

type DashboardMlPayload = {
  data?: {
    confidence?: unknown
    model_info?: {
      version?: unknown
    } | null
    savings_estimate?: {
      daily_uah?: unknown
      monthly_uah?: unknown
    } | null
  } | null
} | null

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}

function loadLatestRetrainingArtifacts(tenantId: string): RetrainingArtifacts {
  const retrainingDir = path.join(process.cwd(), 'data', 'tenants', tenantId, 'retraining')
  if (!fs.existsSync(retrainingDir)) {
    return {
      trainingStatus: 'idle',
      lastTrainedAt: null as string | null,
      latestMetrics: null,
    }
  }

  const files = fs.readdirSync(retrainingDir)
  const progressFiles = files
    .filter((file) => file.endsWith('.json') && !file.endsWith('-metrics.json'))
    .map((file) => {
      const absolutePath = path.join(retrainingDir, file)
      const stat = fs.statSync(absolutePath)
      return { file, absolutePath, mtimeMs: stat.mtimeMs }
    })
    .sort((a, b) => b.mtimeMs - a.mtimeMs)

  if (progressFiles.length === 0) {
    return {
      trainingStatus: 'idle',
      lastTrainedAt: null as string | null,
      latestMetrics: null,
    }
  }

  const latestProgressFile = progressFiles[0]
  if (!latestProgressFile) {
    return {
      trainingStatus: 'idle',
      lastTrainedAt: null,
      latestMetrics: null,
    }
  }

  const latestProgress = JSON.parse(fs.readFileSync(latestProgressFile.absolutePath, 'utf-8')) as Record<string, unknown>
  const metricsPath = path.join(retrainingDir, `${latestProgress.jobId}-metrics.json`)
  const latestMetrics = fs.existsSync(metricsPath)
    ? JSON.parse(fs.readFileSync(metricsPath, 'utf-8')) as Record<string, unknown>
    : null

  const rawLastTrained = typeof latestMetrics?.completedAt === 'string' || typeof latestMetrics?.completedAt === 'number'
    ? latestMetrics.completedAt
    : typeof latestProgress?.endTime === 'string' || typeof latestProgress?.endTime === 'number'
      ? latestProgress.endTime
      : typeof latestProgress?.timestamp === 'string' || typeof latestProgress?.timestamp === 'number'
        ? latestProgress.timestamp
        : null
  const lastTrainedAt = typeof rawLastTrained === 'number'
    ? new Date(rawLastTrained).toISOString()
    : typeof rawLastTrained === 'string'
      ? rawLastTrained
      : null

  return {
    trainingStatus: typeof latestProgress.status === 'string' ? latestProgress.status : 'idle',
    lastTrainedAt,
    latestMetrics,
  }
}

export default defineEventHandler(async (event): Promise<Record<string, unknown>> => {
  // GET /api/metrics/dashboard
  // STANDARDIZED RESPONSE: { success, metrics: { ... } }

  try {
    const tenant = await resolveTenantContext(event)
    const tenantRequest: DashboardTenantRequest = {
      headers: {
        'x-tenant-id': tenant.id,
      },
      query: {
        tenantId: tenant.id,
      },
    }

    const [baseMetrics, pricePayload, batteryPayload, mlPayload]: [
      DashboardBaseMetricsPayload,
      DashboardPricePayload,
      DashboardBatteryPayload,
      DashboardMlPayload,
    ] = await Promise.all([
      $fetch<DashboardBaseMetricsPayload>('/api/metrics', tenantRequest).catch(() => null),
      $fetch<DashboardPricePayload>('/api/prices/current', tenantRequest).catch(() => null),
      $fetch<DashboardBatteryPayload>('/api/battery/status', tenantRequest).catch(() => null),
      $fetch<DashboardMlPayload>('/api/ml/recommendation', tenantRequest).catch(() => null),
    ])

    const now = new Date()

    const dailySavingsFromML = Number(mlPayload?.data?.savings_estimate?.daily_uah || 0)
    const monthlySavingsFromML = Number(mlPayload?.data?.savings_estimate?.monthly_uah || 0)

    const dailySavingsFallback = Number(baseMetrics?.savings?.daily_avg || 0)
    const dailyRealizedNetFallback = Number(baseMetrics?.realized?.net_daily_avg || 0)
    const monthlySavingsFallback = Number(baseMetrics?.forecast?.monthly || 0)

    const savingsToday = dailySavingsFromML > 0
      ? dailySavingsFromML
      : dailySavingsFallback > 0
        ? dailySavingsFallback
        : dailyRealizedNetFallback
    const savingsMonth = monthlySavingsFromML > 0 ? monthlySavingsFromML : monthlySavingsFallback

    const confidence = Number(mlPayload?.data?.confidence || 0)
    const retrainingArtifacts = loadLatestRetrainingArtifacts(tenant.id)

    const forecastAccuracy = retrainingArtifacts.latestMetrics?.newAccuracy
      ? Number(retrainingArtifacts.latestMetrics.newAccuracy)
      : confidence > 0
        ? confidence * 100
        : 0

    const batteryHealth = Number(batteryPayload?.battery?.health || 95)

    const avgPrice = Number(pricePayload?.prices?.today?.avg || 0)
    const peakPrice = Number(pricePayload?.prices?.forecast?.peak || 0)
    const offPeakPrice = Number(pricePayload?.prices?.forecast?.offPeak || 0)

    const lastTrainedAt = retrainingArtifacts.lastTrainedAt || null

    const trendValue = dailySavingsFallback > 0
      ? ((savingsToday - dailySavingsFallback) / dailySavingsFallback) * 100
      : 0
    const savingsTrend = trendValue > 2 ? 'up' : trendValue < -2 ? 'down' : 'stable'

    const nextCycleHours = Math.max(1, Math.round(Number(batteryPayload?.battery?.availableToCharge || 20) / 10))
    const nextCycleIn = `${nextCycleHours}h 0m`

    const modelVersion = mlPayload?.data?.model_info?.version || 'Phase4F-v1.0'

    const breakdown = {
      arbitrage: Number(baseMetrics?.breakdown?.battery_arbitrage || 0),
      peak_avoidance: Number(baseMetrics?.breakdown?.load_shifting || 0),
      efficiency: Number(baseMetrics?.breakdown?.demand_response || 0),
    }

    const realized = {
      revenueTotal: Number(baseMetrics?.realized?.revenue_total || 0),
      costTotal: Number(baseMetrics?.realized?.cost_total || 0),
      netTotal: Number(baseMetrics?.realized?.net_total || 0),
      autoTransitions: Number(baseMetrics?.realized?.auto_transitions || 0),
    }

    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      metrics: {
        savingsToday: Number(savingsToday.toFixed(2)),
        savingsTrend,
        savingsTrendValue: Number(trendValue.toFixed(2)),
        savingsMonth: Number(savingsMonth.toFixed(2)),
        forecastAccuracy: Number(forecastAccuracy.toFixed(2)),
        batteryHealth: Number(batteryHealth.toFixed(1)),
        nextCycleIn,
        averagePrice: Number(avgPrice.toFixed(2)),
        peakPrice: Number(peakPrice.toFixed(2)),
        offPeakPrice: Number(offPeakPrice.toFixed(2)),
        modelVersion,
        trainingStatus: retrainingArtifacts.trainingStatus,
        lastTrainedAt,
        savingsBreakdown: breakdown,
        realized,
      },
      source: {
        tenant_filter_applied: true,
      },
    }
  } catch (error) {
    const errorData = typeof error === 'object' && error !== null && 'data' in error
      ? (error as { data?: { error?: { code?: string } } }).data
      : undefined
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('Failed to fetch metrics:', error)
    return {
      success: false,
      error: getErrorMessage(error, 'Failed to fetch metrics'),
      metrics: null,
    }
  }
})

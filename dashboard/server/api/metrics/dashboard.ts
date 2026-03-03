// server/api/metrics/dashboard.ts - Dashboard metrics with standardized response

import fs from 'fs'
import path from 'path'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

function loadLatestRetrainingArtifacts(tenantId: string) {
  const retrainingDir = path.join(process.cwd(), 'data', 'tenants', tenantId, 'retraining')
  if (!fs.existsSync(retrainingDir)) {
    return {
      trainingStatus: 'idle',
      lastTrainedAt: null as string | null,
      latestMetrics: null as any,
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
      latestMetrics: null as any,
    }
  }

  const latestProgress = JSON.parse(fs.readFileSync(progressFiles[0].absolutePath, 'utf-8'))
  const metricsPath = path.join(retrainingDir, `${latestProgress.jobId}-metrics.json`)
  const latestMetrics = fs.existsSync(metricsPath)
    ? JSON.parse(fs.readFileSync(metricsPath, 'utf-8'))
    : null

  const rawLastTrained = latestMetrics?.completedAt || latestProgress?.endTime || latestProgress?.timestamp || null
  const lastTrainedAt = typeof rawLastTrained === 'number'
    ? new Date(rawLastTrained).toISOString()
    : rawLastTrained

  return {
    trainingStatus: latestProgress.status || 'idle',
    lastTrainedAt,
    latestMetrics,
  }
}

export default defineEventHandler(async (event) => {
  // GET /api/metrics/dashboard
  // STANDARDIZED RESPONSE: { success, metrics: { ... } }

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

    const [baseMetrics, pricePayload, batteryPayload, mlPayload] = await Promise.all([
      $fetch<any>('/api/metrics', tenantRequest).catch(() => null),
      $fetch<any>('/api/prices/current', tenantRequest).catch(() => null),
      $fetch<any>('/api/battery/status', tenantRequest).catch(() => null),
      $fetch<any>('/api/ml/recommendation', tenantRequest).catch(() => null),
    ])

    const now = new Date()

    const dailySavingsFromML = Number(mlPayload?.data?.savings_estimate?.daily_uah || 0)
    const monthlySavingsFromML = Number(mlPayload?.data?.savings_estimate?.monthly_uah || 0)

    const dailySavingsFallback = Number(baseMetrics?.savings?.daily_avg || 0)
    const monthlySavingsFallback = Number(baseMetrics?.forecast?.monthly || 0)

    const savingsToday = dailySavingsFromML > 0 ? dailySavingsFromML : dailySavingsFallback
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
      },
      source: {
        tenant_filter_applied: true,
      },
    }
  } catch (error: any) {
    const errorData = error?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('Failed to fetch metrics:', error)
    return {
      success: false,
      error: error.message || 'Failed to fetch metrics',
      metrics: null,
    }
  }
})

// API endpoint for deterministic 24-hour schedule backed by live ML/price payloads.

import { eventHandler } from 'h3'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

type ScheduleRow = {
  hour?: number | null
  hour_offset?: number | null
  time?: string | null
  expected_profit_uah?: number | null
  recommended_action?: string | null
  [key: string]: unknown
}

type DagsterRecommendationPayload = {
  schedule_24h?: {
    schedule?: ScheduleRow[] | null
  } | null
  source_metadata?: Record<string, unknown> | null
}

type MlflowStatusPayload = {
  mlflow_connected?: boolean | null
  service_role?: string | null
  registry_summary?: {
    latest_run_name?: string | null
    recent_runs_count?: number | null
  } | null
}

type Schedule24hResponse = {
  status: 'success' | 'error'
  timestamp?: string
  tenant?: ReturnType<typeof getTenantResponseMetadata>
  registry_diagnostics?: {
    available: boolean
    service_role: string
    latest_run_name: string | null
    recent_runs_count: number
    authoritative_for_runtime_serving: boolean
  }
  schedule?: ScheduleRow[]
  summary?: {
    total_expected_profit: number
    average_hourly_profit: number
    buy_hours: number
    sell_hours: number
    discharge_hours: number
    hold_hours: number
  }
  source_metadata?: Record<string, unknown>
  error?: string
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  if (typeof error === 'string' && error.trim()) {
    return error
  }
  return 'Failed to load 24-hour schedule'
}

export default eventHandler(async (event): Promise<Schedule24hResponse> => {
  try {
    const tenant = await resolveTenantContext(event)
    const tenantRequest = {
      query: {
        tenantId: tenant.id,
      },
      headers: {
        'x-tenant-id': tenant.id,
      },
    }

    const [recommendationPayload, mlflowStatus]: [DagsterRecommendationPayload | null, MlflowStatusPayload | null] = await Promise.all([
      $fetch<DagsterRecommendationPayload>('/api/dagster/recommendation', tenantRequest).catch(() => null),
      $fetch<MlflowStatusPayload>('/api/mlflow/status', tenantRequest).catch(() => null),
    ])

    const schedule = recommendationPayload?.schedule_24h?.schedule || []
    const recommendationSourceMetadata = recommendationPayload?.source_metadata
      && typeof recommendationPayload.source_metadata === 'object'
      ? recommendationPayload.source_metadata
      : {}
    const totalProfit = schedule.reduce((sum: number, row) => sum + Number(row?.expected_profit_uah || 0), 0)

    return {
      status: 'success',
      timestamp: new Date().toISOString(),
      tenant: getTenantResponseMetadata(tenant),
      registry_diagnostics: {
        available: mlflowStatus?.mlflow_connected === true,
        service_role: mlflowStatus?.service_role || 'registry_and_experiment_diagnostics',
        latest_run_name: mlflowStatus?.registry_summary?.latest_run_name || null,
        recent_runs_count: mlflowStatus?.registry_summary?.recent_runs_count || 0,
        authoritative_for_runtime_serving: false,
      },
      schedule,
      summary: {
        total_expected_profit: Number(totalProfit.toFixed(2)),
        average_hourly_profit: schedule.length > 0 ? Number((totalProfit / schedule.length).toFixed(2)) : 0,
        buy_hours: schedule.filter(s => s.recommended_action === 'BUY').length,
        sell_hours: schedule.filter(s => s.recommended_action === 'SELL').length,
        discharge_hours: schedule.filter(s => s.recommended_action === 'DISCHARGE').length,
        hold_hours: schedule.filter(s => s.recommended_action === 'HOLD').length,
      },
      source_metadata: {
        ...recommendationSourceMetadata,
        tenant_filter_applied: true,
        mlflow_registry_diagnostics_available: mlflowStatus?.mlflow_connected === true,
      },
    }
  } catch (error) {
    const errorData = (error as any)?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('[schedule-24h] Error:', error)
    return {
      status: 'error',
      error: getErrorMessage(error),
    }
  }
})

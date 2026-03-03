// API endpoint for deterministic 24-hour schedule backed by live ML/price payloads.

import { eventHandler } from 'h3'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

export default eventHandler(async (event) => {
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

    const [recommendationPayload, mlflowStatus] = await Promise.all([
      $fetch<any>('/api/dagster/recommendation', tenantRequest).catch(() => null),
      $fetch<any>('/api/mlflow/status', tenantRequest).catch(() => null),
    ])

    const schedule = recommendationPayload?.schedule_24h?.schedule || []
    const totalProfit = schedule.reduce((sum: number, row: any) => sum + Number(row?.expected_profit_uah || 0), 0)

    return {
      status: 'success',
      timestamp: new Date().toISOString(),
      tenant: getTenantResponseMetadata(tenant),
      mlflow_connected: mlflowStatus?.mlflow_connected === true,
      experiments: (mlflowStatus?.experiments || []).map((exp: any) => ({
        id: exp.id,
        name: exp.name,
        last_update: exp.last_update_time || new Date().toISOString(),
      })),
      schedule,
      summary: {
        total_expected_profit: Number(totalProfit.toFixed(2)),
        average_hourly_profit: schedule.length > 0 ? Number((totalProfit / schedule.length).toFixed(2)) : 0,
        buy_hours: schedule.filter((s: any) => s.recommended_action === 'BUY').length,
        sell_hours: schedule.filter((s: any) => s.recommended_action === 'SELL').length,
        discharge_hours: schedule.filter((s: any) => s.recommended_action === 'DISCHARGE').length,
        hold_hours: schedule.filter((s: any) => s.recommended_action === 'HOLD').length,
      },
      source_metadata: {
        tenant_filter_applied: true,
      },
    }
  } catch (error: any) {
    const errorData = error?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('[schedule-24h] Error:', error)
    return {
      status: 'error',
      error: error.message,
    }
  }
})

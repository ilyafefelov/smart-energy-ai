/**
 * Server API endpoint for ML model predictions and optimization
 * Delegates to the canonical Python bridge contract so serving/fallback
 * semantics stay aligned with the shared PredictionService adapter.
 */

import { exec } from 'child_process'
import { resolve } from 'path'
import { promisify } from 'util'
import { eventHandler, getMethod, readBody } from 'h3'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

const execAsync = promisify(exec)

const ALLOWED_STRATEGIES = new Set(['balanced', 'max_earn', 'max_battery_health', 'max_charge'])

function sanitizeStrategy(value: unknown): string {
  const normalized = typeof value === 'string' ? value.trim() : ''
  return ALLOWED_STRATEGIES.has(normalized) ? normalized : 'balanced'
}

function sanitizeNumber(value: unknown, defaultValue: number): number {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : defaultValue
}

async function syncOptimizationStrategy(projectRoot: string, tenantId: string, strategy: string) {
  const pythonScript = resolve(projectRoot, 'scripts', 'ml_integration_api.py')
  const tenantConfigDir = resolve(projectRoot, 'energy_ml', 'configs', 'tenants', tenantId)
  const setStrategyCmd = `python "${pythonScript}" --action=set_optimization_strategy --strategy=${strategy} --format=json`

  await execAsync(setStrategyCmd, {
    timeout: 30000,
    maxBuffer: 10 * 1024 * 1024,
    cwd: projectRoot,
    env: {
      ...process.env,
      ENERGY_ML_CONFIG_DIR: tenantConfigDir,
      ENERGY_ML_TENANT_ID: tenantId,
    },
  })
}

function buildLiveContext(tenantId: string, strategy: string, batterySoc: number, price: number) {
  return {
    tenant_id: tenantId,
    captured_at: new Date().toISOString(),
    config: {
      optimization_strategy: strategy,
    },
    price_signal: {
      source: 'api/ml/predict',
      current_uah_kwh: price,
      forecast_next24h: [
        {
          hour: new Date().getHours(),
          price,
        },
      ],
    },
    battery_signal: {
      source: 'simulator_backed_telemetry',
      source_detail: 'api/ml/predict',
      soc_percent: batterySoc,
    },
  }
}

export default eventHandler(async (event) => {
  const method = getMethod(event)

  if (method === 'POST') {
    const tenant = await resolveTenantContext(event)
    const body = await readBody(event)
    const strategy = sanitizeStrategy(body?.strategy)
    const batterySoc = sanitizeNumber(body?.battery_soc, 50)
    const price = sanitizeNumber(body?.price, 14.26)
    const projectRoot = resolve(process.cwd(), '..')
    const pythonScript = resolve(projectRoot, 'scripts', 'ml_integration_api.py')
    const tenantConfigDir = resolve(projectRoot, 'energy_ml', 'configs', 'tenants', tenant.id)
    const liveContext = buildLiveContext(tenant.id, strategy, batterySoc, price)

    let strategySyncError: string | null = null
    let pythonStderr: string | null = null

    try {
      try {
        await syncOptimizationStrategy(projectRoot, tenant.id, strategy)
      } catch (error: any) {
        strategySyncError = error?.message || 'Failed to set optimization strategy'
      }

      const pythonCmd = `python "${pythonScript}" --action=get_recommendation --format=json --enhanced=true`
      const { stdout, stderr } = await execAsync(pythonCmd, {
        timeout: 30000,
        maxBuffer: 10 * 1024 * 1024,
        cwd: projectRoot,
        env: {
          ...process.env,
          ENERGY_ML_CONFIG_DIR: tenantConfigDir,
          ENERGY_ML_TENANT_ID: tenant.id,
          ENERGY_ML_LIVE_CONTEXT_JSON: JSON.stringify(liveContext),
        },
      })

      pythonStderr = stderr ? String(stderr).trim() : null
      const recommendationPayload = JSON.parse((stdout || '').trim())

      if (!recommendationPayload?.success || !recommendationPayload?.data?.action) {
        throw new Error(recommendationPayload?.error || 'Shared ML recommendation bridge failed')
      }

      const serving = recommendationPayload?.serving || {
        requested_mode: 'incumbent',
        active_mode: 'incumbent',
        adapter: 'PredictionService',
        fallback_used: false,
        fallback_reason_code: 'none',
        model_info: null,
      }

      return {
        status: 'success',
        timestamp: new Date().toISOString(),
        tenant: getTenantResponseMetadata(tenant),
        recommendation: {
          action: recommendationPayload.data.action,
          confidence: recommendationPayload.data.confidence || 0.75,
          rationale: recommendationPayload.data.reasoning || 'Recommendation unavailable',
          normalized_action: recommendationPayload.data.normalized_action || recommendationPayload.contract?.normalized_action || null,
          provenance: recommendationPayload.data.provenance || recommendationPayload.contract?.provenance || null,
        },
        contract: recommendationPayload.contract || null,
        serving,
        model_info: {
          strategy,
          version: recommendationPayload.data.model_info?.version || null,
          source: 'ml_integration_api.py',
          fallback_used: Boolean(serving.fallback_used),
          fallback_reason: serving.fallback_reason_code || recommendationPayload.contract?.provenance?.fallback_reason_code || 'none',
          requested_mode: serving.requested_mode,
          active_mode: serving.active_mode,
          serving_adapter: serving.adapter,
          resolved_model_uri: serving.model_info?.resolved_model_uri || null,
          strategy_sync_error: strategySyncError,
          python_stderr: pythonStderr,
          input_context: {
            battery_soc: batterySoc,
            price,
          },
        },
        raw_output: recommendationPayload,
      }
    } catch (error: any) {
      return {
        status: 'error',
        timestamp: new Date().toISOString(),
        error: error?.message || 'Prediction request failed',
      }
    }
  }

  // GET request - return API info
  return {
    status: 'ok',
    message: 'ML Prediction API (delegates to the shared Python serving contract)',
    usage: 'POST with { strategy, battery_soc, price }',
    available_strategies: ['max_earn', 'max_battery_health', 'max_charge', 'balanced'],
    example: {
      strategy: 'balanced',
      battery_soc: 50,
      price: 14.26,
    },
    contract_version: 'learned_policy_migration_v1',
  }
})

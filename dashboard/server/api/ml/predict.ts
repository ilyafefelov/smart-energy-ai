/**
 * Server API endpoint for ML model predictions and optimization
 * Integrates with energy_ml ML pipeline via Python subprocess
 */

import { exec } from 'child_process'
import { existsSync } from 'fs'
import { resolve } from 'path'
import { promisify } from 'util'
import { eventHandler, getMethod, readBody } from 'h3'

const execAsync = promisify(exec)

const ALLOWED_STRATEGIES = new Set(['balanced', 'max_earn', 'max_battery_health', 'max_charge'])

type FallbackReason =
  | 'script_missing'
  | 'strategy_sync_failed'
  | 'python_execution_failed'
  | 'invalid_python_payload'
  | 'unexpected_error'

function sanitizeStrategy(value: unknown): string {
  const normalized = typeof value === 'string' ? value.trim() : ''
  return ALLOWED_STRATEGIES.has(normalized) ? normalized : 'balanced'
}

function sanitizeNumber(value: unknown, defaultValue: number): number {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : defaultValue
}

function buildFallbackRecommendation(batterySoc: number, price: number) {
  let action = 'HOLD'
  let confidence = 0.75
  let rationale = 'Moderate price, no action needed'

  if (price < 12 && batterySoc < 90) {
    action = 'BUY'
    confidence = 0.85
    rationale = 'Low price, battery has capacity'
  } else if (price > 18 && batterySoc > 50) {
    action = 'DISCHARGE'
    confidence = 0.82
    rationale = 'Peak price, discharging battery'
  } else if (price > 16 && batterySoc > 30) {
    action = 'SELL'
    confidence = 0.88
    rationale = 'High price, selling from battery'
  }

  return {
    action,
    confidence,
    rationale,
  }
}

export default eventHandler(async (event) => {
  const method = getMethod(event)

  if (method === 'POST') {
    const body = await readBody(event)
    const strategy = sanitizeStrategy(body?.strategy)
    const batterySoc = sanitizeNumber(body?.battery_soc, 50)
    const price = sanitizeNumber(body?.price, 14.26)

    const projectRoot = resolve(process.cwd(), '..')
    const pythonScript = resolve(projectRoot, 'ml_integration_api.py')

    let strategySyncError: string | null = null
    let pythonError: string | null = null
    let fallbackReason: FallbackReason | null = null

    try {
      if (!existsSync(pythonScript)) {
        fallbackReason = 'script_missing'
      } else {
        const setStrategyCmd = `python "${pythonScript}" --action=set_optimization_strategy --strategy=${strategy} --format=json`
        try {
          await execAsync(setStrategyCmd, {
            timeout: 30000,
            maxBuffer: 10 * 1024 * 1024,
            cwd: projectRoot,
          })
        } catch (error: any) {
          strategySyncError = error?.message || 'Failed to set optimization strategy'
          fallbackReason = 'strategy_sync_failed'
        }

        const pythonCmd = `python "${pythonScript}" --action=get_recommendation --format=json --enhanced=true`
        try {
          const { stdout, stderr } = await execAsync(pythonCmd, {
            timeout: 30000,
            maxBuffer: 10 * 1024 * 1024,
            cwd: projectRoot,
          })

          pythonError = stderr || null

          let recommendation: any = null
          try {
            recommendation = JSON.parse((stdout || '').trim())
          } catch {
            fallbackReason = 'invalid_python_payload'
          }

          if (recommendation?.success && recommendation?.action) {
            return {
              status: 'success',
              timestamp: new Date().toISOString(),
              recommendation: {
                action: recommendation.action,
                confidence: recommendation.confidence || 0.75,
                rationale: recommendation.reasoning || 'From ML model',
              },
              model_info: {
                strategy,
                version: 'Phase4F-v1.0',
                source: 'ml_integration_api.py',
                fallback_used: false,
                fallback_reason: null,
                strategy_sync_error: strategySyncError,
                python_error: pythonError,
                input_context: {
                  battery_soc: batterySoc,
                  price,
                },
              },
              raw_output: recommendation,
            }
          }

          if (!fallbackReason) {
            fallbackReason = 'python_execution_failed'
            pythonError = pythonError || 'Python recommendation response was not valid for API contract'
          }
        } catch (error: any) {
          pythonError = error?.message || 'Python subprocess failed'
          if (!fallbackReason) {
            fallbackReason = 'python_execution_failed'
          }
        }
      }

      const fallbackRecommendation = buildFallbackRecommendation(batterySoc, price)

      return {
        status: 'success',
        timestamp: new Date().toISOString(),
        recommendation: fallbackRecommendation,
        model_info: {
          strategy,
          version: 'fallback-v1.0',
          source: 'fallback_heuristic',
          fallback_used: true,
          fallback_reason: fallbackReason || 'unexpected_error',
          strategy_sync_error: strategySyncError,
          python_error: pythonError,
          input_context: {
            battery_soc: batterySoc,
            price,
          },
        },
        fallback: {
          used: true,
          reason: fallbackReason || 'unexpected_error',
          details: {
            strategy_sync_error: strategySyncError,
            python_error: pythonError,
          },
        },
      }
    } catch (error: any) {
      const fallbackRecommendation = buildFallbackRecommendation(batterySoc, price)
      return {
        status: 'success',
        timestamp: new Date().toISOString(),
        recommendation: fallbackRecommendation,
        model_info: {
          strategy,
          version: 'fallback-v1.0',
          source: 'fallback_heuristic',
          fallback_used: true,
          fallback_reason: 'unexpected_error',
          python_error: error?.message || 'Unexpected prediction error',
          input_context: {
            battery_soc: batterySoc,
            price,
          },
        },
        fallback: {
          used: true,
          reason: 'unexpected_error',
        },
      }
    }
  }

  // GET request - return API info
  return {
    status: 'ok',
    message: 'ML Prediction API',
    usage: 'POST with { strategy, battery_soc, price }',
    available_strategies: ['max_earn', 'max_battery_health', 'max_charge', 'balanced'],
    example: {
      strategy: 'balanced',
      battery_soc: 50,
      price: 14.26,
    },
  }
})

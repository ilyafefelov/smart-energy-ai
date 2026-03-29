// Runtime diagnostics capture for MLflow-adjacent metrics.

import { resolve } from 'path'
import { appendMlflowDiagnosticEvent } from '../../utils/mlflow-diagnostics'

export default defineEventHandler(async (event) => {
  const method = getMethod(event)
  
  if (method !== 'POST') {
    return {
      status: 'error',
      error: 'POST required',
      service_role: 'runtime_diagnostic_capture',
      tracking_mode: 'diagnostic_only',
      example: {
        action: 'BUY',
        confidence: 0.85,
        actual_price: 12.5,
        metrics: { profit: 10.5 },
        model_version: '1.0.0'
      }
    }
  }
  
  try {
    const body = await readBody(event)
    const timestamp = new Date().toISOString()
    const projectRoot = resolve(process.cwd(), '..')
    
    const logEntry = {
      timestamp,
      service_role: 'runtime_diagnostic_capture' as const,
      tracking_mode: 'diagnostic_only' as const,
      event_kind: 'runtime_metric_capture' as const,
      run_id: body.run_id || `session-${Date.now()}`,
      action: typeof body.action === 'string' ? body.action : null,
      confidence: Number.isFinite(Number(body.confidence)) ? Number(body.confidence) : null,
      actual_price: Number.isFinite(Number(body.actual_price)) ? Number(body.actual_price) : null,
      predicted_profit: Number.isFinite(Number(body.predicted_profit)) ? Number(body.predicted_profit) : null,
      actual_profit: Number.isFinite(Number(body.actual_profit)) ? Number(body.actual_profit) : null,
      metrics: body.metrics || {},
      params: body.params || {},
      model_version: typeof body.model_version === 'string' ? body.model_version : null,
      environment: process.env.NODE_ENV || 'development',
    }

    const storage = await appendMlflowDiagnosticEvent(projectRoot, logEntry)
    console.info('[mlflow-log-metrics] recorded local runtime diagnostics', {
      path: storage.relativePath,
      run_id: logEntry.run_id,
      action: logEntry.action,
    })
    
    return {
      status: 'success',
      timestamp,
      service_role: logEntry.service_role,
      tracking_mode: logEntry.tracking_mode,
      mlflow_tracking_enabled: false,
      logged: true,
      storage: {
        path: storage.relativePath,
        format: 'jsonl',
      },
      event: logEntry,
    }
  } catch (error: any) {
    console.error('[mlflow-log-metrics] Error:', error.message)
    return {
      status: 'error',
      service_role: 'runtime_diagnostic_capture',
      tracking_mode: 'diagnostic_only',
      error: error.message
    }
  }
})

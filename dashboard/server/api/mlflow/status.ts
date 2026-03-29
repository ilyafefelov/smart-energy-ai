// MLflow API integration via REST API
// MLflow provides HTTP REST endpoints at /api/2.0/mlflow/*

const MLFLOW_URI = process.env.MLFLOW_API_URL || 'http://localhost:5000'
const MLFLOW_STATUS_TIMEOUT_MS = Number(process.env.MLFLOW_STATUS_TIMEOUT_MS || 3000)
let loggedMlflowUnavailable = false

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message
  }

  return String(error || '')
}

function isMlflowUnavailable(error: unknown): boolean {
  const message = getErrorMessage(error).toLowerCase()
  return message.includes('fetch failed') || message.includes('econnrefused') || message.includes('enotfound') || message.includes('timed out')
}

async function fetchMlflow(path: string, body: Record<string, unknown>) {
  return await $fetch(`${MLFLOW_URI}${path}`, {
    method: 'POST',
    body,
    timeout: MLFLOW_STATUS_TIMEOUT_MS,
  })
}

export default defineEventHandler(async (event) => {
  try {
    // Fetch experiments via MLflow REST API
    const expResponse = await fetchMlflow('/ajax-api/2.0/mlflow/experiments/search', { max_results: 10 })
    
    const experiments = (expResponse as any).experiments || []
    
    // Get runs from first experiment
    let runs = []
    if (experiments.length > 0) {
      const runsResponse = await fetchMlflow('/ajax-api/2.0/mlflow/runs/search', {
        experiment_ids: [experiments[0].experiment_id],
        max_results: 5,
      })
      runs = (runsResponse as any).runs || []
    }
    
    const activeRun = runs.length > 0 ? runs[0] : null
    const activeModel = activeRun ? {
      name: activeRun.info.run_name || null,
      version: null,
      stage: null,
      metrics: activeRun.data?.metrics || {},
      params: activeRun.data?.params || {},
      feature_importance: [],
      last_updated: activeRun.info.start_time ? new Date(activeRun.info.start_time).toISOString() : null,
      source: 'latest_run_metadata',
      authoritative_for_runtime_serving: false,
    } : {
      name: null,
      version: null,
      stage: null,
      metrics: {},
      params: {},
      feature_importance: [],
      last_updated: null,
      source: 'no_runs_available',
      authoritative_for_runtime_serving: false,
    }
    
    return {
      status: 'success',
      timestamp: new Date().toISOString(),
      service_role: 'registry_and_experiment_diagnostics',
      mlflow_connected: true,
      runtime_serving_authoritative: false,
      runtime_serving_source: 'python_serving_contract',
      tracking_uri: MLFLOW_URI,
      active_model: activeModel,
      registry_summary: {
        experiments_count: experiments.length,
        recent_runs_count: runs.length,
        latest_run_id: activeRun?.info?.run_id || null,
        latest_run_name: activeRun?.info?.run_name || null,
      },
      
      experiments: experiments.map((e: any) => ({
        id: e.experiment_id,
        name: e.name,
        lifecycle_stage: e.lifecycle_stage,
        last_update_time: new Date(e.last_update_time).toISOString()
      })),
      
      runs: runs.map((r: any) => ({
        id: r.info.run_id,
        name: r.info.run_name,
        status: r.info.status,
        start_time: new Date(r.info.start_time).toISOString(),
        metrics: r.data?.metrics || {},
        params: r.data?.params || {}
      })),
      
      monitoring: {
        last_evaluation: new Date().toISOString(),
        drift_detected: false,
        recommendations: experiments.length > 0 
          ? [
              'MLflow diagnostics are available for experiments and recent runs.',
              `${experiments.length} experiments discovered at ${MLFLOW_URI}.`,
              `${runs.length} recent runs available for benchmark or registry inspection.`,
              'Live learned-policy serving remains authoritative only through the Python serving contract.',
            ]
          : [
              'Connected to MLflow, but no experiments or runs were found.',
              'This endpoint does not prove live learned-policy serving is active.',
            ]
      }
    }
  } catch (error: any) {
    const message = getErrorMessage(error) || 'MLflow unavailable'
    if (isMlflowUnavailable(error)) {
      if (!loggedMlflowUnavailable) {
        console.warn('[mlflow-status] Degraded mode enabled:', message)
        loggedMlflowUnavailable = true
      }
    } else {
      console.error('[mlflow-status] Error:', message)
    }

    return {
      success: true,
      status: 'degraded',
      timestamp: new Date().toISOString(),
      service_role: 'registry_and_experiment_diagnostics',
      error: message,
      mlflow_connected: false,
      mlflow_available: false,
      runtime_serving_authoritative: false,
      runtime_serving_source: 'python_serving_contract',
      tracking_uri: MLFLOW_URI,
      active_model: {
        name: null,
        version: null,
        stage: null,
        metrics: {},
        params: {},
        feature_importance: [],
        last_updated: null,
        source: 'mlflow_unavailable',
        authoritative_for_runtime_serving: false,
      },
      registry_summary: {
        experiments_count: 0,
        recent_runs_count: 0,
        latest_run_id: null,
        latest_run_name: null,
      },
      experiments: [],
      runs: [],
      monitoring: {
        last_evaluation: new Date().toISOString(),
        drift_detected: false,
        recommendations: [
          'MLflow server is currently unavailable',
          'Local runtime continues, but MLflow experiment and registry diagnostics are unavailable',
          'This endpoint is not authoritative for live learned-policy serving',
          `Set MLFLOW_API_URL to a reachable server (current: ${MLFLOW_URI})`,
        ],
      },
    }
  }
})

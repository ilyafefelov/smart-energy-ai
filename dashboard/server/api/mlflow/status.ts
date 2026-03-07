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
    
    // Format response
    const activeRun = runs.length > 0 ? runs[0] : null
    
    return {
      status: 'success',
      timestamp: new Date().toISOString(),
      mlflow_connected: true,
      mlflow_version: '3.x',
      
      active_model: activeRun ? {
        name: activeRun.info.run_name || activeRun.info.run_uuid,
        version: '1.0.0',
        stage: 'Production',
        metrics: activeRun.data?.metrics || {},
        params: activeRun.data?.params || {},
        last_updated: new Date(activeRun.info.start_time).toISOString(),
      } : {
        name: 'No runs yet',
        version: '1.0.0',
        stage: 'Development',
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
          ? [`Connected to MLflow`, `${experiments.length} experiments`, `${runs.length} recent runs`]
          : ['No experiments found']
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
      error: message,
      mlflow_connected: false,
      mlflow_available: false,
      active_model: {
        name: 'MLflow offline (local fallback mode)',
        version: 'n/a',
        stage: 'Unavailable',
      },
      experiments: [],
      runs: [],
      monitoring: {
        last_evaluation: new Date().toISOString(),
        drift_detected: false,
        recommendations: [
          'MLflow server is currently unavailable',
          'Local runtime continues without experiment tracking',
          `Set MLFLOW_API_URL to a reachable server (current: ${MLFLOW_URI})`,
        ],
      },
    }
  }
})

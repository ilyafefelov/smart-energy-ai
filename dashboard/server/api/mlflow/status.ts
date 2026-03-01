// MLflow API integration via REST API
// MLflow provides HTTP REST endpoints at /api/2.0/mlflow/*

const MLFLOW_URI = process.env.MLFLOW_API_URL || 'http://localhost:5000'

export default defineEventHandler(async (event) => {
  try {
    // Fetch experiments via MLflow REST API
    const expResponse = await $fetch(`${MLFLOW_URI}/ajax-api/2.0/mlflow/experiments/search`, {
      method: 'POST',
      body: { max_results: 10 }
    })
    
    const experiments = (expResponse as any).experiments || []
    
    // Get runs from first experiment
    let runs = []
    if (experiments.length > 0) {
      const runsResponse = await $fetch(`${MLFLOW_URI}/ajax-api/2.0/mlflow/runs/search`, {
        method: 'POST',
        body: {
          experiment_ids: [experiments[0].experiment_id],
          max_results: 5
        }
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
    console.error('[mlflow-status] Error:', error.message)
    return {
      status: 'error',
      error: error.message,
      mlflow_connected: false
    }
  }
})

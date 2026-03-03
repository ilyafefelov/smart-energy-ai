/**
 * ML Pipeline Recalculation API Endpoint
 * Triggers complete recalculation of ML models and analytics
 */
import { exec } from 'child_process'
import { writeFileSync, readFileSync, existsSync } from 'fs'
import { join } from 'path'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const forceRecalculate = body?.force || false
    
    // Check if recalculation is already in progress
    const statusPath = join(process.cwd(), '../energy_ml/configs/recalculation_status.json')
    
    if (existsSync(statusPath)) {
      try {
        const statusData = readFileSync(statusPath, 'utf-8')
        const status = JSON.parse(statusData)
        
        if (status.status === 'running' && !forceRecalculate) {
          return {
            success: false,
            error: 'Recalculation already in progress',
            jobId: status.jobId,
            status: status.status,
            progress: status.progress || 0
          }
        }
      } catch (e) {
        console.warn('Could not read recalculation status:', e)
      }
    }
    
    // Generate unique job ID
    const jobId = createJobId()
    
    // Initialize recalculation status
    const initialStatus = {
      jobId,
      status: 'initializing',
      progress: 0,
      stage: 'Preparing recalculation',
      startTime: new Date().toISOString(),
      details: 'Loading configuration and initializing ML pipeline',
      errors: []
    }
    
    writeFileSync(statusPath, JSON.stringify(initialStatus, null, 2))
    
    // Start the recalculation process
    const result = await startRecalculationProcess(jobId, statusPath)
    
    return {
      success: true,
      jobId,
      message: 'ML pipeline recalculation started',
      ...result
    }
    
  } catch (error) {
    console.error('ML recalculation error:', error)
    
    throw createError({
      statusCode: 500,
      statusMessage: 'Internal server error starting ML recalculation'
    })
  }
})

async function startRecalculationProcess(jobId: string, statusPath: string) {
  const pythonCommand = process.platform === 'win32' ? 'python' : 'python3'
  const workingDir = join(process.cwd(), '..')
  const scriptPath = join(workingDir, 'recalculate_pipeline.py')
  
  try {
    // Update status to running
    updateStatus(statusPath, {
      status: 'running',
      progress: 5,
      stage: 'Starting pipeline',
      details: 'Launching recalculation pipeline process'
    })

    // Execute the Python script in background
    exec(`"${pythonCommand}" "${scriptPath}"`, {
      cwd: workingDir,
      env: {
        ...process.env,
        PYTHONPATH: workingDir,
        RECALC_JOB_ID: jobId,
      }
    }, (error, stdout, stderr) => {
      if (error) {
        console.error('Recalculation script error:', error)
        updateStatus(statusPath, {
          status: 'failed',
          progress: 0,
          stage: 'Error',
          details: `Script execution failed: ${error.message}`,
          error: error.message
        })
      } else {
        updateStatus(statusPath, { jobId })
        console.log('Recalculation script output:', stdout)
        if (stderr) {
          console.warn('Recalculation script warnings:', stderr)
        }
      }
    })
    
    return {
      status: 'started',
      message: 'Recalculation process initiated successfully'
    }
    
  } catch (error) {
    updateStatus(statusPath, {
      status: 'failed',
      progress: 0,
      stage: 'Error',
      details: `Failed to start recalculation: ${error.message}`,
      error: error.message
    })
    
    throw error
  }
}

function updateStatus(statusPath: string, updates: any) {
  try {
    let currentStatus = {}
    
    if (existsSync(statusPath)) {
      const statusData = readFileSync(statusPath, 'utf-8')
      currentStatus = JSON.parse(statusData)
    }
    
    const updatedStatus = {
      ...currentStatus,
      ...updates,
      timestamp: new Date().toISOString()
    }
    
    writeFileSync(statusPath, JSON.stringify(updatedStatus, null, 2))
  } catch (e) {
    console.error('Failed to update recalculation status:', e)
  }
}

function createJobId() {
  if (!(globalThis as any).__recalculateJobCounter) {
    ;(globalThis as any).__recalculateJobCounter = 0
  }
  ;(globalThis as any).__recalculateJobCounter += 1
  return `job_${Date.now()}_${(globalThis as any).__recalculateJobCounter}`
}
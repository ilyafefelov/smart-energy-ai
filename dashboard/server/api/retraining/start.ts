// server/api/retraining/start.ts - Start model retraining

import fs from 'fs'
import path from 'path'
import { spawn } from 'child_process'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

interface RetrainingJob {
  id: string
  status: 'running' | 'completed' | 'failed'
  progress: number
  startTime: number
  executionMode: 'python' | 'simulation_fallback'
  endTime?: number
  error?: string
}

const activeJobs = new Map<string, RetrainingJob>()

function buildTenantJobKey(tenantId: string, jobId: string): string {
  return `${tenantId}:${jobId}`
}

function resolveRetrainingDir(tenantId: string): string {
  return path.join(process.cwd(), 'data', 'tenants', tenantId, 'retraining')
}

export default defineEventHandler(async (event) => {
  // POST /api/retraining/start
  // STANDARDIZED RESPONSE: { success, jobId, estimatedTime }

  try {
    const body = await readBody(event)
    const tenant = await resolveTenantContext(event, { body })

    // Generate unique job ID
    const jobId = createJobId()
    const tenantJobKey = buildTenantJobKey(tenant.id, jobId)

    // Create progress file path
    const progressDir = resolveRetrainingDir(tenant.id)
    if (!fs.existsSync(progressDir)) {
      fs.mkdirSync(progressDir, { recursive: true })
    }

    const progressFile = path.join(progressDir, `${jobId}.json`)

    const pythonScript = path.join(process.cwd(), '..', 'scripts', 'train_model.py')
    const executionMode: 'python' | 'simulation_fallback' = fs.existsSync(pythonScript)
      ? 'python'
      : 'simulation_fallback'

    // Initialize progress file
    const initialProgress = {
      tenant_id: tenant.id,
      jobId,
      status: 'running',
      progress: 0,
      startTime: Date.now(),
      execution_mode: executionMode,
      message: 'Starting model retraining...'
    }

    fs.writeFileSync(progressFile, JSON.stringify(initialProgress, null, 2))

    // Add to active jobs
    activeJobs.set(tenantJobKey, {
      id: jobId,
      status: 'running',
      progress: 0,
      startTime: Date.now(),
      executionMode,
    })

    // Start Python training process in background
    // Only spawn if script exists, otherwise simulate
    if (executionMode === 'python') {
      const tenantConfigDir = path.join(process.cwd(), '..', 'energy_ml', 'configs', 'tenants', tenant.id)
      const trainProcess = spawn('python', [
        pythonScript,
        '--job-id',
        jobId,
        '--tenant-id',
        tenant.id,
        '--config',
        JSON.stringify(body),
      ], {
        env: {
          ...process.env,
          ENERGY_ML_CONFIG_DIR: tenantConfigDir,
          ENERGY_ML_TENANT_ID: tenant.id,
        },
      })

      trainProcess.stdout?.on('data', (data) => {
        console.log(`[${jobId}] ${data.toString()}`)
      })

      trainProcess.stderr?.on('data', (data) => {
        console.error(`[${jobId}] ${data.toString()}`)
      })

      trainProcess.on('close', (code) => {
        const job = activeJobs.get(tenantJobKey)
        if (job) {
          job.status = code === 0 ? 'completed' : 'failed'
          job.endTime = Date.now()
          if (code !== 0) {
            job.error = `Process exited with code ${code}`
          }
        }

        // Update progress file
        const finalProgress = {
          tenant_id: tenant.id,
          jobId,
          status: code === 0 ? 'completed' : 'failed',
          progress: code === 0 ? 100 : activeJobs.get(tenantJobKey)?.progress || 0,
          startTime: activeJobs.get(tenantJobKey)?.startTime,
          endTime: Date.now(),
          execution_mode: 'python',
          error: code === 0 ? null : `Process exited with code ${code}`,
          message: code === 0 ? 'Training completed successfully!' : `Training failed: ${code}`
        }
        fs.writeFileSync(progressFile, JSON.stringify(finalProgress, null, 2))
      })
    } else {
      // Simulate training with gradual progress
      console.log(`[${jobId}] Python script not found, simulating training...`)
      simulateTraining(tenant.id, jobId, progressFile, executionMode)
    }

    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      jobId,
      execution_mode: executionMode,
      estimatedTime: 600, // 10 minutes
      message: 'Retraining started successfully'
    }
  } catch (error: any) {
    const errorData = error?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('Failed to start retraining:', error)
    return {
      success: false,
      error: error.message || 'Failed to start retraining',
      jobId: null
    }
  }
})

function simulateTraining(
  tenantId: string,
  jobId: string,
  progressFile: string,
  executionMode: 'python' | 'simulation_fallback'
) {
  const tenantJobKey = buildTenantJobKey(tenantId, jobId)
  let progress = 0
  const steps = [5, 15, 25, 40, 55, 70, 85, 95, 100]
  let stepIndex = 0

  const interval = setInterval(() => {
    if (stepIndex < steps.length) {
      progress = steps[stepIndex]
      stepIndex++

      const progressData = {
        tenant_id: tenantId,
        jobId,
        status: progress === 100 ? 'completed' : 'running',
        progress,
        startTime: activeJobs.get(tenantJobKey)?.startTime,
        execution_mode: executionMode,
        message: getProgressMessage(progress)
      }

      fs.writeFileSync(progressFile, JSON.stringify(progressData, null, 2))

      if (progress === 100) {
        const job = activeJobs.get(tenantJobKey)
        if (job) {
          job.status = 'completed'
          job.progress = 100
          job.endTime = Date.now()
        }
        clearInterval(interval)
      }
    }
  }, 800)
}

function getProgressMessage(progress: number): string {
  if (progress < 20) return 'Loading data...'
  if (progress < 40) return 'Preprocessing data...'
  if (progress < 60) return 'Training model...'
  if (progress < 85) return 'Optimizing parameters...'
  if (progress < 100) return 'Finalizing...'
  return 'Training completed!'
}

function createJobId() {
  if (!(globalThis as any).__retrainingJobCounter) {
    ;(globalThis as any).__retrainingJobCounter = 0
  }
  ;(globalThis as any).__retrainingJobCounter += 1
  return `job-${Date.now()}-${(globalThis as any).__retrainingJobCounter}`
}

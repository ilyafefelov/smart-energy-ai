// server/api/retraining/start.ts - Start model retraining

import fs from 'fs'
import path from 'path'
import { spawn } from 'child_process'

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

export default defineEventHandler(async (event) => {
  // POST /api/retraining/start
  // STANDARDIZED RESPONSE: { success, jobId, estimatedTime }

  try {
    const body = await readBody(event)

    // Generate unique job ID
    const jobId = createJobId()

    // Create progress file path
    const progressDir = path.join(process.cwd(), 'data', 'retraining')
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
      jobId,
      status: 'running',
      progress: 0,
      startTime: Date.now(),
      execution_mode: executionMode,
      message: 'Starting model retraining...'
    }

    fs.writeFileSync(progressFile, JSON.stringify(initialProgress, null, 2))

    // Add to active jobs
    activeJobs.set(jobId, {
      id: jobId,
      status: 'running',
      progress: 0,
      startTime: Date.now(),
      executionMode,
    })

    // Start Python training process in background
    // Only spawn if script exists, otherwise simulate
    if (executionMode === 'python') {
      const trainProcess = spawn('python', [pythonScript, '--job-id', jobId, '--config', JSON.stringify(body)])

      trainProcess.stdout?.on('data', (data) => {
        console.log(`[${jobId}] ${data.toString()}`)
      })

      trainProcess.stderr?.on('data', (data) => {
        console.error(`[${jobId}] ${data.toString()}`)
      })

      trainProcess.on('close', (code) => {
        const job = activeJobs.get(jobId)
        if (job) {
          job.status = code === 0 ? 'completed' : 'failed'
          job.endTime = Date.now()
          if (code !== 0) {
            job.error = `Process exited with code ${code}`
          }
        }

        // Update progress file
        const finalProgress = {
          jobId,
          status: code === 0 ? 'completed' : 'failed',
          progress: code === 0 ? 100 : activeJobs.get(jobId)?.progress || 0,
          startTime: activeJobs.get(jobId)?.startTime,
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
      simulateTraining(jobId, progressFile, executionMode)
    }

    return {
      success: true,
      jobId,
      execution_mode: executionMode,
      estimatedTime: 600, // 10 minutes
      message: 'Retraining started successfully'
    }
  } catch (error: any) {
    console.error('Failed to start retraining:', error)
    return {
      success: false,
      error: error.message || 'Failed to start retraining',
      jobId: null
    }
  }
})

function simulateTraining(
  jobId: string,
  progressFile: string,
  executionMode: 'python' | 'simulation_fallback'
) {
  let progress = 0
  const steps = [5, 15, 25, 40, 55, 70, 85, 95, 100]
  let stepIndex = 0

  const interval = setInterval(() => {
    if (stepIndex < steps.length) {
      progress = steps[stepIndex]
      stepIndex++

      const progressData = {
        jobId,
        status: progress === 100 ? 'completed' : 'running',
        progress,
        startTime: activeJobs.get(jobId)?.startTime,
        execution_mode: executionMode,
        message: getProgressMessage(progress)
      }

      fs.writeFileSync(progressFile, JSON.stringify(progressData, null, 2))

      if (progress === 100) {
        const job = activeJobs.get(jobId)
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

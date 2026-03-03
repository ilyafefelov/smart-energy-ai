// server/api/retraining/progress.ts - Check retraining progress

import fs from 'fs'
import path from 'path'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

export default defineEventHandler(async (event) => {
  // GET /api/retraining/progress?jobId=...
  // STANDARDIZED RESPONSE: { success, status, progress, message, error?, metrics? }

  try {
    const query = getQuery(event)
    const tenant = await resolveTenantContext(event)
    const jobId = query.jobId as string

    if (!jobId) {
      return {
        success: false,
        error: 'Missing jobId parameter'
      }
    }

    const progressFile = path.join(process.cwd(), 'data', 'tenants', tenant.id, 'retraining', `${jobId}.json`)

    if (!fs.existsSync(progressFile)) {
      return {
        success: false,
        error: 'Job not found',
        status: 'unknown'
      }
    }

    const progressData = JSON.parse(fs.readFileSync(progressFile, 'utf-8'))

    const response: any = {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      status: progressData.status,
      progress: progressData.progress,
      execution_mode: progressData.execution_mode || 'python',
      message: progressData.message
    }

    if (progressData.error) {
      response.error = progressData.error
    }

    // If completed, try to load metrics
    if (progressData.status === 'completed') {
      const metricsFile = path.join(process.cwd(), 'data', 'tenants', tenant.id, 'retraining', `${jobId}-metrics.json`)
      if (fs.existsSync(metricsFile)) {
        const metrics = JSON.parse(fs.readFileSync(metricsFile, 'utf-8'))
        response.metrics = metrics
      } else {
        response.metrics = null
        response.metrics_available = false
        response.metrics_message = 'Training metrics artifact not found for this job'
      }
    }

    return response
  } catch (error: any) {
    const errorData = error?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('Failed to check retraining progress:', error)
    return {
      success: false,
      error: error.message || 'Failed to check progress',
      status: 'error'
    }
  }
})

// server/api/retraining/cancel.ts - Cancel retraining

import fs from 'fs'
import path from 'path'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

export default defineEventHandler(async (event) => {
  // POST /api/retraining/cancel?jobId=...
  // STANDARDIZED RESPONSE: { success, message }

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
        error: 'Job not found'
      }
    }

    const progressData = JSON.parse(fs.readFileSync(progressFile, 'utf-8'))

    if (progressData.status !== 'running') {
      return {
        success: false,
        error: `Cannot cancel job with status: ${progressData.status}`
      }
    }

    // Update status to cancelled
    progressData.status = 'failed'
    progressData.endTime = Date.now()
    progressData.error = 'Cancelled by user'
    progressData.message = 'Training cancelled'

    fs.writeFileSync(progressFile, JSON.stringify(progressData, null, 2))

    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      message: 'Retraining cancelled successfully'
    }
  } catch (error: any) {
    const errorData = error?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('Failed to cancel retraining:', error)
    return {
      success: false,
      error: error.message || 'Failed to cancel retraining'
    }
  }
})

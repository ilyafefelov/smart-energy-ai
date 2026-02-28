/**
 * ML Recalculation Status API Endpoint
 * Returns current status of ML pipeline recalculation
 */
import { readFileSync, existsSync } from 'fs'
import { join } from 'path'

export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const jobId = query.jobId as string | undefined
    
    const statusPath = join(process.cwd(), '../energy_ml/configs/recalculation_status.json')
    
    if (!existsSync(statusPath)) {
      return {
        success: true,
        status: 'idle',
        progress: 0,
        stage: 'Ready',
        details: 'No recalculation in progress',
        message: 'ML pipeline is idle and ready for recalculation'
      }
    }
    
    try {
      const statusData = readFileSync(statusPath, 'utf-8')
      const status = JSON.parse(statusData)
      
      // Filter by job ID if provided
      if (jobId && status.jobId !== jobId) {
        return {
          success: false,
          error: `Job ID ${jobId} not found`,
          currentJobId: status.jobId || null
        }
      }
      
      // Check if process is stale (older than 10 minutes)
      const now = Date.now()
      const statusTime = status.timestamp ? new Date(status.timestamp).getTime() : now
      const isStale = (now - statusTime) > 10 * 60 * 1000 // 10 minutes
      
      if (isStale && status.status === 'running') {
        return {
          success: true,
          status: 'failed',
          progress: status.progress || 0,
          stage: 'Timeout',
          details: 'Recalculation process appears to have stalled',
          error: 'Process timeout - may have crashed or been interrupted',
          jobId: status.jobId
        }
      }
      
      return {
        success: true,
        jobId: status.jobId,
        status: status.status || 'unknown',
        progress: status.progress || 0,
        stage: status.stage || 'Unknown',
        details: status.details || 'No details available',
        startTime: status.startTime,
        completedAt: status.completedAt,
        failedAt: status.failedAt,
        results: status.results,
        error: status.error,
        timestamp: status.timestamp
      }
      
    } catch (parseError) {
      console.error('Failed to parse status file:', parseError)
      return {
        success: false,
        error: 'Failed to parse status file - may be corrupted',
        status: 'unknown'
      }
    }
    
  } catch (error) {
    console.error('Status check error:', error)
    
    throw createError({
      statusCode: 500,
      statusMessage: 'Internal server error checking recalculation status'
    })
  }
})
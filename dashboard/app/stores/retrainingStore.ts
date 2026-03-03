import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useTenantContext } from '~/composables/useTenantContext'

export interface RetrainingJob {
  id: string
  status: 'idle' | 'running' | 'completed' | 'failed'
  progress: number
  startTime: Date | null
  endTime: Date | null
  error?: string
  message: string
  estimatedTimeRemaining: number // in seconds
  metricsImprovement?: {
    previousAccuracy: number
    newAccuracy: number
    improvementPercent: number
  }
}

const DEFAULT_JOB: RetrainingJob = {
  id: '',
  status: 'idle',
  progress: 0,
  startTime: null,
  endTime: null,
  message: 'Ready to train',
  estimatedTimeRemaining: 0
}

export const useRetrainingStore = defineStore('retraining', () => {
  const tenantContext = useTenantContext()
  const job = ref<RetrainingJob>({ ...DEFAULT_JOB })
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const progressInterval = ref<NodeJS.Timeout | null>(null)
  const pollInterval = ref<NodeJS.Timeout | null>(null)
  const history = ref<RetrainingJob[]>([])

  // Getters
  const isRunning = computed(() => job.value.status === 'running')
  const isCompleted = computed(() => job.value.status === 'completed')
  const isFailed = computed(() => job.value.status === 'failed')
  const isIdle = computed(() => job.value.status === 'idle')

  const progressPercent = computed(() => job.value.progress)
  const progressPercentFormatted = computed(() => `${Math.round(job.value.progress)}%`)

  const timeRemaining = computed(() => {
    const seconds = job.value.estimatedTimeRemaining
    if (seconds < 60) return `${seconds}s`
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`
    return `${Math.round(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`
  })

  const statusIcon = computed(() => {
    switch (job.value.status) {
      case 'running':
        return '⚙️'
      case 'completed':
        return '✅'
      case 'failed':
        return '❌'
      default:
        return '⏱️'
    }
  })

  const statusColor = computed(() => {
    switch (job.value.status) {
      case 'running':
        return 'yellow'
      case 'completed':
        return 'green'
      case 'failed':
        return 'red'
      default:
        return 'slate'
    }
  })

  // Actions
  const startRetraining = async (configOverrides?: any) => {
    if (isRunning.value) {
      error.value = 'Retraining already in progress'
      return { success: false, error: error.value }
    }

    isLoading.value = true
    error.value = null

    try {
      await tenantContext.loadTenants()
      const tenantId = tenantContext.currentTenantId.value
      const response = await $fetch('/api/retraining/start', {
        method: 'POST',
        query: {
          tenantId,
        },
        headers: {
          'x-tenant-id': tenantId,
        },
        body: {
          ...(configOverrides || {}),
          tenantId,
        },
      }) as any

      if (response.success && response.jobId) {
        job.value = {
          id: response.jobId,
          status: 'running',
          progress: 0,
          startTime: new Date(),
          endTime: null,
          message: 'Training started...',
          estimatedTimeRemaining: response.estimatedTime || 600
        }

        // Start polling for progress
        startProgressPolling()

        return { success: true, jobId: response.jobId }
      } else {
        throw new Error(response.error || 'Failed to start retraining')
      }
    } catch (e) {
      const errorMsg = (e as Error).message
      console.error('Failed to start retraining:', e)
      error.value = errorMsg
      job.value = {
        ...job.value,
        status: 'failed',
        error: errorMsg,
        message: `Failed: ${errorMsg}`
      }
      return { success: false, error: errorMsg }
    } finally {
      isLoading.value = false
    }
  }

  const checkRetrainingStatus = async () => {
    if (!job.value.id || job.value.status !== 'running') {
      return
    }

    try {
      await tenantContext.loadTenants()
      const tenantId = tenantContext.currentTenantId.value
      const response = await $fetch('/api/retraining/progress', {
        query: {
          tenantId,
          jobId: job.value.id,
        },
        headers: {
          'x-tenant-id': tenantId,
        },
      }) as any

      if (response.success) {
        const progress = response.progress || job.value.progress
        const timeRemaining = Math.max(0, job.value.estimatedTimeRemaining - 1)

        // Decrease estimated time remaining
        job.value.estimatedTimeRemaining = timeRemaining

        if (response.status === 'completed') {
          job.value = {
            ...job.value,
            status: 'completed',
            progress: 100,
            endTime: new Date(),
            message: 'Training completed successfully!',
            estimatedTimeRemaining: 0,
            metricsImprovement: response.metrics
          }
          stopProgressPolling()
          // Save to history
          history.value.push({ ...job.value })
        } else if (response.status === 'failed') {
          job.value = {
            ...job.value,
            status: 'failed',
            error: response.error || 'Training failed',
            message: `Failed: ${response.error}`,
            endTime: new Date()
          }
          stopProgressPolling()
          history.value.push({ ...job.value })
        } else {
          // Update progress
          job.value.progress = Math.min(progress, 99)
          job.value.message = response.message || 'Training in progress...'
        }
      }
    } catch (e) {
      console.error('Failed to check retraining status:', e)
      // Continue polling even if this fails
    }
  }

  const startProgressPolling = () => {
    if (pollInterval.value) {
      clearInterval(pollInterval.value)
    }

    // Poll every 2 seconds
    pollInterval.value = setInterval(() => {
      checkRetrainingStatus()
    }, 2000)
  }

  const stopProgressPolling = () => {
    if (pollInterval.value) {
      clearInterval(pollInterval.value)
      pollInterval.value = null
    }
  }

  const cancelRetraining = async () => {
    if (!isRunning.value) {
      return { success: false, error: 'No active retraining' }
    }

    try {
      await tenantContext.loadTenants()
      const tenantId = tenantContext.currentTenantId.value
      const response = await $fetch('/api/retraining/cancel', {
        method: 'POST',
        query: {
          tenantId,
          jobId: job.value.id,
        },
        headers: {
          'x-tenant-id': tenantId,
        },
      }) as any

      if (response.success) {
        stopProgressPolling()
        job.value = {
          ...job.value,
          status: 'failed',
          endTime: new Date(),
          message: 'Training cancelled by user'
        }
        return { success: true }
      } else {
        throw new Error(response.error || 'Failed to cancel retraining')
      }
    } catch (e) {
      console.error('Failed to cancel retraining:', e)
      error.value = (e as Error).message
      return { success: false, error: error.value }
    }
  }

  const resetJob = () => {
    stopProgressPolling()
    job.value = { ...DEFAULT_JOB }
    error.value = null
  }

  const clearError = () => {
    error.value = null
  }

  const getLastSuccess = () => {
    return history.value.reverse().find(j => j.status === 'completed') || null
  }

  return {
    // State
    job,
    isLoading,
    error,
    history,

    // Getters
    isRunning,
    isCompleted,
    isFailed,
    isIdle,
    progressPercent,
    progressPercentFormatted,
    timeRemaining,
    statusIcon,
    statusColor,

    // Actions
    startRetraining,
    checkRetrainingStatus,
    startProgressPolling,
    stopProgressPolling,
    cancelRetraining,
    resetJob,
    clearError,
    getLastSuccess
  }
})

import { ref, computed, onMounted, onUnmounted } from 'vue'

export const useBatteryStatus = () => {
  const status = ref(null)
  const error = ref(null)
  const loading = ref(false)
  let pollInterval: NodeJS.Timeout | null = null
  
  const fetchStatus = async () => {
    loading.value = true
    try {
      status.value = await $fetch('/api/battery/status?simulate=true')
      error.value = null
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch battery status'
      console.error('Battery status fetch failed:', e)
    } finally {
      loading.value = false
    }
  }
  
  const updateSOC = async (newSOC: number) => {
    try {
      const result = await $fetch('/api/battery/update', {
        method: 'POST',
        body: { soc: newSOC }
      })
      status.value = result
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update SOC'
      return false
    }
  }
  
  // Auto-polling setup
  onMounted(() => {
    // Initial fetch
    fetchStatus()
    
    // Poll every 5 seconds
    pollInterval = setInterval(() => {
      fetchStatus()
    }, 5000)
  })
  
  // Auto-cleanup
  onUnmounted(() => {
    if (pollInterval) {
      clearInterval(pollInterval)
    }
  })
  
  return {
    status: computed(() => status.value),
    error: computed(() => error.value),
    loading: computed(() => loading.value),
    fetchStatus,
    updateSOC
  }
}

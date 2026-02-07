import { ref } from 'vue'

const defaultSettings = {
  general: {
    siteName: 'Factory #1',
    timezone: 'Europe/Kiev (GMT+2)',
    currency: 'UAH',
    notificationsEnabled: true
  },
  battery: {
    capacity: 150,
    minSOC: 15,
    maxChargeRate: 50,
    maxDischargeRate: 50
  },
  notifications: {
    highPrice: true,
    highPriceThreshold: 13.0,
    lowPrice: true,
    lowPriceThreshold: 7.0,
    modelComplete: true,
    systemAlerts: true
  },
  model: {
    learningRate: 0.0003,
    batchSize: 64,
    epochs: 20
  }
}

export const useSettings = () => {
  // Initialize from localStorage or use defaults
  const settings = ref({ ...defaultSettings })
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const loadSettings = async () => {
    isLoading.value = true
    error.value = null

    try {
      // Try to load from API first
      const response = await $fetch('/api/settings/load')

      if (response.success && response.settings) {
        Object.assign(settings.value, response.settings)
      } else if (process.client) {
        // Fallback to localStorage
        const saved = localStorage.getItem('energy_settings')
        if (saved) {
          const parsed = JSON.parse(saved)
          Object.assign(settings.value, parsed)
        }
      }
    } catch (e) {
      console.warn('Failed to load settings from API:', e)
      // Fallback to localStorage
      if (process.client) {
        try {
          const saved = localStorage.getItem('energy_settings')
          if (saved) {
            const parsed = JSON.parse(saved)
            Object.assign(settings.value, parsed)
          }
        } catch (localErr) {
          console.warn('Failed to load settings from localStorage:', localErr)
          error.value = 'Failed to load settings'
        }
      }
    } finally {
      isLoading.value = false
    }
  }

  const saveSettings = async (newSettings?: any) => {
    isLoading.value = true
    error.value = null

    try {
      const dataToSave = newSettings || settings.value

      // Save to API
      const response = await $fetch('/api/settings/save', {
        method: 'POST',
        body: dataToSave
      })

      if (response.success) {
        // Update local state
        if (newSettings) {
          Object.assign(settings.value, newSettings)
        }

        // Also save to localStorage as backup
        if (process.client) {
          localStorage.setItem('energy_settings', JSON.stringify(settings.value))
        }

        return { success: true }
      } else {
        throw new Error(response.error || 'Failed to save settings')
      }
    } catch (e) {
      const errorMsg = (e as Error).message
      console.error('Save failed:', e)
      error.value = errorMsg
      return { success: false, error: errorMsg }
    } finally {
      isLoading.value = false
    }
  }

  const resetSettings = async () => {
    try {
      Object.assign(settings.value, defaultSettings)
      if (process.client) {
        localStorage.removeItem('energy_settings')
      }
      await saveSettings(defaultSettings)
    } catch (e) {
      console.error('Reset failed:', e)
      error.value = (e as Error).message
    }
  }

  return {
    settings,
    saveSettings,
    resetSettings,
    loadSettings,
    isLoading,
    error
  }
}

import { ref, computed } from 'vue'

export const useSettings = () => {
  // Initialize from localStorage or use defaults
  const settings = ref({
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
  })

  const saveSettings = async (newSettings: any) => {
    try {
      // Save to localStorage
      if (process.client) {
        localStorage.setItem('energy_settings', JSON.stringify(newSettings))
      }

      // Update state
      Object.assign(settings.value, newSettings)

      return { success: true }
    } catch (e) {
      console.error('Save failed:', e)
      return { success: false, error: (e as Error).message }
    }
  }

  const resetSettings = () => {
    if (process.client) {
      localStorage.removeItem('energy_settings')
    }
  }

  const loadSettings = async () => {
    if (process.client) {
      try {
        const saved = localStorage.getItem('energy_settings')
        if (saved) {
          const parsed = JSON.parse(saved)
          Object.assign(settings.value, parsed)
        }
      } catch (e) {
        console.warn('Failed to load settings from localStorage:', e)
      }
    }
  }

  return {
    settings: computed(() => settings.value),
    saveSettings,
    resetSettings,
    loadSettings
  }
}

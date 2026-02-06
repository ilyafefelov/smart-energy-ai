import { useState, computed } from '#app'

export const useSettings = () => {
  // Default settings
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

  // Initialize from localStorage
  const settings = useState('energy_settings', () => {
    if (process.client) {
      try {
        const saved = localStorage.getItem('energy_settings')
        if (saved) {
          const parsed = JSON.parse(saved)
          // Merge with defaults to handle missing keys
          return {
            general: { ...defaultSettings.general, ...parsed.general },
            battery: { ...defaultSettings.battery, ...parsed.battery },
            notifications: { ...defaultSettings.notifications, ...parsed.notifications },
            model: { ...defaultSettings.model, ...parsed.model }
          }
        }
      } catch (e) {
        console.warn('Failed to load settings from localStorage:', e)
      }
    }

    return JSON.parse(JSON.stringify(defaultSettings))
  })

  const saveSettings = async (newSettings: any) => {
    try {
      // Save to localStorage immediately
      localStorage.setItem('energy_settings', JSON.stringify(newSettings))

      // Optionally: sync to backend
      if (!process.server) {
        try {
          const response = await $fetch('/api/settings/save', {
            method: 'POST',
            body: newSettings
          })

          // Update state with response
          if (response && response.settings) {
            Object.assign(settings.value, response.settings)
          }

          return { success: true, message: 'Settings saved locally and synced to backend' }
        } catch (e: any) {
          console.warn('Backend sync failed, using local storage only:', e)
          // Continue anyway - localStorage works offline
          return { success: true, message: 'Settings saved locally (offline mode)' }
        }
      }

      // Update state
      Object.assign(settings.value, newSettings)

      return { success: true, message: 'Settings saved successfully' }
    } catch (e: any) {
      console.error('Save failed:', e)
      return { success: false, error: e.message }
    }
  }

  const loadSettings = async () => {
    try {
      if (!process.server) {
        const response = await $fetch('/api/settings/load')

        if (response && response.settings) {
          // Merge loaded settings with current state
          const merged = {
            general: { ...settings.value.general, ...response.settings.general },
            battery: { ...settings.value.battery, ...response.settings.battery },
            notifications: { ...settings.value.notifications, ...response.settings.notifications },
            model: { ...settings.value.model, ...response.settings.model }
          }
          Object.assign(settings.value, merged)
          return { success: true }
        }
      }
    } catch (e: any) {
      console.warn('Failed to load settings from backend:', e)
      // Settings already loaded from localStorage, no error
    }

    return { success: true }
  }

  const resetSettings = () => {
    // Reset localStorage
    localStorage.removeItem('energy_settings')
    // Reset state
    Object.assign(settings.value, JSON.parse(JSON.stringify(defaultSettings)))
  }

  const resetAndReload = () => {
    resetSettings()
    if (process.client) {
      location.reload() // Reload with defaults
    }
  }

  return {
    settings: computed(() => settings.value),
    saveSettings,
    loadSettings,
    resetSettings,
    resetAndReload,
    defaultSettings
  }
}

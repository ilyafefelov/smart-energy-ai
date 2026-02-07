import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface GeneralSettings {
  siteName: string
  timezone: string
  currency: string
  notificationsEnabled: boolean
}

export interface BatterySettings {
  capacity: number
  minSOC: number
  maxChargeRate: number
  maxDischargeRate: number
}

export interface NotificationSettings {
  highPrice: boolean
  highPriceThreshold: number
  lowPrice: boolean
  lowPriceThreshold: number
  modelComplete: boolean
  systemAlerts: boolean
}

export interface ModelSettings {
  learningRate: number
  batchSize: number
  epochs: number
}

export interface Settings {
  general: GeneralSettings
  battery: BatterySettings
  notifications: NotificationSettings
  model: ModelSettings
}

const DEFAULT_SETTINGS: Settings = {
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

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref<Settings>({ ...DEFAULT_SETTINGS })
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)
  const lastSaveTime = ref<Date | null>(null)
  const isDirty = ref(false)

  // Getters
  const generalSettings = computed(() => settings.value.general)
  const batterySettings = computed(() => settings.value.battery)
  const notificationSettings = computed(() => settings.value.notifications)
  const modelSettings = computed(() => settings.value.model)

  const hasError = computed(() => error.value !== null)
  const isModified = computed(() => isDirty.value)

  // Actions
  const loadSettings = async () => {
    isLoading.value = true
    error.value = null

    try {
      // PRIORITY 1: Try localStorage first (client-side, always available)
      if (process.client) {
        const saved = localStorage.getItem('energy_settings')
        if (saved) {
          try {
            const parsed = JSON.parse(saved)
            settings.value = {
              general: { ...DEFAULT_SETTINGS.general, ...parsed.general },
              battery: { ...DEFAULT_SETTINGS.battery, ...parsed.battery },
              notifications: { ...DEFAULT_SETTINGS.notifications, ...parsed.notifications },
              model: { ...DEFAULT_SETTINGS.model, ...parsed.model }
            }
            console.log('[Settings] Loaded from localStorage:', settings.value)
            isDirty.value = false
            return
          } catch (err) {
            console.warn('[Settings] localStorage parse failed:', err)
          }
        }
      }

      // PRIORITY 2: Try backend API
      try {
        const response = await $fetch('/api/settings/load') as any

        if (response.success && response.settings) {
          settings.value = {
            general: { ...DEFAULT_SETTINGS.general, ...response.settings.general },
            battery: { ...DEFAULT_SETTINGS.battery, ...response.settings.battery },
            notifications: { ...DEFAULT_SETTINGS.notifications, ...response.settings.notifications },
            model: { ...DEFAULT_SETTINGS.model, ...response.settings.model }
          }
          console.log('[Settings] Loaded from backend API:', settings.value)
          
          // Also persist to localStorage
          if (process.client) {
            localStorage.setItem('energy_settings', JSON.stringify(settings.value))
          }
          
          isDirty.value = false
        }
      } catch (apiErr) {
        console.warn('[Settings] Backend API load failed:', apiErr)
      }
    } catch (e) {
      console.error('Failed to load settings:', e)
      error.value = 'Failed to load settings'
    } finally {
      isLoading.value = false
    }
  }

  const saveSettings = async (newSettings?: Partial<Settings>) => {
    isSaving.value = true
    error.value = null

    try {
      const dataToSave = newSettings ? { ...settings.value, ...newSettings } : settings.value

      // PRIORITY 1: Save to localStorage (always works, client-side)
      if (process.client) {
        localStorage.setItem('energy_settings', JSON.stringify(dataToSave))
        console.log('[Settings] Saved to localStorage:', dataToSave)
      }

      // PRIORITY 2: Try to save to backend (may fail, but try)
      try {
        const response = await $fetch('/api/settings/save', {
          method: 'POST',
          body: dataToSave
        }) as any

        if (response.success) {
          console.log('[Settings] Saved to backend:', response)
        } else {
          console.warn('[Settings] Backend save returned error:', response.error)
        }
      } catch (apiErr) {
        console.warn('[Settings] Backend save failed, but localStorage persisted:', apiErr)
      }

      // Mark as saved (success because localStorage definitely worked)
      Object.assign(settings.value, dataToSave)
      isDirty.value = false
      lastSaveTime.value = new Date()

      return { success: true }
    } catch (e) {
      const errorMsg = (e as Error).message
      console.error('Save failed:', e)
      error.value = errorMsg
      return { success: false, error: errorMsg }
    } finally {
      isSaving.value = false
    }
  }

  const updateGeneralSettings = async (updates: Partial<GeneralSettings>) => {
    settings.value.general = { ...settings.value.general, ...updates }
    isDirty.value = true
    return saveSettings()
  }

  const updateBatterySettings = async (updates: Partial<BatterySettings>) => {
    settings.value.battery = { ...settings.value.battery, ...updates }
    isDirty.value = true
    return saveSettings()
  }

  const updateNotificationSettings = async (updates: Partial<NotificationSettings>) => {
    settings.value.notifications = { ...settings.value.notifications, ...updates }
    isDirty.value = true
    return saveSettings()
  }

  const updateModelSettings = async (updates: Partial<ModelSettings>) => {
    settings.value.model = { ...settings.value.model, ...updates }
    isDirty.value = true
    return saveSettings()
  }

  const resetToDefaults = async () => {
    settings.value = { ...DEFAULT_SETTINGS }
    isDirty.value = true
    return saveSettings()
  }

  const clearError = () => {
    error.value = null
  }

  return {
    // State
    settings,
    isLoading,
    isSaving,
    error,
    lastSaveTime,
    isDirty,

    // Getters
    generalSettings,
    batterySettings,
    notificationSettings,
    modelSettings,
    hasError,
    isModified,

    // Actions
    loadSettings,
    saveSettings,
    updateGeneralSettings,
    updateBatterySettings,
    updateNotificationSettings,
    updateModelSettings,
    resetToDefaults,
    clearError
  }
})

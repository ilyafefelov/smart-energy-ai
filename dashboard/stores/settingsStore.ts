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

const STORAGE_KEY = 'energy_settings_v1'

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
      // Only try localStorage (skip API entirely for now)
      if (typeof window !== 'undefined' && window.localStorage) {
        const saved = localStorage.getItem(STORAGE_KEY)
        if (saved) {
          try {
            const parsed = JSON.parse(saved)
            console.log('[SettingsStore] Loaded from localStorage:', parsed)
            settings.value = {
              general: { ...DEFAULT_SETTINGS.general, ...parsed.general },
              battery: { ...DEFAULT_SETTINGS.battery, ...parsed.battery },
              notifications: { ...DEFAULT_SETTINGS.notifications, ...parsed.notifications },
              model: { ...DEFAULT_SETTINGS.model, ...parsed.model }
            }
            isDirty.value = false
            return
          } catch (parseErr) {
            console.error('[SettingsStore] Failed to parse localStorage:', parseErr)
            error.value = 'Failed to parse saved settings'
          }
        }
      }

      // No saved settings found, use defaults
      console.log('[SettingsStore] No saved settings found, using defaults')
      settings.value = { ...DEFAULT_SETTINGS }
    } catch (e) {
      console.error('[SettingsStore] Error loading settings:', e)
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

      // Save to localStorage
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(dataToSave))
        console.log('[SettingsStore] Saved to localStorage:', dataToSave)
      } else {
        throw new Error('localStorage not available')
      }

      // Update state
      Object.assign(settings.value, dataToSave)
      isDirty.value = false
      lastSaveTime.value = new Date()

      console.log('[SettingsStore] Settings saved successfully')
      return { success: true }
    } catch (e) {
      const errorMsg = (e as Error).message
      console.error('[SettingsStore] Save failed:', e)
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

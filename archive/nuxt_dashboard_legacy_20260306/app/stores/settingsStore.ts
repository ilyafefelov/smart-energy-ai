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
  maxSOC: number
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

export interface GenerationSettings {
  solarCapacity: number
  windCapacity: number
}

export interface ModelSettings {
  learningRate: number
  batchSize: number
  epochs: number
}

export interface OptimizationSettings {
  strategy: 'savings' | 'balanced' | 'longevity'
  currentElectricityCost: number  // ₴/kWh - non-optimized baseline cost
}

export interface Settings {
  general: GeneralSettings
  battery: BatterySettings
  generation: GenerationSettings
  notifications: NotificationSettings
  model: ModelSettings
  optimization: OptimizationSettings
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
    maxSOC: 95,
    maxChargeRate: 50,
    maxDischargeRate: 50
  },
  generation: {
    solarCapacity: 50,
    windCapacity: 10
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
  },
  optimization: {
    strategy: 'balanced',
    currentElectricityCost: 12.0  // ₴/kWh baseline cost
  }
}

const STORAGE_KEY = 'energy_settings_v1'

type LegacyConfigState = Record<string, unknown> & {
  battery_capacity_kwh?: number
  battery_c_rate_charge?: number
  battery_c_rate_discharge?: number
  battery_soc_min?: number
  battery_soc_max?: number
  solar_capacity_kw?: number
  wind_capacity_kw?: number
  optimization_strategy?: string
}

const OPTIMIZATION_STRATEGY_MAP: Record<OptimizationSettings['strategy'], string> = {
  savings: 'max_earn',
  balanced: 'balanced',
  longevity: 'max_battery_health'
}

function buildLegacyConfigUpdate(currentConfig: LegacyConfigState, appSettings: Settings): LegacyConfigState {
  const batteryCapacity = appSettings.battery.capacity > 0
    ? appSettings.battery.capacity
    : (currentConfig.battery_capacity_kwh ?? DEFAULT_SETTINGS.battery.capacity)

  return {
    ...currentConfig,
    battery_capacity_kwh: batteryCapacity,
    battery_c_rate_charge: appSettings.battery.maxChargeRate / batteryCapacity,
    battery_c_rate_discharge: appSettings.battery.maxDischargeRate / batteryCapacity,
    battery_soc_min: appSettings.battery.minSOC / 100,
    battery_soc_max: appSettings.battery.maxSOC / 100,
    solar_capacity_kw: appSettings.generation.solarCapacity,
    wind_capacity_kw: appSettings.generation.windCapacity,
    optimization_strategy: OPTIMIZATION_STRATEGY_MAP[appSettings.optimization.strategy]
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
  const generationSettings = computed(() => settings.value.generation)
  const notificationSettings = computed(() => settings.value.notifications)
  const modelSettings = computed(() => settings.value.model)
  const optimizationSettings = computed(() => settings.value.optimization)

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
              generation: { ...DEFAULT_SETTINGS.generation, ...parsed.generation },
              notifications: { ...DEFAULT_SETTINGS.notifications, ...parsed.notifications },
              model: { ...DEFAULT_SETTINGS.model, ...parsed.model },
              optimization: { ...DEFAULT_SETTINGS.optimization, ...parsed.optimization }
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

  const syncToConfig = async (appSettings: Settings) => {
    try {
      const currentConfigResponse = await $fetch<{ data?: LegacyConfigState }>("/api/config/current")
      const currentConfig = currentConfigResponse.data ?? {}
      const updatedConfig = buildLegacyConfigUpdate(currentConfig, appSettings)

      const saveResponse = await $fetch<{ recalculation?: { triggered?: boolean } }>("/api/config/save", {
        method: "POST",
        body: updatedConfig
      })

      if (!saveResponse.recalculation?.triggered) {
        await $fetch("/api/ml/recalculate", {
          method: "POST",
          body: {}
        })
      }
    } catch (e) {
      console.warn("Failed to sync settings to config endpoints:", e)
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
      }

      await syncToConfig(dataToSave)

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

  const updateGenerationSettings = async (updates: Partial<GenerationSettings>) => {
    settings.value.generation = { ...settings.value.generation, ...updates }
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

  const updateOptimization = (updates: Partial<OptimizationSettings>) => {
    settings.value.optimization = { ...settings.value.optimization, ...updates }
    saveSettings()
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
    generationSettings,
    notificationSettings,
    modelSettings,
    optimizationSettings,
    hasError,
    isModified,

    // Actions
    loadSettings,
    saveSettings,
    updateGeneralSettings,
    updateBatterySettings,
    updateGenerationSettings,
    updateNotificationSettings,
    updateModelSettings,
    updateOptimization,
    resetToDefaults,
    clearError
  }
})

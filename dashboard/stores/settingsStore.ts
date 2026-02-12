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

export interface UserConfigSettings {
  // Battery Configuration (Phase 4B Extended)
  battery_type: 'LFP' | 'Lead-Acid' | 'VRFB'
  battery_capacity_kwh: number
  battery_efficiency: number
  battery_c_rate_charge: number
  battery_c_rate_discharge: number
  battery_dod_max: number
  battery_soc_min: number
  battery_soc_max: number
  battery_cycles_max: number
  battery_degradation_per_cycle: number
  
  // Load Profile Configuration (Phase 4C Extended)
  load_profile_type: 'standard' | 'multi_shift' | '24_7' | 'custom'
  load_peak_kw: number
  load_base_kw: number
  load_custom_hourly?: number[]
  load_seasonal_variation: number
  load_weekend_factor: number
  load_night_factor: number
  
  // Tariff Configuration (Phase 4D)
  tariff_region: 'ukraine'
  tariff_peak_hours_start: number
  tariff_peak_hours_end: number
  tariff_peak_rate_uah_kwh: number
  tariff_off_peak_rate_uah_kwh: number
  
  // ML Configuration (Phase 4E)
  ml_retrain_frequency_days: number
  ml_confidence_threshold: number
  ml_model_type: 'xgboost' | 'lightgbm' | 'catboost' | 'ensemble'
  ml_lookback_hours: number
  ml_forecast_horizon_hours: number
  
  // Dashboard Preferences (Phase 4F)
  dashboard_refresh_seconds: number
  dashboard_show_degradation_cost: boolean
  dashboard_show_arbitrage_opportunities: boolean
  dashboard_currency_symbol: string
  dashboard_language: 'en' | 'uk'
}

export interface Settings {
  general: GeneralSettings
  battery: BatterySettings
  notifications: NotificationSettings
  model: ModelSettings
  userConfig?: UserConfigSettings
}

const DEFAULT_USER_CONFIG: UserConfigSettings = {
  // Battery Configuration
  battery_type: 'LFP',
  battery_capacity_kwh: 10.0,
  battery_efficiency: 0.95,
  battery_c_rate_charge: 0.5,
  battery_c_rate_discharge: 1.0,
  battery_dod_max: 0.9,
  battery_soc_min: 0.1,
  battery_soc_max: 1.0,
  battery_cycles_max: 8000,
  battery_degradation_per_cycle: 0.0000125,
  
  // Load Profile Configuration
  load_profile_type: 'standard',
  load_peak_kw: 10.0,
  load_base_kw: 2.0,
  load_custom_hourly: undefined,
  load_seasonal_variation: 0.2,
  load_weekend_factor: 0.6,
  load_night_factor: 0.3,
  
  // Tariff Configuration
  tariff_region: 'ukraine',
  tariff_peak_hours_start: 6,
  tariff_peak_hours_end: 23,
  tariff_peak_rate_uah_kwh: 12.5,
  tariff_off_peak_rate_uah_kwh: 8.0,
  
  // ML Configuration
  ml_retrain_frequency_days: 7,
  ml_confidence_threshold: 0.7,
  ml_model_type: 'ensemble',
  ml_lookback_hours: 168,
  ml_forecast_horizon_hours: 24,
  
  // Dashboard Preferences
  dashboard_refresh_seconds: 30,
  dashboard_show_degradation_cost: true,
  dashboard_show_arbitrage_opportunities: true,
  dashboard_currency_symbol: '₴',
  dashboard_language: 'en'
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
  },
  userConfig: DEFAULT_USER_CONFIG
}

const STORAGE_KEY = 'energy_settings_v2'

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
  const userConfig = computed(() => settings.value.userConfig || DEFAULT_USER_CONFIG)

  const hasError = computed(() => error.value !== null)
  const isModified = computed(() => isDirty.value)

  // Battery-specific getters
  const batteryConfig = computed(() => ({
    battery_type: userConfig.value.battery_type,
    battery_capacity_kwh: userConfig.value.battery_capacity_kwh,
    battery_efficiency: userConfig.value.battery_efficiency,
    battery_c_rate_charge: userConfig.value.battery_c_rate_charge,
    battery_c_rate_discharge: userConfig.value.battery_c_rate_discharge,
    battery_dod_max: userConfig.value.battery_dod_max,
    battery_soc_min: userConfig.value.battery_soc_min,
    battery_soc_max: userConfig.value.battery_soc_max,
    battery_cycles_max: userConfig.value.battery_cycles_max,
    battery_degradation_per_cycle: userConfig.value.battery_degradation_per_cycle
  }))

  const loadConfig = computed(() => ({
    load_profile_type: userConfig.value.load_profile_type,
    load_peak_kw: userConfig.value.load_peak_kw,
    load_base_kw: userConfig.value.load_base_kw,
    load_custom_hourly: userConfig.value.load_custom_hourly,
    load_seasonal_variation: userConfig.value.load_seasonal_variation,
    load_weekend_factor: userConfig.value.load_weekend_factor,
    load_night_factor: userConfig.value.load_night_factor
  }))

  const tariffConfig = computed(() => ({
    tariff_region: userConfig.value.tariff_region,
    tariff_peak_hours_start: userConfig.value.tariff_peak_hours_start,
    tariff_peak_hours_end: userConfig.value.tariff_peak_hours_end,
    tariff_peak_rate_uah_kwh: userConfig.value.tariff_peak_rate_uah_kwh,
    tariff_off_peak_rate_uah_kwh: userConfig.value.tariff_off_peak_rate_uah_kwh
  }))

  const mlConfig = computed(() => ({
    ml_retrain_frequency_days: userConfig.value.ml_retrain_frequency_days,
    ml_confidence_threshold: userConfig.value.ml_confidence_threshold,
    ml_model_type: userConfig.value.ml_model_type,
    ml_lookback_hours: userConfig.value.ml_lookback_hours,
    ml_forecast_horizon_hours: userConfig.value.ml_forecast_horizon_hours
  }))

  // Actions
  const loadSettings = async () => {
    isLoading.value = true
    error.value = null

    try {
      // Try loading from API first
      try {
        const response = await $fetch('/api/config/current')
        if (response.success && response.data) {
          settings.value.userConfig = { ...DEFAULT_USER_CONFIG, ...response.data }
          isDirty.value = false
          console.log('[SettingsStore] Loaded from API:', settings.value.userConfig)
          return
        }
      } catch (apiError) {
        console.warn('[SettingsStore] API load failed, trying localStorage:', apiError)
      }

      // Fall back to localStorage
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
              model: { ...DEFAULT_SETTINGS.model, ...parsed.model },
              userConfig: { ...DEFAULT_USER_CONFIG, ...parsed.userConfig }
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

      // Save to localStorage as backup
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(dataToSave))
        console.log('[SettingsStore] Saved to localStorage:', dataToSave)
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

  // Enhanced user config methods
  const updateBatteryConfig = async (updates: Partial<UserConfigSettings>) => {
    if (!settings.value.userConfig) {
      settings.value.userConfig = { ...DEFAULT_USER_CONFIG }
    }
    
    // Update battery-specific fields
    Object.assign(settings.value.userConfig, updates)
    isDirty.value = true
    
    // Save to API
    try {
      const response = await $fetch('/api/settings/battery', {
        method: 'POST',
        body: updates
      })
      
      if (response.success) {
        lastSaveTime.value = new Date()
        return { success: true, recalculation: response.recalculation }
      } else {
        throw new Error('API save failed')
      }
    } catch (apiError) {
      // Fall back to localStorage only
      await saveSettings()
      return { success: true, recalculation: null }
    }
  }

  const updateLoadConfig = async (updates: Partial<UserConfigSettings>) => {
    if (!settings.value.userConfig) {
      settings.value.userConfig = { ...DEFAULT_USER_CONFIG }
    }
    
    // Update load profile specific fields
    Object.assign(settings.value.userConfig, updates)
    isDirty.value = true
    
    // Save to API
    try {
      const response = await $fetch('/api/settings/load-profile', {
        method: 'POST',
        body: updates
      })
      
      if (response.success) {
        lastSaveTime.value = new Date()
        return { success: true, recalculation: response.recalculation }
      } else {
        throw new Error('API save failed')
      }
    } catch (apiError) {
      // Fall back to localStorage only
      await saveSettings()
      return { success: true, recalculation: null }
    }
  }

  const updateUserConfig = async (updates: Partial<UserConfigSettings>) => {
    if (!settings.value.userConfig) {
      settings.value.userConfig = { ...DEFAULT_USER_CONFIG }
    }
    
    Object.assign(settings.value.userConfig, updates)
    isDirty.value = true
    
    // Save to API
    try {
      const response = await $fetch('/api/config/save', {
        method: 'POST',
        body: settings.value.userConfig
      })
      
      if (response.success) {
        lastSaveTime.value = new Date()
        return { success: true, recalculation: response.recalculation }
      } else {
        throw new Error('API save failed')
      }
    } catch (apiError) {
      // Fall back to localStorage only
      await saveSettings()
      return { success: true, recalculation: null }
    }
  }

  const triggerRecalculation = async () => {
    try {
      const response = await $fetch('/api/ml/recalculate', {
        method: 'POST',
        body: {}
      })
      return response
    } catch (error) {
      console.error('Failed to trigger recalculation:', error)
      return { success: false, error: error.message }
    }
  }

  // Computed helper methods
  const getBatterySpecs = () => {
    const type = userConfig.value.battery_type
    const specs = {
      'LFP': {
        name: 'Lithium Iron Phosphate',
        cycles_max: 8000,
        cost_uah_per_kwh: 13000,
        efficiency_typical: 0.95,
        degradation_low: true
      },
      'Lead-Acid': {
        name: 'Lead-Acid Deep Cycle',
        cycles_max: 600,
        cost_uah_per_kwh: 5500,
        efficiency_typical: 0.85,
        degradation_low: false
      },
      'VRFB': {
        name: 'Vanadium Redox Flow Battery',
        cycles_max: 20000,
        cost_uah_per_kwh: 22000,
        efficiency_typical: 0.75,
        degradation_low: true
      }
    }
    return specs[type] || specs['LFP']
  }

  const calculateArbitrageMetrics = () => {
    const config = userConfig.value
    const usableCapacity = config.battery_capacity_kwh * config.battery_dod_max
    const priceSpread = config.tariff_peak_rate_uah_kwh - config.tariff_off_peak_rate_uah_kwh
    
    const dailyArbitrageGross = usableCapacity * priceSpread * config.battery_efficiency
    const specs = getBatterySpecs()
    const degradationCost = config.battery_capacity_kwh * specs.cost_uah_per_kwh / specs.cycles_max
    const dailyProfitNet = dailyArbitrageGross - degradationCost
    
    return {
      daily_arbitrage_gross: Math.round(dailyArbitrageGross * 100) / 100,
      daily_degradation_cost: Math.round(degradationCost * 100) / 100,
      daily_profit_net: Math.round(dailyProfitNet * 100) / 100,
      annual_profit: Math.round(dailyProfitNet * 365),
      payback_period_years: dailyProfitNet > 0 
        ? Math.round((config.battery_capacity_kwh * specs.cost_uah_per_kwh) / (dailyProfitNet * 365) * 10) / 10
        : null,
      usable_capacity_kwh: Math.round(usableCapacity * 100) / 100
    }
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
    userConfig,
    batteryConfig,
    loadConfig,
    tariffConfig,
    mlConfig,
    hasError,
    isModified,

    // Actions
    loadSettings,
    saveSettings,
    updateGeneralSettings,
    updateBatterySettings,
    updateNotificationSettings,
    updateModelSettings,
    updateBatteryConfig,
    updateLoadConfig,
    updateUserConfig,
    resetToDefaults,
    clearError,
    triggerRecalculation,
    
    // Helper methods
    getBatterySpecs,
    calculateArbitrageMetrics
  }
})

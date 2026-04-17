import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useTenantContext } from '~/composables/useTenantContext'

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

export type UserConfigLoadProfileType = 'standard' | 'multi-shift' | '24/7' | 'multi_shift' | '24_7' | 'custom'

export interface UserConfigSettings {
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
  load_profile_type: UserConfigLoadProfileType
  load_peak_kw: number
  load_base_kw: number
  load_custom_hourly: number[]
  load_seasonal_variation: number
  load_weekend_factor: number
  load_night_factor: number
  tariff_region: string
  tariff_peak_hours_start: number
  tariff_peak_hours_end: number
  tariff_peak_rate_uah_kwh: number
  tariff_off_peak_rate_uah_kwh: number
  ml_retrain_frequency_days: number
  ml_confidence_threshold: number
  ml_model_type: string
  ml_lookback_hours: number
  ml_forecast_horizon_hours: number
  dashboard_refresh_seconds: number
  dashboard_show_degradation_cost: boolean
  dashboard_show_arbitrage_opportunities: boolean
  dashboard_currency_symbol: string
  dashboard_language: string
  optimization_strategy: string
  custom_optimization_weights: unknown
  has_solar: boolean
  has_wind: boolean
  solar_capacity_kw: number
  wind_capacity_kw: number
  solar_efficiency: number
  wind_efficiency: number
  solar_tilt_deg: number
  wind_cut_in_speed_mps: number
  wind_rated_speed_mps: number
  latitude: number
  longitude: number
  timezone: string
  connected_power_kw: number
  market_regime_override: string
}

export interface Settings {
  general: GeneralSettings
  battery: BatterySettings
  notifications: NotificationSettings
  model: ModelSettings
  userConfig?: UserConfigSettings
}

interface SettingsLoadResponse {
  success?: boolean
  settings?: Partial<Settings>
  error?: string
}

interface ConfigLoadResponse {
  success?: boolean
  data?: Partial<UserConfigSettings>
  error?: string
}

interface ConfigSaveResponse {
  success?: boolean
  error?: string
  recalculation?: unknown
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
  userConfig: undefined,
}

const DEFAULT_USER_CONFIG: UserConfigSettings = {
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
  load_profile_type: 'standard',
  load_peak_kw: 10.0,
  load_base_kw: 2.0,
  load_custom_hourly: Array.from({ length: 24 }, () => 0.5),
  load_seasonal_variation: 0.2,
  load_weekend_factor: 0.6,
  load_night_factor: 0.3,
  tariff_region: 'ukraine',
  tariff_peak_hours_start: 6,
  tariff_peak_hours_end: 23,
  tariff_peak_rate_uah_kwh: 12.5,
  tariff_off_peak_rate_uah_kwh: 8.0,
  ml_retrain_frequency_days: 7,
  ml_confidence_threshold: 0.7,
  ml_model_type: 'ensemble',
  ml_lookback_hours: 168,
  ml_forecast_horizon_hours: 24,
  dashboard_refresh_seconds: 30,
  dashboard_show_degradation_cost: true,
  dashboard_show_arbitrage_opportunities: true,
  dashboard_currency_symbol: '₴',
  dashboard_language: 'en',
  optimization_strategy: 'balanced',
  custom_optimization_weights: null,
  has_solar: false,
  has_wind: false,
  solar_capacity_kw: 0,
  wind_capacity_kw: 0,
  solar_efficiency: 0.2,
  wind_efficiency: 0.35,
  solar_tilt_deg: 30,
  wind_cut_in_speed_mps: 3,
  wind_rated_speed_mps: 12,
  latitude: 50.45,
  longitude: 30.52,
  timezone: 'Europe/Kiev',
  connected_power_kw: 10.0,
  market_regime_override: 'auto',
}

type TenantRequest = {
  query: {
    tenantId: string
  }
  headers: {
    'x-tenant-id': string
  }
}

const storageKeyForTenant = (tenantId: string) => `energy_settings_v2_${tenantId}`

const toFiniteNumber = (value: unknown, fallback: number) => {
  const numericValue = Number(value)
  return Number.isFinite(numericValue) ? numericValue : fallback
}

const normalizeLoadProfileType = (value: unknown): UserConfigLoadProfileType => {
  const normalized = String(value || '').trim().toLowerCase()
  if (normalized === 'multi-shift') return 'multi-shift'
  if (normalized === 'multi_shift') return 'multi_shift'
  if (normalized === '24/7') return '24/7'
  if (normalized === '24_7') return '24_7'
  if (normalized === 'custom') return 'custom'
  return 'standard'
}

const normalizeBatteryType = (value: unknown): UserConfigSettings['battery_type'] => {
  if (value === 'Lead-Acid' || value === 'VRFB') {
    return value
  }
  return 'LFP'
}

const normalizeUserConfig = (value?: Partial<UserConfigSettings> | null): UserConfigSettings => ({
  ...DEFAULT_USER_CONFIG,
  ...value,
  battery_type: normalizeBatteryType(value?.battery_type),
  battery_capacity_kwh: toFiniteNumber(value?.battery_capacity_kwh, DEFAULT_USER_CONFIG.battery_capacity_kwh),
  battery_efficiency: toFiniteNumber(value?.battery_efficiency, DEFAULT_USER_CONFIG.battery_efficiency),
  battery_c_rate_charge: toFiniteNumber(value?.battery_c_rate_charge, DEFAULT_USER_CONFIG.battery_c_rate_charge),
  battery_c_rate_discharge: toFiniteNumber(value?.battery_c_rate_discharge, DEFAULT_USER_CONFIG.battery_c_rate_discharge),
  battery_dod_max: toFiniteNumber(value?.battery_dod_max, DEFAULT_USER_CONFIG.battery_dod_max),
  battery_soc_min: toFiniteNumber(value?.battery_soc_min, DEFAULT_USER_CONFIG.battery_soc_min),
  battery_soc_max: toFiniteNumber(value?.battery_soc_max, DEFAULT_USER_CONFIG.battery_soc_max),
  battery_cycles_max: toFiniteNumber(value?.battery_cycles_max, DEFAULT_USER_CONFIG.battery_cycles_max),
  battery_degradation_per_cycle: toFiniteNumber(value?.battery_degradation_per_cycle, DEFAULT_USER_CONFIG.battery_degradation_per_cycle),
  load_profile_type: normalizeLoadProfileType(value?.load_profile_type),
  load_peak_kw: toFiniteNumber(value?.load_peak_kw, DEFAULT_USER_CONFIG.load_peak_kw),
  load_base_kw: toFiniteNumber(value?.load_base_kw, DEFAULT_USER_CONFIG.load_base_kw),
  load_custom_hourly: Array.isArray(value?.load_custom_hourly)
    ? value.load_custom_hourly.map((entry) => toFiniteNumber(entry, 0.5))
    : [...DEFAULT_USER_CONFIG.load_custom_hourly],
  load_seasonal_variation: toFiniteNumber(value?.load_seasonal_variation, DEFAULT_USER_CONFIG.load_seasonal_variation),
  load_weekend_factor: toFiniteNumber(value?.load_weekend_factor, DEFAULT_USER_CONFIG.load_weekend_factor),
  load_night_factor: toFiniteNumber(value?.load_night_factor, DEFAULT_USER_CONFIG.load_night_factor),
  tariff_region: String(value?.tariff_region || DEFAULT_USER_CONFIG.tariff_region),
  tariff_peak_hours_start: toFiniteNumber(value?.tariff_peak_hours_start, DEFAULT_USER_CONFIG.tariff_peak_hours_start),
  tariff_peak_hours_end: toFiniteNumber(value?.tariff_peak_hours_end, DEFAULT_USER_CONFIG.tariff_peak_hours_end),
  tariff_peak_rate_uah_kwh: toFiniteNumber(value?.tariff_peak_rate_uah_kwh, DEFAULT_USER_CONFIG.tariff_peak_rate_uah_kwh),
  tariff_off_peak_rate_uah_kwh: toFiniteNumber(value?.tariff_off_peak_rate_uah_kwh, DEFAULT_USER_CONFIG.tariff_off_peak_rate_uah_kwh),
  ml_retrain_frequency_days: toFiniteNumber(value?.ml_retrain_frequency_days, DEFAULT_USER_CONFIG.ml_retrain_frequency_days),
  ml_confidence_threshold: toFiniteNumber(value?.ml_confidence_threshold, DEFAULT_USER_CONFIG.ml_confidence_threshold),
  ml_model_type: String(value?.ml_model_type || DEFAULT_USER_CONFIG.ml_model_type),
  ml_lookback_hours: toFiniteNumber(value?.ml_lookback_hours, DEFAULT_USER_CONFIG.ml_lookback_hours),
  ml_forecast_horizon_hours: toFiniteNumber(value?.ml_forecast_horizon_hours, DEFAULT_USER_CONFIG.ml_forecast_horizon_hours),
  dashboard_refresh_seconds: toFiniteNumber(value?.dashboard_refresh_seconds, DEFAULT_USER_CONFIG.dashboard_refresh_seconds),
  dashboard_show_degradation_cost: typeof value?.dashboard_show_degradation_cost === 'boolean'
    ? value.dashboard_show_degradation_cost
    : DEFAULT_USER_CONFIG.dashboard_show_degradation_cost,
  dashboard_show_arbitrage_opportunities: typeof value?.dashboard_show_arbitrage_opportunities === 'boolean'
    ? value.dashboard_show_arbitrage_opportunities
    : DEFAULT_USER_CONFIG.dashboard_show_arbitrage_opportunities,
  dashboard_currency_symbol: String(value?.dashboard_currency_symbol || DEFAULT_USER_CONFIG.dashboard_currency_symbol),
  dashboard_language: String(value?.dashboard_language || DEFAULT_USER_CONFIG.dashboard_language),
  optimization_strategy: String(value?.optimization_strategy || DEFAULT_USER_CONFIG.optimization_strategy),
  custom_optimization_weights: value?.custom_optimization_weights ?? DEFAULT_USER_CONFIG.custom_optimization_weights,
  has_solar: typeof value?.has_solar === 'boolean' ? value.has_solar : DEFAULT_USER_CONFIG.has_solar,
  has_wind: typeof value?.has_wind === 'boolean' ? value.has_wind : DEFAULT_USER_CONFIG.has_wind,
  solar_capacity_kw: toFiniteNumber(value?.solar_capacity_kw, DEFAULT_USER_CONFIG.solar_capacity_kw),
  wind_capacity_kw: toFiniteNumber(value?.wind_capacity_kw, DEFAULT_USER_CONFIG.wind_capacity_kw),
  solar_efficiency: toFiniteNumber(value?.solar_efficiency, DEFAULT_USER_CONFIG.solar_efficiency),
  wind_efficiency: toFiniteNumber(value?.wind_efficiency, DEFAULT_USER_CONFIG.wind_efficiency),
  solar_tilt_deg: toFiniteNumber(value?.solar_tilt_deg, DEFAULT_USER_CONFIG.solar_tilt_deg),
  wind_cut_in_speed_mps: toFiniteNumber(value?.wind_cut_in_speed_mps, DEFAULT_USER_CONFIG.wind_cut_in_speed_mps),
  wind_rated_speed_mps: toFiniteNumber(value?.wind_rated_speed_mps, DEFAULT_USER_CONFIG.wind_rated_speed_mps),
  latitude: toFiniteNumber(value?.latitude, DEFAULT_USER_CONFIG.latitude),
  longitude: toFiniteNumber(value?.longitude, DEFAULT_USER_CONFIG.longitude),
  timezone: String(value?.timezone || DEFAULT_USER_CONFIG.timezone),
  connected_power_kw: toFiniteNumber(value?.connected_power_kw, DEFAULT_USER_CONFIG.connected_power_kw),
  market_regime_override: String(value?.market_regime_override || DEFAULT_USER_CONFIG.market_regime_override),
})

export const useSettingsStore = defineStore('settings', () => {
  const tenantContext = useTenantContext()
  const settings = ref<Settings>({
    ...DEFAULT_SETTINGS,
    userConfig: { ...DEFAULT_USER_CONFIG },
  })
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
  const userConfig = computed(() => settings.value.userConfig || normalizeUserConfig())

  const hasError = computed(() => error.value !== null)
  const isModified = computed(() => isDirty.value)

  const getTenantRequest = async (): Promise<TenantRequest | undefined> => {
    await tenantContext.loadTenants().catch(() => undefined)
    const tenantId = typeof tenantContext.currentTenantId.value === 'string'
      ? tenantContext.currentTenantId.value.trim().toLowerCase()
      : ''

    if (!tenantId) {
      return undefined
    }

    return {
      query: {
        tenantId,
      },
      headers: {
        'x-tenant-id': tenantId,
      },
    }
  }

  const getStorageKey = () => storageKeyForTenant(tenantContext.currentTenantId.value || 'default')

  const syncDerivedSettings = (config: UserConfigSettings) => {
    settings.value.userConfig = config
    settings.value.general = {
      ...settings.value.general,
      timezone: config.timezone,
      currency: config.dashboard_currency_symbol === '$' ? 'USD' : 'UAH',
    }
    settings.value.battery = {
      ...settings.value.battery,
      capacity: config.battery_capacity_kwh,
      minSOC: Math.round(config.battery_soc_min * 100),
      maxChargeRate: Number((config.battery_capacity_kwh * config.battery_c_rate_charge).toFixed(2)),
      maxDischargeRate: Number((config.battery_capacity_kwh * config.battery_c_rate_discharge).toFixed(2)),
    }
  }

  const persistLocalSettings = () => {
    if (typeof window === 'undefined' || !window.localStorage) {
      return
    }

    localStorage.setItem(getStorageKey(), JSON.stringify(settings.value))
  }

  const loadFromLocalStorage = () => {
    if (typeof window === 'undefined' || !window.localStorage) {
      return false
    }

    const saved = localStorage.getItem(getStorageKey())
    if (!saved) {
      return false
    }

    const parsed = JSON.parse(saved)
    settings.value = {
      general: { ...DEFAULT_SETTINGS.general, ...parsed.general },
      battery: { ...DEFAULT_SETTINGS.battery, ...parsed.battery },
      notifications: { ...DEFAULT_SETTINGS.notifications, ...parsed.notifications },
      model: { ...DEFAULT_SETTINGS.model, ...parsed.model },
      userConfig: normalizeUserConfig(parsed.userConfig),
    }
    syncDerivedSettings(normalizeUserConfig(settings.value.userConfig))
    isDirty.value = false
    return true
  }

  // Actions
  const loadSettings = async () => {
    isLoading.value = true
    error.value = null

    try {
      const tenantRequest = await getTenantRequest()
      const [settingsResponse, configResponse] = await Promise.all([
        tenantRequest
          ? $fetch<SettingsLoadResponse>('/api/settings/load', tenantRequest).catch(() => null)
          : $fetch<SettingsLoadResponse>('/api/settings/load').catch(() => null),
        tenantRequest
          ? $fetch<ConfigLoadResponse>('/api/config/current', tenantRequest).catch(() => null)
          : $fetch<ConfigLoadResponse>('/api/config/current').catch(() => null),
      ])

      let loadedFromApi = false

      if (settingsResponse?.success && settingsResponse.settings) {
        const loaded = settingsResponse.settings
        settings.value = {
          general: { ...DEFAULT_SETTINGS.general, ...loaded.general },
          battery: { ...DEFAULT_SETTINGS.battery, ...loaded.battery },
          notifications: { ...DEFAULT_SETTINGS.notifications, ...loaded.notifications },
          model: { ...DEFAULT_SETTINGS.model, ...loaded.model },
          userConfig: settings.value.userConfig,
        }
        loadedFromApi = true
      }

      if (configResponse?.success && configResponse.data) {
        syncDerivedSettings(normalizeUserConfig(configResponse.data))
        loadedFromApi = true
      }

      if (loadedFromApi) {
        persistLocalSettings()
        isDirty.value = false
        return
      }

      throw new Error(settingsResponse?.error || configResponse?.error || 'Failed to load settings from API')
    } catch (e) {
      console.error('[SettingsStore] Error loading settings:', e)

      try {
        if (loadFromLocalStorage()) {
          return
        }
      } catch {
        // Fall through to defaults.
      }

      error.value = 'Failed to load settings'
      settings.value = {
        ...DEFAULT_SETTINGS,
        userConfig: { ...DEFAULT_USER_CONFIG },
      }
      syncDerivedSettings(userConfig.value)
    } finally {
      isLoading.value = false
    }
  }

  const saveSettings = async (newSettings?: Partial<Settings>) => {
    isSaving.value = true
    error.value = null

    try {
      const dataToSave: Settings = {
        general: { ...settings.value.general, ...newSettings?.general },
        battery: { ...settings.value.battery, ...newSettings?.battery },
        notifications: { ...settings.value.notifications, ...newSettings?.notifications },
        model: { ...settings.value.model, ...newSettings?.model },
        userConfig: normalizeUserConfig(newSettings?.userConfig ?? settings.value.userConfig),
      }

      const tenantRequest = await getTenantRequest()
      const response = tenantRequest
        ? await $fetch<{ success?: boolean; error?: string }>('/api/settings/save', {
            ...tenantRequest,
            method: 'POST',
            body: {
              ...dataToSave,
              tenantId: tenantRequest.query.tenantId,
            },
          })
        : await $fetch<{ success?: boolean; error?: string }>('/api/settings/save', {
            method: 'POST',
            body: dataToSave,
          })

      if (!response?.success) {
        throw new Error(response?.error || 'Settings save failed')
      }

      settings.value = dataToSave
  syncDerivedSettings(normalizeUserConfig(dataToSave.userConfig))
      persistLocalSettings()
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

  const saveUserConfig = async (updates: Partial<UserConfigSettings>) => {
    isSaving.value = true
    error.value = null

    try {
      const nextConfig = normalizeUserConfig({
        ...userConfig.value,
        ...updates,
      })

      const tenantRequest = await getTenantRequest()
      const response = tenantRequest
        ? await $fetch<ConfigSaveResponse>('/api/config/save', {
            ...tenantRequest,
            method: 'POST',
            body: {
              ...nextConfig,
              tenantId: tenantRequest.query.tenantId,
            },
          })
        : await $fetch<ConfigSaveResponse>('/api/config/save', {
            method: 'POST',
            body: nextConfig,
          })

      if (!response?.success) {
        throw new Error(response?.error || 'Configuration save failed')
      }

      syncDerivedSettings(nextConfig)
      persistLocalSettings()
      isDirty.value = false
      lastSaveTime.value = new Date()
      return { success: true, recalculation: response.recalculation ?? null }
    } catch (e) {
      const errorMsg = (e as Error).message
      console.error('[SettingsStore] Config save failed:', e)
      error.value = errorMsg
      return { success: false, error: errorMsg }
    } finally {
      isSaving.value = false
    }
  }

  const loadConfig = async () => {
    await loadSettings()
    return userConfig.value
  }

  const saveConfig = async (updates: Partial<UserConfigSettings>) => {
    return saveUserConfig(updates)
  }

  const updateBatteryConfig = async (updates: Partial<UserConfigSettings>) => {
    return saveUserConfig(updates)
  }

  const updateLoadConfig = async (updates: Partial<UserConfigSettings>) => {
    return saveUserConfig(updates)
  }

  const updateUserConfig = async (updates: Partial<UserConfigSettings>) => {
    return saveUserConfig(updates)
  }

  const triggerRecalculation = async () => {
    const tenantRequest = await getTenantRequest()

    try {
      return tenantRequest
        ? await $fetch('/api/ml/recalculate', {
            ...tenantRequest,
            method: 'POST',
          })
        : await $fetch('/api/ml/recalculate', {
            method: 'POST',
          })
    } catch (recalculationError) {
      console.error('Failed to trigger recalculation:', recalculationError)
      return {
        success: false,
        error: recalculationError instanceof Error ? recalculationError.message : 'Unknown error',
      }
    }
  }

  const getBatterySpecs = () => {
    const specs = {
      LFP: {
        name: 'Lithium Iron Phosphate',
        cycles_max: 8000,
        cost_uah_per_kwh: 13000,
        efficiency_typical: 0.95,
        degradation_low: true,
      },
      'Lead-Acid': {
        name: 'Lead-Acid Deep Cycle',
        cycles_max: 600,
        cost_uah_per_kwh: 5500,
        efficiency_typical: 0.85,
        degradation_low: false,
      },
      VRFB: {
        name: 'Vanadium Redox Flow Battery',
        cycles_max: 20000,
        cost_uah_per_kwh: 22000,
        efficiency_typical: 0.75,
        degradation_low: true,
      },
    }

    return specs[userConfig.value.battery_type] || specs.LFP
  }

  const calculateArbitrageMetrics = () => {
    const config = userConfig.value
    const usableCapacity = config.battery_capacity_kwh * config.battery_dod_max
    const priceSpread = config.tariff_peak_rate_uah_kwh - config.tariff_off_peak_rate_uah_kwh
    const specs = getBatterySpecs()

    const dailyArbitrageGross = usableCapacity * priceSpread * config.battery_efficiency
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
      usable_capacity_kwh: Math.round(usableCapacity * 100) / 100,
    }
  }

  const resetToDefaults = async () => {
    settings.value = {
      ...DEFAULT_SETTINGS,
      userConfig: { ...DEFAULT_USER_CONFIG },
    }
    syncDerivedSettings(userConfig.value)
    isDirty.value = true
    return saveUserConfig(userConfig.value)
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
    userConfig,
    hasError,
    isModified,

    // Actions
    loadSettings,
    saveSettings,
    loadConfig,
    saveConfig,
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
    getBatterySpecs,
    calculateArbitrageMetrics,
  }
})

<template>
  <div class="settings-page min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-6xl">
      <!-- Page Header -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Configuration Center
        </h1>
        <p class="text-lg text-gray-600 dark:text-gray-400">
          Configure your battery system, load profile, and ML settings for optimal energy arbitrage
        </p>
        <div class="flex items-center gap-4 mt-4">
          <UBadge 
            v-if="lastSaveTime" 
            color="green" 
            variant="soft"
            class="px-3 py-1"
          >
            ✓ Last saved {{ formatLastSaveTime() }}
          </UBadge>
          <UBadge 
            v-if="isDirty" 
            color="amber" 
            variant="soft"
            class="px-3 py-1"
          >
            ⚠ Unsaved changes
          </UBadge>
        </div>
      </div>

      <!-- Quick Stats Overview -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <UCard class="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950 dark:to-blue-900">
          <div class="text-center">
            <div class="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {{ currentConfig?.battery_capacity_kwh || 0 }}kWh
            </div>
            <div class="text-sm text-blue-700 dark:text-blue-300">
              {{ currentConfig?.battery_type || 'LFP' }} Battery
            </div>
          </div>
        </UCard>
        
        <UCard class="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-950 dark:to-green-900">
          <div class="text-center">
            <div class="text-2xl font-bold text-green-600 dark:text-green-400">
              {{ currentConfig?.load_peak_kw || 0 }}kW
            </div>
            <div class="text-sm text-green-700 dark:text-green-300">
              Peak Load
            </div>
          </div>
        </UCard>
        
        <UCard class="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-950 dark:to-purple-900">
          <div class="text-center">
            <div class="text-2xl font-bold text-purple-600 dark:text-purple-400">
              ₴{{ calculateArbitrageProfit().toFixed(0) }}
            </div>
            <div class="text-sm text-purple-700 dark:text-purple-300">
              Daily Profit Est.
            </div>
          </div>
        </UCard>
        
        <UCard class="bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-950 dark:to-orange-900">
          <div class="text-center">
            <div class="text-2xl font-bold text-orange-600 dark:text-orange-400">
              {{ getPaybackYears() }}
            </div>
            <div class="text-sm text-orange-700 dark:text-orange-300">
              Payback Years
            </div>
          </div>
        </UCard>
      </div>

      <!-- Main Configuration Sections -->
      <div class="space-y-8">
        <!-- Battery Configuration -->
        <section id="battery-config">
          <BatteryConfig @settings-changed="onSettingsChanged" />
        </section>

        <!-- Load Profile Configuration -->
        <section id="load-config">
          <LoadProfileConfig @settings-changed="onSettingsChanged" />
        </section>

        <!-- ML Model Retraining -->
        <section id="ml-retraining">
          <MLRetraining @retraining-complete="onRetrainingComplete" />
        </section>

        <!-- Advanced Settings -->
        <section id="advanced-settings">
          <UCard>
            <template #header>
              <div class="flex justify-between items-center">
                <h3 class="text-lg font-semibold flex items-center gap-2">
                  ⚙️ Advanced Settings
                </h3>
                <UButton
                  @click="showAdvanced = !showAdvanced"
                  variant="ghost"
                  :icon="showAdvanced ? 'i-heroicons-chevron-up' : 'i-heroicons-chevron-down'"
                  size="sm"
                >
                  {{ showAdvanced ? 'Hide' : 'Show' }} Advanced
                </UButton>
              </div>
            </template>

            <div v-if="showAdvanced" class="space-y-6">
              <!-- Tariff Settings -->
              <div>
                <h4 class="text-lg font-semibold mb-4 flex items-center gap-2">
                  💸 Electricity Tariff Settings
                </h4>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormGroup label="Peak Rate (UAH/kWh)" help="Electricity rate during peak hours">
                    <UInput 
                      v-model="tariffSettings.peak_rate"
                      type="number" 
                      step="0.1" 
                      min="5" 
                      max="25"
                      @input="onTariffChange"
                    >
                      <template #trailing>
                        <span class="text-gray-400 text-sm">₴/kWh</span>
                      </template>
                    </UInput>
                  </UFormGroup>
                  
                  <UFormGroup label="Off-Peak Rate (UAH/kWh)" help="Electricity rate during off-peak hours">
                    <UInput 
                      v-model="tariffSettings.off_peak_rate"
                      type="number" 
                      step="0.1" 
                      min="3" 
                      max="15"
                      @input="onTariffChange"
                    >
                      <template #trailing>
                        <span class="text-gray-400 text-sm">₴/kWh</span>
                      </template>
                    </UInput>
                  </UFormGroup>
                </div>
                
                <UAlert 
                  icon="i-heroicons-information-circle"
                  color="blue"
                  :title="`Price Spread: ₴${(tariffSettings.peak_rate - tariffSettings.off_peak_rate).toFixed(2)}/kWh`"
                  class="mt-4"
                >
                  <template #description>
                    Higher price spreads increase arbitrage opportunities. 
                    Current spread allows for ₴{{ ((tariffSettings.peak_rate - tariffSettings.off_peak_rate) * (currentConfig?.battery_capacity_kwh || 10) * 0.9).toFixed(0) }} max daily revenue.
                  </template>
                </UAlert>
              </div>

              <!-- ML Configuration -->
              <div>
                <h4 class="text-lg font-semibold mb-4 flex items-center gap-2">
                  🤖 Machine Learning Configuration
                </h4>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <UFormGroup label="Retrain Frequency" help="How often to retrain ML models">
                    <USelect 
                      v-model="mlSettings.retrain_frequency"
                      :options="retrainOptions"
                      @change="onMLSettingsChange"
                    />
                  </UFormGroup>
                  
                  <UFormGroup label="Confidence Threshold" help="Minimum confidence for ML predictions">
                    <URange 
                      v-model="mlSettings.confidence_threshold"
                      :min="0.5" 
                      :max="0.95" 
                      :step="0.05"
                      @input="onMLSettingsChange"
                    />
                    <div class="flex justify-between text-sm text-gray-600 mt-1">
                      <span>50%</span>
                      <span class="font-semibold">{{ (mlSettings.confidence_threshold * 100).toFixed(0) }}%</span>
                      <span>95%</span>
                    </div>
                  </UFormGroup>
                  
                  <UFormGroup label="Model Type" help="ML algorithm for predictions">
                    <USelect 
                      v-model="mlSettings.model_type"
                      :options="modelTypeOptions"
                      @change="onMLSettingsChange"
                    />
                  </UFormGroup>
                </div>
              </div>

              <!-- Dashboard Preferences -->
              <div>
                <h4 class="text-lg font-semibold mb-4 flex items-center gap-2">
                  📊 Dashboard Preferences
                </h4>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormGroup label="Refresh Interval" help="How often to update dashboard data">
                    <USelect 
                      v-model="dashboardSettings.refresh_seconds"
                      :options="refreshOptions"
                      @change="onDashboardSettingsChange"
                    />
                  </UFormGroup>
                  
                  <div class="space-y-3">
                    <UFormGroup label="Display Options">
                      <div class="space-y-2">
                        <UCheckbox
                          v-model="dashboardSettings.show_degradation_cost"
                          label="Show Battery Degradation Costs"
                          @change="onDashboardSettingsChange"
                        />
                        <UCheckbox
                          v-model="dashboardSettings.show_arbitrage_opportunities"
                          label="Show Arbitrage Opportunities"
                          @change="onDashboardSettingsChange"
                        />
                      </div>
                    </UFormGroup>
                  </div>
                </div>
              </div>

              <!-- Save Advanced Settings -->
              <div class="flex justify-end pt-4 border-t">
                <UButton 
                  @click="saveAdvancedSettings"
                  :loading="savingAdvanced"
                  size="lg"
                >
                  Save Advanced Settings
                </UButton>
              </div>
            </div>
          </UCard>
        </section>

        <!-- Configuration Export/Import -->
        <section id="config-management">
          <UCard>
            <template #header>
              <h3 class="text-lg font-semibold flex items-center gap-2">
                💾 Configuration Management
              </h3>
            </template>
            
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <UButton 
                @click="exportConfiguration"
                variant="outline"
                icon="i-heroicons-arrow-down-tray"
                block
              >
                Export Configuration
              </UButton>
              
              <UButton 
                @click="importConfiguration"
                variant="outline"
                icon="i-heroicons-arrow-up-tray"
                block
              >
                Import Configuration
              </UButton>
              
              <UButton 
                @click="resetToDefaults"
                variant="outline"
                color="red"
                icon="i-heroicons-arrow-path"
                block
              >
                Reset to Defaults
              </UButton>
            </div>

            <div class="mt-6 bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
              <h4 class="font-semibold mb-2 flex items-center gap-2">
                <UIcon name="i-heroicons-document-text" />
                Configuration Summary
              </h4>
              <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span class="text-gray-600 dark:text-gray-400">Battery:</span>
                  <div class="font-medium">{{ currentConfig?.battery_type }} {{ currentConfig?.battery_capacity_kwh }}kWh</div>
                </div>
                <div>
                  <span class="text-gray-600 dark:text-gray-400">Load Profile:</span>
                  <div class="font-medium capitalize">{{ currentConfig?.load_profile_type }}</div>
                </div>
                <div>
                  <span class="text-gray-600 dark:text-gray-400">ML Model:</span>
                  <div class="font-medium capitalize">{{ mlSettings.model_type }}</div>
                </div>
                <div>
                  <span class="text-gray-600 dark:text-gray-400">Last Update:</span>
                  <div class="font-medium">{{ formatLastSaveTime() || 'Never' }}</div>
                </div>
              </div>
            </div>
          </UCard>
        </section>
      </div>

      <!-- Floating Save Button (appears when there are unsaved changes) -->
      <div 
        v-if="isDirty"
        class="fixed bottom-6 right-6 z-50"
      >
        <UButton 
          @click="saveAllSettings"
          :loading="saving"
          size="lg"
          color="primary"
          icon="i-heroicons-cloud-arrow-up"
          class="shadow-lg"
        >
          {{ saving ? 'Saving...' : 'Save All Changes' }}
        </UButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useSettingsStore } from '~/stores/settingsStore'
import { useToast } from '#imports'
import BatteryConfig from '~/components/Settings/BatteryConfig.vue'
import LoadProfileConfig from '~/components/Settings/LoadProfileConfig.vue'
import MLRetraining from '~/components/Settings/MLRetraining.vue'

const settingsStore = useSettingsStore()
const toast = useToast()

// Component state
const showAdvanced = ref(false)
const saving = ref(false)
const savingAdvanced = ref(false)

// Current configuration
const currentConfig = computed(() => settingsStore.userConfig)
const isDirty = computed(() => settingsStore.isDirty)
const lastSaveTime = computed(() => settingsStore.lastSaveTime)

// Advanced settings
const tariffSettings = reactive({
  peak_rate: 12.5,
  off_peak_rate: 8.0
})

const mlSettings = reactive({
  retrain_frequency: 7,
  confidence_threshold: 0.7,
  model_type: 'ensemble'
})

const dashboardSettings = reactive({
  refresh_seconds: 30,
  show_degradation_cost: true,
  show_arbitrage_opportunities: true
})

// Options for dropdowns
const retrainOptions = [
  { label: 'Daily', value: 1 },
  { label: 'Weekly', value: 7 },
  { label: 'Bi-weekly', value: 14 },
  { label: 'Monthly', value: 30 }
]

const modelTypeOptions = [
  { label: 'XGBoost', value: 'xgboost' },
  { label: 'LightGBM', value: 'lightgbm' },
  { label: 'CatBoost', value: 'catboost' },
  { label: 'Ensemble', value: 'ensemble' }
]

const refreshOptions = [
  { label: '15 seconds', value: 15 },
  { label: '30 seconds', value: 30 },
  { label: '1 minute', value: 60 },
  { label: '2 minutes', value: 120 },
  { label: '5 minutes', value: 300 }
]

// Methods
const formatLastSaveTime = () => {
  if (!lastSaveTime.value) return null
  return lastSaveTime.value.toLocaleString()
}

const calculateArbitrageProfit = () => {
  const config = currentConfig.value
  if (!config) return 0
  
  const usableCapacity = config.battery_capacity_kwh * (config.battery_dod_max || 0.9)
  const priceSpread = tariffSettings.peak_rate - tariffSettings.off_peak_rate
  const efficiency = config.battery_efficiency || 0.95
  
  return usableCapacity * priceSpread * efficiency
}

const getPaybackYears = () => {
  const dailyProfit = calculateArbitrageProfit()
  const annualProfit = dailyProfit * 365
  const config = currentConfig.value
  
  if (!config || annualProfit <= 0) return '∞'
  
  const batterySpecs = settingsStore.getBatterySpecs()
  const investment = config.battery_capacity_kwh * batterySpecs.cost_uah_per_kwh
  const payback = investment / annualProfit
  
  return payback > 50 ? '>50' : payback.toFixed(1)
}

const onSettingsChanged = (settingsType: string) => {
  console.log(`Settings changed: ${settingsType}`)
  // Trigger any necessary updates
}

const onRetrainingComplete = (results: any) => {
  toast.add({
    title: 'ML Retraining Complete',
    description: `Models updated with ${results.accuracy}% accuracy`,
    icon: 'i-heroicons-check-circle',
    color: 'green'
  })
}

const onTariffChange = async () => {
  await settingsStore.updateUserConfig({
    tariff_peak_rate_uah_kwh: tariffSettings.peak_rate,
    tariff_off_peak_rate_uah_kwh: tariffSettings.off_peak_rate
  })
}

const onMLSettingsChange = async () => {
  await settingsStore.updateUserConfig({
    ml_retrain_frequency_days: mlSettings.retrain_frequency,
    ml_confidence_threshold: mlSettings.confidence_threshold,
    ml_model_type: mlSettings.model_type as any
  })
}

const onDashboardSettingsChange = async () => {
  await settingsStore.updateUserConfig({
    dashboard_refresh_seconds: dashboardSettings.refresh_seconds,
    dashboard_show_degradation_cost: dashboardSettings.show_degradation_cost,
    dashboard_show_arbitrage_opportunities: dashboardSettings.show_arbitrage_opportunities
  })
}

const saveAdvancedSettings = async () => {
  savingAdvanced.value = true
  
  try {
    await settingsStore.updateUserConfig({
      tariff_peak_rate_uah_kwh: tariffSettings.peak_rate,
      tariff_off_peak_rate_uah_kwh: tariffSettings.off_peak_rate,
      ml_retrain_frequency_days: mlSettings.retrain_frequency,
      ml_confidence_threshold: mlSettings.confidence_threshold,
      ml_model_type: mlSettings.model_type as any,
      dashboard_refresh_seconds: dashboardSettings.refresh_seconds,
      dashboard_show_degradation_cost: dashboardSettings.show_degradation_cost,
      dashboard_show_arbitrage_opportunities: dashboardSettings.show_arbitrage_opportunities
    })
    
    toast.add({
      title: 'Advanced Settings Saved',
      description: 'Your advanced configuration has been updated.',
      icon: 'i-heroicons-check-circle',
      color: 'green'
    })
  } catch (error) {
    toast.add({
      title: 'Save Failed',
      description: 'Could not save advanced settings.',
      icon: 'i-heroicons-x-circle',
      color: 'red'
    })
  } finally {
    savingAdvanced.value = false
  }
}

const saveAllSettings = async () => {
  saving.value = true
  
  try {
    await settingsStore.saveSettings()
    
    toast.add({
      title: 'Settings Saved',
      description: 'All configuration changes have been saved.',
      icon: 'i-heroicons-check-circle',
      color: 'green'
    })
  } catch (error) {
    toast.add({
      title: 'Save Failed',
      description: 'Could not save settings.',
      icon: 'i-heroicons-x-circle',
      color: 'red'
    })
  } finally {
    saving.value = false
  }
}

const exportConfiguration = () => {
  const config = {
    ...currentConfig.value,
    tariff: tariffSettings,
    ml: mlSettings,
    dashboard: dashboardSettings,
    exported_at: new Date().toISOString()
  }
  
  const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `energy-config-${new Date().toISOString().split('T')[0]}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  
  toast.add({
    title: 'Configuration Exported',
    description: 'Configuration file downloaded successfully.',
    icon: 'i-heroicons-arrow-down-tray',
    color: 'blue'
  })
}

const importConfiguration = () => {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json'
  
  input.onchange = async (e) => {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (!file) return
    
    try {
      const text = await file.text()
      const config = JSON.parse(text)
      
      // Validate and apply configuration
      if (config.battery_type && config.battery_capacity_kwh) {
        await settingsStore.updateUserConfig(config)
        
        // Update local advanced settings
        if (config.tariff) Object.assign(tariffSettings, config.tariff)
        if (config.ml) Object.assign(mlSettings, config.ml)
        if (config.dashboard) Object.assign(dashboardSettings, config.dashboard)
        
        toast.add({
          title: 'Configuration Imported',
          description: 'Settings have been loaded from file.',
          icon: 'i-heroicons-check-circle',
          color: 'green'
        })
      } else {
        throw new Error('Invalid configuration file')
      }
    } catch (error) {
      toast.add({
        title: 'Import Failed',
        description: 'Could not import configuration file.',
        icon: 'i-heroicons-x-circle',
        color: 'red'
      })
    }
  }
  
  input.click()
}

const resetToDefaults = async () => {
  try {
    await settingsStore.resetToDefaults()
    
    // Reset advanced settings to defaults
    tariffSettings.peak_rate = 12.5
    tariffSettings.off_peak_rate = 8.0
    mlSettings.retrain_frequency = 7
    mlSettings.confidence_threshold = 0.7
    mlSettings.model_type = 'ensemble'
    dashboardSettings.refresh_seconds = 30
    dashboardSettings.show_degradation_cost = true
    dashboardSettings.show_arbitrage_opportunities = true
    
    toast.add({
      title: 'Reset Complete',
      description: 'All settings have been reset to defaults.',
      icon: 'i-heroicons-arrow-path',
      color: 'blue'
    })
  } catch (error) {
    toast.add({
      title: 'Reset Failed',
      description: 'Could not reset settings.',
      icon: 'i-heroicons-x-circle',
      color: 'red'
    })
  }
}

// Initialize
onMounted(async () => {
  await settingsStore.loadSettings()
  
  // Load advanced settings from store
  const config = currentConfig.value
  if (config) {
    tariffSettings.peak_rate = config.tariff_peak_rate_uah_kwh || 12.5
    tariffSettings.off_peak_rate = config.tariff_off_peak_rate_uah_kwh || 8.0
    mlSettings.retrain_frequency = config.ml_retrain_frequency_days || 7
    mlSettings.confidence_threshold = config.ml_confidence_threshold || 0.7
    mlSettings.model_type = config.ml_model_type || 'ensemble'
    dashboardSettings.refresh_seconds = config.dashboard_refresh_seconds || 30
    dashboardSettings.show_degradation_cost = config.dashboard_show_degradation_cost ?? true
    dashboardSettings.show_arbitrage_opportunities = config.dashboard_show_arbitrage_opportunities ?? true
  }
})
</script>

<style scoped>
.settings-page {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  min-height: 100vh;
}

:deep(.dark) .settings-page {
  background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
}

.floating-save-button {
  animation: bounce 2s infinite;
}

@keyframes bounce {
  0%, 20%, 50%, 80%, 100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-10px);
  }
  60% {
    transform: translateY(-5px);
  }
}
</style>
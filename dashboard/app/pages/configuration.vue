<template>
  <div class="configuration-page">
    <div class="container mx-auto px-4 py-8 max-w-4xl">
      <div class="mb-8">
        <h1 class="text-4xl font-bold text-gray-900 dark:text-white">Configuration</h1>
        <p class="text-lg text-gray-600 dark:text-gray-300 mt-2">
          Configure your battery system and load profile for accurate optimization
        </p>
      </div>

      <!-- Success/Error Notifications -->
      <div v-if="successMessage" class="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
        <div class="flex items-center">
          <svg class="w-5 h-5 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
          </svg>
          <span class="text-green-700">{{ successMessage }}</span>
        </div>
      </div>

      <div v-if="errorMessage" class="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
        <div class="flex items-center">
          <svg class="w-5 h-5 text-red-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
          </svg>
          <span class="text-red-700">{{ errorMessage }}</span>
        </div>
      </div>

      <!-- Validation Errors -->
      <div v-if="validationErrors.length > 0" class="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <div class="flex items-start">
          <svg class="w-5 h-5 text-yellow-500 mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
          <div>
            <h3 class="font-medium text-yellow-800 mb-2">Configuration Errors</h3>
            <ul class="list-disc list-inside text-yellow-700">
              <li v-for="(error, idx) in validationErrors" :key="idx" class="text-sm">
                {{ error }}
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="settingsStore.isLoading" class="flex justify-center items-center py-8">
        <div class="text-center">
          <div class="animate-spin inline-block">
            <svg class="w-8 h-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
          <p class="mt-2 text-gray-600 dark:text-gray-400">Loading configuration...</p>
        </div>
      </div>

      <!-- Form -->
      <form v-else @submit.prevent="handleSave" class="space-y-8">
        <!-- Battery Configuration Section -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">
            <svg class="w-6 h-6 inline-block mr-2 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
              <path d="M8 16.5a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM15 16.5a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" />
              <path d="M3 4a1 1 0 00-1 1v10a1 1 0 001 1h1.05a2.5 2.5 0 014.9 0H10a1 1 0 001-1V5a1 1 0 00-1-1H3zM14 7a1 1 0 00-1 1v6.05A2.5 2.5 0 0115.95 16H17a1 1 0 001-1v-5a1 1 0 00-.293-.707l-2-2A1 1 0 0015 7h-1z" />
            </svg>
            Battery Configuration
          </h2>

          <div class="space-y-6">
            <!-- Battery Type -->
            <div>
              <label for="battery-type" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Battery Type
              </label>
              <select
                id="battery-type"
                v-model="formData.battery_type"
                class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
              >
                <option value="LFP">LFP (Lithium Iron Phosphate)</option>
                <option value="Lead-Acid">Lead-Acid (Gel/AGM)</option>
                <option value="VRFB">VRFB (Vanadium Redox Flow)</option>
              </select>
              <div class="mt-2 text-sm text-gray-600 dark:text-gray-400">
                {{ getBatteryDescription(formData.battery_type) }}
              </div>
            </div>

            <!-- Battery Capacity -->
            <div>
              <label for="battery-capacity" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Battery Capacity (kWh)
              </label>
              <div class="flex items-center space-x-4">
                <input
                  id="battery-capacity"
                  v-model.number="formData.battery_capacity_kwh"
                  type="number"
                  step="0.1"
                  min="0.1"
                  max="1000"
                  class="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                />
                <span class="text-gray-600 dark:text-gray-400">kWh</span>
              </div>
              <p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
                Recommended range: 5-100 kWh for most applications
              </p>
            </div>

            <!-- Battery Efficiency -->
            <div>
              <label for="battery-efficiency" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Round-Trip Efficiency
              </label>
              <div class="flex items-center space-x-4">
                <input
                  id="battery-efficiency"
                  v-model.number="formData.battery_efficiency"
                  type="number"
                  step="0.01"
                  min="0.7"
                  max="1.0"
                  class="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                />
                <span class="text-gray-600 dark:text-gray-400">{{ (formData.battery_efficiency * 100).toFixed(1) }}%</span>
              </div>
              <p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
                Typical: LFP=95%, Lead-Acid=85%, VRFB=75%
              </p>
            </div>
          </div>
        </div>

        <!-- Load Profile Configuration Section -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">
            <svg class="w-6 h-6 inline-block mr-2 text-green-500" fill="currentColor" viewBox="0 0 20 20">
              <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
            </svg>
            Load Profile Configuration
          </h2>

          <div class="space-y-6">
            <!-- Load Profile Type -->
            <div>
              <label for="profile-type" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Load Profile Type
              </label>
              <select
                id="profile-type"
                v-model="formData.load_profile_type"
                class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
              >
                <option value="standard">Standard Work Hours (9-18)</option>
                <option value="multi-shift">Multi-Shift (2-Shift)</option>
                <option value="24/7">24/7 Continuous</option>
                <option value="custom">Custom Hourly</option>
              </select>
              <div class="mt-2 text-sm text-gray-600 dark:text-gray-400">
                {{ getLoadDescription(formData.load_profile_type) }}
              </div>
            </div>

            <!-- Peak Load -->
            <div>
              <label for="peak-load" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Peak Load Power (kW)
              </label>
              <div class="flex items-center space-x-4">
                <input
                  id="peak-load"
                  v-model.number="formData.load_peak_kw"
                  type="number"
                  step="0.1"
                  min="0.1"
                  max="500"
                  class="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                />
                <span class="text-gray-600 dark:text-gray-400">kW</span>
              </div>
              <p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
                Maximum power demand during peak hours
              </p>
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex justify-between items-center bg-gray-50 dark:bg-gray-900 rounded-lg p-6">
          <div class="flex space-x-4">
            <button
              type="submit"
              :disabled="settingsStore.isSaving"
              class="px-6 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white font-medium rounded-lg transition duration-200 flex items-center space-x-2"
            >
              <svg v-if="!settingsStore.isSaving" class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M7.707 10.293a1 1 0 10-1.414 1.414l2 2a1 1 0 001.414 0l4-4a1 1 0 10-1.414-1.414L9 10.586 7.707 10.293z" />
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm0-2a6 6 0 100-12 6 6 0 000 12z" clip-rule="evenodd" />
              </svg>
              <svg v-else class="animate-spin w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>{{ settingsStore.isSaving ? 'Saving...' : 'Save Configuration' }}</span>
            </button>
            <button
              type="button"
              @click="handleReset"
              class="px-6 py-2 bg-gray-300 hover:bg-gray-400 dark:bg-gray-600 dark:hover:bg-gray-500 text-gray-800 dark:text-white font-medium rounded-lg transition duration-200"
            >
              Reset to Defaults
            </button>
          </div>
          <div v-if="settingsStore.lastSaveTime" class="text-sm text-gray-500 dark:text-gray-400">
            Last saved: {{ formatTime(settingsStore.lastSaveTime) }}
          </div>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useSettingsStore } from '~/stores/settingsStore'

const settingsStore = useSettingsStore()

const formData = reactive({
  battery_type: 'LFP' as 'LFP' | 'Lead-Acid' | 'VRFB',
  battery_capacity_kwh: 10.0,
  battery_efficiency: 0.95,
  load_profile_type: 'standard' as 'standard' | 'multi-shift' | '24/7' | 'custom',
  load_peak_kw: 10.0
})

const successMessage = ref('')
const errorMessage = ref('')
const validationErrors = ref<string[]>([])

const batteryDescriptions: Record<string, string> = {
  'LFP': 'Lithium Iron Phosphate - 8000+ cycles, best for daily cycling',
  'Lead-Acid': 'Lead-Acid Gel/AGM - 600 cycles, lower cost but limited cycling',
  'VRFB': 'Vanadium Redox Flow - 20000+ cycles, long duration, ideal for large systems'
}

const loadDescriptions: Record<string, string> = {
  'standard': 'Standard work hours: Office/retail operation (9 AM - 6 PM)',
  'multi-shift': 'Multi-shift operation: Manufacturing with 2+ shifts',
  '24/7': 'Continuous operation: 24/7 baseline with variable peak loads',
  'custom': 'Custom hourly: Define your own hourly load coefficients'
}

function getBatteryDescription(type: string): string {
  return batteryDescriptions[type] || ''
}

function getLoadDescription(type: string): string {
  return loadDescriptions[type] || ''
}

function formatTime(date: Date): string {
  return new Date(date).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

async function handleSave() {
  validationErrors.value = []
  errorMessage.value = ''
  successMessage.value = ''

  // Basic client-side validation
  if (formData.battery_capacity_kwh <= 0 || formData.battery_capacity_kwh > 1000) {
    validationErrors.value.push('Battery capacity must be between 0.1 and 1000 kWh')
  }

  if (formData.battery_efficiency < 0.7 || formData.battery_efficiency > 1.0) {
    validationErrors.value.push('Battery efficiency must be between 0.7 and 1.0')
  }

  if (formData.load_peak_kw <= 0 || formData.load_peak_kw > 500) {
    validationErrors.value.push('Peak load must be between 0.1 and 500 kW')
  }

  if (validationErrors.value.length > 0) {
    return
  }

  const result = await settingsStore.saveConfig({
    ...formData,
    tariff_region: 'ukraine'
  })

  if (result.success) {
    successMessage.value = 'Configuration saved successfully!'
    setTimeout(() => {
      successMessage.value = ''
    }, 5000)
  } else {
    errorMessage.value = result.error || 'Failed to save configuration'
  }
}

function handleReset() {
  if (settingsStore.settings.userConfig) {
    Object.assign(formData, settingsStore.settings.userConfig)
  }
  validationErrors.value = []
  errorMessage.value = ''
  successMessage.value = ''
}

onMounted(async () => {
  await settingsStore.loadConfig()

  if (settingsStore.settings.userConfig) {
    Object.assign(formData, settingsStore.settings.userConfig)
  }
})
</script>

<style scoped>
.configuration-page {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  min-height: 100vh;
}

@media (prefers-color-scheme: dark) {
  .configuration-page {
    background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%);
  }
}

/* Smooth transitions */
input,
select {
  transition: all 0.3s ease;
}

input:focus,
select:focus {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}
</style>

<template>
  <div class="configuration-page">
    <div class="container mx-auto px-4 py-8 max-w-4xl">
      <!-- Page Header -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Configuration
        </h1>
        <p class="text-lg text-gray-600 dark:text-gray-400">
          Configure your battery type, capacity, and load profile
        </p>
      </div>

      <!-- Main Form -->
      <form @submit.prevent="handleSave" class="space-y-8">
        <!-- Battery Configuration Section -->
        <section class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <h2 class="text-2xl font-semibold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            Battery Configuration
          </h2>

          <!-- Battery Type Selector -->
          <div class="mb-6">
            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
              Battery Type
            </label>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <button
                v-for="(template, type) in batteryTemplates"
                :key="type"
                type="button"
                @click="formData.battery_type = type"
                :class="[
                  'p-4 border-2 rounded-lg transition-all cursor-pointer',
                  formData.battery_type === type
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900'
                    : 'border-gray-300 dark:border-gray-600 hover:border-blue-300'
                ]"
              >
                <div class="text-left">
                  <div class="font-semibold text-gray-900 dark:text-white">
                    {{ template.name }}
                  </div>
                  <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    {{ template.description }}
                  </div>
                </div>
              </button>
            </div>
          </div>

          <!-- Battery Capacity Input -->
          <div class="mb-6">
            <label for="capacity" class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Battery Capacity (kWh)
            </label>
            <div class="relative">
              <input
                id="capacity"
                v-model.number="formData.battery_capacity_kwh"
                type="number"
                min="0.1"
                max="1000"
                step="0.1"
                placeholder="10"
                class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <span class="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-500">kWh</span>
            </div>
            <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
              Recommended: 5-50 kWh for small businesses
            </p>
          </div>

          <!-- Battery Efficiency Input -->
          <div class="mb-6">
            <label for="efficiency" class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Round-Trip Efficiency
            </label>
            <div class="relative">
              <input
                id="efficiency"
                v-model.number="formData.battery_efficiency"
                type="number"
                min="0.7"
                max="1.0"
                step="0.01"
                placeholder="0.95"
                class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <span class="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-500">%</span>
            </div>
            <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
              Typical range: 0.75 (VRFB) to 0.95 (LFP)
            </p>
          </div>
        </section>

        <!-- Load Profile Configuration Section -->
        <section class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <h2 class="text-2xl font-semibold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Load Profile Configuration
          </h2>

          <!-- Load Profile Type Selector -->
          <div class="mb-6">
            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
              Load Profile Type
            </label>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <button
                v-for="(template, type) in profileTemplates"
                :key="type"
                type="button"
                @click="formData.load_profile_type = type"
                :class="[
                  'p-4 border-2 rounded-lg transition-all cursor-pointer',
                  formData.load_profile_type === type
                    ? 'border-green-500 bg-green-50 dark:bg-green-900'
                    : 'border-gray-300 dark:border-gray-600 hover:border-green-300'
                ]"
              >
                <div class="text-left">
                  <div class="font-semibold text-gray-900 dark:text-white">
                    {{ template.name }}
                  </div>
                  <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    {{ template.description }}
                  </div>
                </div>
              </button>
            </div>
          </div>

          <!-- Peak Load Input -->
          <div class="mb-6">
            <label for="peak-load" class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Peak Load (kW)
            </label>
            <div class="relative">
              <input
                id="peak-load"
                v-model.number="formData.load_peak_kw"
                type="number"
                min="0.1"
                max="500"
                step="0.1"
                placeholder="10"
                class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <span class="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-500">kW</span>
            </div>
            <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
              Maximum load during operation hours
            </p>
          </div>
        </section>

        <!-- Validation Errors -->
        <div v-if="validationErrors.length > 0" class="bg-red-50 dark:bg-red-900 border-l-4 border-red-500 p-4 rounded">
          <div class="flex items-start gap-3">
            <svg class="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4v2m0 4v2M7.08 6.06A9 9 0 0110 3.5a9 9 0 018.92 2.56M7.08 17.94A9 9 0 0110 20.5a9 9 0 008.92-2.56" />
            </svg>
            <div class="text-red-800 dark:text-red-200">
              <h3 class="font-semibold mb-2">Validation Errors:</h3>
              <ul class="list-disc list-inside space-y-1">
                <li v-for="(error, index) in validationErrors" :key="index" class="text-sm">
                  {{ error }}
                </li>
              </ul>
            </div>
          </div>
        </div>

        <!-- Success Message -->
        <transition
          enter-active-class="transition duration-300"
          enter-from-class="opacity-0 translate-y-4"
          enter-to-class="opacity-100 translate-y-0"
          leave-active-class="transition duration-300"
          leave-from-class="opacity-100 translate-y-0"
          leave-to-class="opacity-0 translate-y-4"
        >
          <div v-if="showSuccessMessage" class="bg-green-50 dark:bg-green-900 border-l-4 border-green-500 p-4 rounded">
            <div class="flex items-center gap-3">
              <svg class="w-6 h-6 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
              <span class="text-green-800 dark:text-green-200 font-semibold">
                Configuration saved successfully!
              </span>
            </div>
          </div>
        </transition>

        <!-- Action Buttons -->
        <div class="flex flex-col sm:flex-row gap-4 justify-end">
          <button
            type="button"
            @click="handleReset"
            :disabled="isSaving"
            class="px-6 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Reset
          </button>
          <button
            type="submit"
            :disabled="isSaving || validationErrors.length > 0"
            class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            <svg v-if="isSaving" class="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span>{{ isSaving ? 'Saving...' : 'Save Configuration' }}</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useSettingsStore } from '~/stores/settingsStore'

const settingsStore = useSettingsStore()

// Form state
const formData = reactive({
  battery_type: 'LFP' as 'LFP' | 'Lead-Acid' | 'VRFB',
  battery_capacity_kwh: 10.0,
  battery_efficiency: 0.95,
  load_profile_type: 'standard' as 'standard' | 'multi-shift' | '24/7' | 'custom',
  load_peak_kw: 10.0,
  tariff_region: 'ukraine'
})

// UI state
const isSaving = ref(false)
const showSuccessMessage = ref(false)
const validationErrors = ref<string[]>([])

// Templates
const batteryTemplates = ref<Record<string, any>>({})
const profileTemplates = ref<Record<string, any>>({})

// Load templates on mount
const loadTemplates = async () => {
  try {
    const response = await fetch('/api/config/templates')
    if (response.ok) {
      const data = await response.json()
      if (data.success) {
        batteryTemplates.value = data.data.battery || {}
        profileTemplates.value = data.data.load_profiles || {}
      }
    }
  } catch (error) {
    console.error('Failed to load templates:', error)
  }
}

// Load user config on mount
const loadUserConfig = async () => {
  try {
    const response = await fetch('/api/config/current')
    if (response.ok) {
      const data = await response.json()
      if (data.success && data.data) {
        Object.assign(formData, data.data)
      }
    }
  } catch (error) {
    console.error('Failed to load config:', error)
  }
}

// Validate form data
const validateForm = (): boolean => {
  validationErrors.value = []

  if (!['LFP', 'Lead-Acid', 'VRFB'].includes(formData.battery_type)) {
    validationErrors.value.push('Invalid battery type selected')
  }

  if (formData.battery_capacity_kwh <= 0) {
    validationErrors.value.push('Battery capacity must be greater than 0 kWh')
  } else if (formData.battery_capacity_kwh > 1000) {
    validationErrors.value.push('Battery capacity must not exceed 1000 kWh')
  }

  if (formData.battery_efficiency < 0.7 || formData.battery_efficiency > 1.0) {
    validationErrors.value.push('Battery efficiency must be between 0.7 and 1.0')
  }

  if (!['standard', 'multi-shift', '24/7', 'custom'].includes(formData.load_profile_type)) {
    validationErrors.value.push('Invalid load profile type selected')
  }

  if (formData.load_peak_kw <= 0) {
    validationErrors.value.push('Peak load must be greater than 0 kW')
  } else if (formData.load_peak_kw > 500) {
    validationErrors.value.push('Peak load must not exceed 500 kW')
  }

  return validationErrors.value.length === 0
}

// Handle save
const handleSave = async () => {
  if (!validateForm()) {
    return
  }

  isSaving.value = true
  showSuccessMessage.value = false

  try {
    const response = await fetch('/api/config/save', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(formData)
    })

    if (response.ok) {
      const data = await response.json()
      if (data.success) {
        showSuccessMessage.value = true
        // Hide message after 3 seconds
        setTimeout(() => {
          showSuccessMessage.value = false
        }, 3000)
        
        // Also update the store
        await settingsStore.saveConfig(formData)
      } else {
        validationErrors.value = data.errors || ['Failed to save configuration']
      }
    } else {
      const error = await response.json()
      validationErrors.value = error.errors || ['Server error saving configuration']
    }
  } catch (error) {
    console.error('Error saving configuration:', error)
    validationErrors.value = ['Network error: could not save configuration']
  } finally {
    isSaving.value = false
  }
}

// Handle reset
const handleReset = () => {
  Object.assign(formData, {
    battery_type: 'LFP',
    battery_capacity_kwh: 10.0,
    battery_efficiency: 0.95,
    load_profile_type: 'standard',
    load_peak_kw: 10.0,
    tariff_region: 'ukraine'
  })
  validationErrors.value = []
  showSuccessMessage.value = false
}

// Initialize
onMounted(async () => {
  await loadTemplates()
  await loadUserConfig()
})
</script>

<style scoped>
.configuration-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

:deep(.dark) .configuration-page {
  background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
}
</style>

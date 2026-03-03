<template>
  <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-white">Scenario and Load Profile</h2>
        <p class="text-sm text-slate-400">Persisted load parameters used by optimization and retraining.</p>
      </div>
      <button class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded text-sm" @click="loadConfig" :disabled="isLoading">
        {{ isLoading ? 'Loading...' : 'Reload' }}
      </button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <label class="block">
        <span class="text-sm text-slate-300">Profile Type</span>
        <select v-model="form.load_profile_type" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2">
          <option value="standard">Standard</option>
          <option value="multi-shift">Multi-shift</option>
          <option value="24/7">24/7</option>
          <option value="custom">Custom</option>
        </select>
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Peak Load (kW)</span>
        <input v-model.number="form.load_peak_kw" type="number" min="1" max="500" step="0.1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Base Load (kW)</span>
        <input v-model.number="form.load_base_kw" type="number" min="0.1" max="100" step="0.1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Weekend Factor (0..1)</span>
        <input v-model.number="form.load_weekend_factor" type="number" min="0.1" max="1" step="0.01" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Night Factor (0..1)</span>
        <input v-model.number="form.load_night_factor" type="number" min="0.1" max="1" step="0.01" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Seasonal Variation (0..0.5)</span>
        <input v-model.number="form.load_seasonal_variation" type="number" min="0" max="0.5" step="0.01" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
      </label>
    </div>

    <div class="rounded-lg bg-slate-900 bg-opacity-60 border border-slate-700 p-4">
      <p class="text-sm text-slate-300">Estimated daily energy</p>
      <p class="text-2xl font-bold text-energy-400 mt-1">{{ estimatedDailyEnergy.toFixed(1) }} kWh/day</p>
      <p class="text-xs text-slate-400 mt-2">Computed from base and peak values as a sanity check.</p>
    </div>

    <div class="flex items-center gap-3">
      <button class="px-6 py-2 bg-energy-400 hover:bg-cyan-300 text-slate-950 font-semibold rounded" @click="save" :disabled="isSaving">
        {{ isSaving ? 'Saving...' : 'Save Scenario Settings' }}
      </button>
      <p v-if="message" class="text-sm" :class="messageClass">{{ message }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useTenantContext } from '../../composables/useTenantContext'

const tenantContext = useTenantContext()

const isLoading = ref(false)
const isSaving = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

const form = reactive({
  load_profile_type: 'standard',
  load_peak_kw: 10,
  load_base_kw: 2,
  load_weekend_factor: 0.6,
  load_night_factor: 0.3,
  load_seasonal_variation: 0.2,
})

const estimatedDailyEnergy = computed(() => {
  const daytimeHours = 12
  const nighttimeHours = 12
  const daytimeLoad = (form.load_peak_kw + form.load_base_kw) / 2
  const nighttimeLoad = form.load_base_kw * form.load_night_factor
  return (daytimeLoad * daytimeHours) + (nighttimeLoad * nighttimeHours)
})

const messageClass = computed(() => (
  messageType.value === 'success' ? 'text-green-300' : 'text-red-300'
))

const showMessage = (text: string, type: 'success' | 'error') => {
  message.value = text
  messageType.value = type
  setTimeout(() => {
    message.value = ''
  }, 4000)
}

const loadConfig = async () => {
  isLoading.value = true
  try {
    await tenantContext.loadTenants()
    const tenantId = tenantContext.currentTenantId.value
    const response = await $fetch<any>('/api/config/current', {
      query: { tenantId },
      headers: { 'x-tenant-id': tenantId },
    })
    if (response?.success && response?.data) {
      Object.assign(form, {
        load_profile_type: response.data.load_profile_type || 'standard',
        load_peak_kw: Number(response.data.load_peak_kw ?? 10),
        load_base_kw: Number(response.data.load_base_kw ?? 2),
        load_weekend_factor: Number(response.data.load_weekend_factor ?? 0.6),
        load_night_factor: Number(response.data.load_night_factor ?? 0.3),
        load_seasonal_variation: Number(response.data.load_seasonal_variation ?? 0.2),
      })
    }
  } catch (error) {
    console.error('[ScenarioManager] load failed', error)
    showMessage('Failed to load scenario settings', 'error')
  } finally {
    isLoading.value = false
  }
}

const save = async () => {
  isSaving.value = true
  try {
    await tenantContext.loadTenants()
    const tenantId = tenantContext.currentTenantId.value
    const response = await $fetch<any>('/api/config/save', {
      method: 'POST',
      query: { tenantId },
      headers: { 'x-tenant-id': tenantId },
      body: {
        tenantId,
        ...form,
      },
    })

    if (!response?.success) {
      throw new Error(response?.error || 'Save failed')
    }

    showMessage('Scenario settings saved', 'success')
  } catch (error) {
    console.error('[ScenarioManager] save failed', error)
    showMessage('Failed to save scenario settings', 'error')
  } finally {
    isSaving.value = false
  }
}

onMounted(loadConfig)
</script>

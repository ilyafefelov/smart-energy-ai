<template>
  <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-white">Generation and Weather Location</h2>
        <p class="text-sm text-slate-400">Location is sent to Dagster weather materialization for this tenant.</p>
      </div>
      <button class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded text-sm" @click="loadConfig" :disabled="isLoading">
        {{ isLoading ? 'Loading...' : 'Reload' }}
      </button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <label class="block">
        <span class="text-sm text-slate-300">Latitude</span>
        <input v-model.number="form.latitude" type="number" min="-90" max="90" step="0.0001" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Longitude</span>
        <input v-model.number="form.longitude" type="number" min="-180" max="180" step="0.0001" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Timezone</span>
        <input v-model="form.timezone" type="text" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" placeholder="Europe/Kiev" />
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Solar Capacity (kW)</span>
        <input v-model.number="form.solar_capacity_kw" type="number" min="0" max="1000" step="0.1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Wind Capacity (kW)</span>
        <input v-model.number="form.wind_capacity_kw" type="number" min="0" max="1000" step="0.1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
      </label>
    </div>

    <div class="rounded-lg bg-slate-900 bg-opacity-60 border border-slate-700 p-4">
      <p class="text-sm text-slate-300">Current setup summary</p>
      <p class="text-sm text-slate-400 mt-2">Coordinates: {{ form.latitude.toFixed(4) }}, {{ form.longitude.toFixed(4) }} | Timezone: {{ form.timezone }}</p>
      <p class="text-sm text-slate-400">Total installed renewables: {{ totalRenewableCapacity.toFixed(1) }} kW</p>
    </div>

    <div class="flex gap-3 items-center">
      <button class="px-6 py-2 bg-energy-400 hover:bg-cyan-300 text-slate-950 font-semibold rounded" @click="save" :disabled="isSaving">
        {{ isSaving ? 'Saving...' : 'Save Generation Settings' }}
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
  latitude: 50.45,
  longitude: 30.52,
  timezone: 'Europe/Kiev',
  solar_capacity_kw: 0,
  wind_capacity_kw: 0,
})

const totalRenewableCapacity = computed(() => form.solar_capacity_kw + form.wind_capacity_kw)
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
        latitude: Number(response.data.latitude ?? 50.45),
        longitude: Number(response.data.longitude ?? 30.52),
        timezone: response.data.timezone || 'Europe/Kiev',
        solar_capacity_kw: Number(response.data.solar_capacity_kw ?? 0),
        wind_capacity_kw: Number(response.data.wind_capacity_kw ?? 0),
      })
    }
  } catch (error) {
    console.error('[SolarWindConfig] load failed', error)
    showMessage('Failed to load generation settings', 'error')
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
        ...form,
        tenantId,
      },
    })

    if (!response?.success) {
      throw new Error(response?.error || 'Save failed')
    }

    showMessage('Generation settings saved', 'success')
  } catch (error) {
    console.error('[SolarWindConfig] save failed', error)
    showMessage('Failed to save generation settings', 'error')
  } finally {
    isSaving.value = false
  }
}

onMounted(loadConfig)
</script>

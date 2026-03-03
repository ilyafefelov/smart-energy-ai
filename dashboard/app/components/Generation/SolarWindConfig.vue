<template>
  <div class="rounded-xl border border-slate-700 bg-slate-800/40 p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-white">Generation and Weather Location</h2>
        <p class="text-sm text-slate-400">Restore client capabilities and tune solar/wind behavior used by forecasts.</p>
      </div>
      <button class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded text-sm" @click="loadConfig" :disabled="isLoading">
        {{ isLoading ? 'Loading...' : 'Reload' }}
      </button>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
      <button
        type="button"
        class="rounded-xl border p-4 text-left transition"
        :class="form.has_solar ? 'border-yellow-400 bg-yellow-500/10' : 'border-slate-700 bg-slate-900/50 hover:border-slate-500'"
        @click="form.has_solar = !form.has_solar"
      >
        <div class="flex items-center justify-between">
          <div>
            <p class="text-2xl">☀️</p>
            <p class="mt-2 font-semibold text-white">Solar Available</p>
            <p class="text-xs text-slate-400">PV array available on-site for daytime generation.</p>
          </div>
          <span class="rounded-full px-2 py-1 text-[10px] uppercase tracking-wide" :class="form.has_solar ? 'bg-yellow-400/20 text-yellow-200' : 'bg-slate-700 text-slate-300'">
            {{ form.has_solar ? 'Enabled' : 'Disabled' }}
          </span>
        </div>
      </button>

      <button
        type="button"
        class="rounded-xl border p-4 text-left transition"
        :class="form.has_wind ? 'border-cyan-400 bg-cyan-500/10' : 'border-slate-700 bg-slate-900/50 hover:border-slate-500'"
        @click="form.has_wind = !form.has_wind"
      >
        <div class="flex items-center justify-between">
          <div>
            <p class="text-2xl">🌬️</p>
            <p class="mt-2 font-semibold text-white">Wind Available</p>
            <p class="text-xs text-slate-400">Turbine generation available for variable wind conditions.</p>
          </div>
          <span class="rounded-full px-2 py-1 text-[10px] uppercase tracking-wide" :class="form.has_wind ? 'bg-cyan-400/20 text-cyan-200' : 'bg-slate-700 text-slate-300'">
            {{ form.has_wind ? 'Enabled' : 'Disabled' }}
          </span>
        </div>
      </button>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
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
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
      <div class="rounded-lg border border-slate-700 bg-slate-900/60 p-4 space-y-4" :class="!form.has_solar ? 'opacity-60' : ''">
        <p class="text-sm font-semibold text-yellow-300">☀️ Solar Configuration</p>

        <label class="block">
          <span class="text-sm text-slate-300">Solar Capacity (kW)</span>
          <input v-model.number="form.solar_capacity_kw" type="number" min="0" max="10000" step="0.1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" :disabled="!form.has_solar" />
        </label>

        <label class="block">
          <span class="text-sm text-slate-300">Panel Efficiency (%)</span>
          <input v-model.number="solarEfficiencyPercent" type="number" min="10" max="35" step="0.1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" :disabled="!form.has_solar" />
        </label>

        <label class="block">
          <span class="text-sm text-slate-300">Tilt Angle (deg)</span>
          <input v-model.number="form.solar_tilt_deg" type="number" min="0" max="90" step="1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" :disabled="!form.has_solar" />
        </label>
      </div>

      <div class="rounded-lg border border-slate-700 bg-slate-900/60 p-4 space-y-4" :class="!form.has_wind ? 'opacity-60' : ''">
        <p class="text-sm font-semibold text-cyan-300">🌬️ Wind Configuration</p>

        <label class="block">
          <span class="text-sm text-slate-300">Wind Capacity (kW)</span>
          <input v-model.number="form.wind_capacity_kw" type="number" min="0" max="10000" step="0.1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" :disabled="!form.has_wind" />
        </label>

        <label class="block">
          <span class="text-sm text-slate-300">Turbine Efficiency (%)</span>
          <input v-model.number="windEfficiencyPercent" type="number" min="20" max="60" step="0.1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" :disabled="!form.has_wind" />
        </label>

        <div class="grid grid-cols-2 gap-3">
          <label class="block">
            <span class="text-sm text-slate-300">Cut-in (m/s)</span>
            <input v-model.number="form.wind_cut_in_speed_mps" type="number" min="1" max="10" step="0.1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" :disabled="!form.has_wind" />
          </label>
          <label class="block">
            <span class="text-sm text-slate-300">Rated (m/s)</span>
            <input v-model.number="form.wind_rated_speed_mps" type="number" min="4" max="30" step="0.1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" :disabled="!form.has_wind" />
          </label>
        </div>
      </div>
    </div>

    <div class="rounded-lg bg-slate-900/60 border border-slate-700 p-4">
      <p class="text-sm text-slate-300">Current setup summary</p>
      <p class="text-sm text-slate-400 mt-2">Coordinates: {{ form.latitude.toFixed(4) }}, {{ form.longitude.toFixed(4) }} | Timezone: {{ form.timezone }}</p>
      <div class="mt-3 grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
        <div>
          <p class="text-slate-400">Installed renewables</p>
          <p class="font-semibold text-white">{{ totalRenewableCapacity.toFixed(1) }} kW</p>
        </div>
        <div>
          <p class="text-slate-400">Solar contribution</p>
          <p class="font-semibold text-yellow-300">{{ solarMixPercent.toFixed(0) }}%</p>
        </div>
        <div>
          <p class="text-slate-400">Wind contribution</p>
          <p class="font-semibold text-cyan-300">{{ windMixPercent.toFixed(0) }}%</p>
        </div>
      </div>
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
  has_solar: false,
  has_wind: false,
  latitude: 50.45,
  longitude: 30.52,
  timezone: 'Europe/Kiev',
  solar_capacity_kw: 0,
  wind_capacity_kw: 0,
  solar_efficiency: 0.2,
  wind_efficiency: 0.35,
  solar_tilt_deg: 30,
  wind_cut_in_speed_mps: 3,
  wind_rated_speed_mps: 12,
})

const totalRenewableCapacity = computed(() => form.solar_capacity_kw + form.wind_capacity_kw)
const solarMixPercent = computed(() => {
  if (totalRenewableCapacity.value <= 0) return 0
  return (form.solar_capacity_kw / totalRenewableCapacity.value) * 100
})
const windMixPercent = computed(() => {
  if (totalRenewableCapacity.value <= 0) return 0
  return (form.wind_capacity_kw / totalRenewableCapacity.value) * 100
})

const solarEfficiencyPercent = computed({
  get: () => Number((form.solar_efficiency * 100).toFixed(1)),
  set: (value: number) => {
    form.solar_efficiency = Math.max(0.1, Math.min(0.35, Number(value) / 100))
  },
})

const windEfficiencyPercent = computed({
  get: () => Number((form.wind_efficiency * 100).toFixed(1)),
  set: (value: number) => {
    form.wind_efficiency = Math.max(0.2, Math.min(0.6, Number(value) / 100))
  },
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
        has_solar: Boolean(response.data.has_solar ?? Number(response.data.solar_capacity_kw ?? 0) > 0),
        has_wind: Boolean(response.data.has_wind ?? Number(response.data.wind_capacity_kw ?? 0) > 0),
        latitude: Number(response.data.latitude ?? 50.45),
        longitude: Number(response.data.longitude ?? 30.52),
        timezone: response.data.timezone || 'Europe/Kiev',
        solar_capacity_kw: Number(response.data.solar_capacity_kw ?? 0),
        wind_capacity_kw: Number(response.data.wind_capacity_kw ?? 0),
        solar_efficiency: Number(response.data.solar_efficiency ?? 0.2),
        wind_efficiency: Number(response.data.wind_efficiency ?? 0.35),
        solar_tilt_deg: Number(response.data.solar_tilt_deg ?? 30),
        wind_cut_in_speed_mps: Number(response.data.wind_cut_in_speed_mps ?? 3),
        wind_rated_speed_mps: Number(response.data.wind_rated_speed_mps ?? 12),
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
        solar_capacity_kw: form.has_solar ? form.solar_capacity_kw : 0,
        wind_capacity_kw: form.has_wind ? form.wind_capacity_kw : 0,
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

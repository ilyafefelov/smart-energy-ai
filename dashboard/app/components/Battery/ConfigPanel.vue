<template>
  <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-white">Battery Configuration</h2>
        <p class="text-sm text-slate-400">These values are persisted per tenant and used by simulation/retraining.</p>
      </div>
      <button
        class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded text-sm"
        @click="loadConfig"
        :disabled="isLoading"
      >
        {{ isLoading ? 'Loading...' : 'Reload' }}
      </button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <label class="block">
        <span class="text-sm text-slate-300">Battery Type</span>
        <select v-model="form.battery_type" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2">
          <option value="LFP">LFP</option>
          <option value="Lead-Acid">Lead-Acid</option>
          <option value="VRFB">VRFB</option>
        </select>
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Capacity (kWh)</span>
        <input v-model.number="form.battery_capacity_kwh" type="number" min="1" max="1000" step="0.1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Efficiency (0..1)</span>
        <input v-model.number="form.battery_efficiency" type="number" min="0.7" max="1" step="0.01" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Charge C-Rate</span>
        <input v-model.number="form.battery_c_rate_charge" type="number" min="0.1" max="2" step="0.1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Discharge C-Rate</span>
        <input v-model.number="form.battery_c_rate_discharge" type="number" min="0.1" max="3" step="0.1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Min SOC (0..1)</span>
        <input v-model.number="form.battery_soc_min" type="number" min="0.05" max="0.5" step="0.01" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Max SOC (0..1)</span>
        <input v-model.number="form.battery_soc_max" type="number" min="0.5" max="1" step="0.01" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
      </label>
    </div>

    <div class="flex gap-3">
      <button
        class="px-6 py-2 bg-energy-400 hover:bg-cyan-300 text-slate-950 font-semibold rounded"
        @click="save"
        :disabled="isSaving"
      >
        {{ isSaving ? 'Saving...' : 'Save Battery Settings' }}
      </button>
      <p v-if="message" class="text-sm" :class="messageClass">{{ message }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useTenantContext } from '../../composables/useTenantContext'
import { useSettingsStore } from '~/stores/settingsStore'
import { useBatteryPhysicsStore } from '~/stores/batteryPhysicsStore'

const tenantContext = useTenantContext()
const settingsStore = useSettingsStore()
const batteryPhysicsStore = useBatteryPhysicsStore()

const isLoading = ref(false)
const isSaving = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

const form = reactive({
  battery_type: 'LFP',
  battery_capacity_kwh: 10,
  battery_efficiency: 0.95,
  battery_c_rate_charge: 0.5,
  battery_c_rate_discharge: 1,
  battery_soc_min: 0.1,
  battery_soc_max: 1,
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
        battery_type: response.data.battery_type,
        battery_capacity_kwh: response.data.battery_capacity_kwh,
        battery_efficiency: response.data.battery_efficiency,
        battery_c_rate_charge: response.data.battery_c_rate_charge,
        battery_c_rate_discharge: response.data.battery_c_rate_discharge,
        battery_soc_min: response.data.battery_soc_min,
        battery_soc_max: response.data.battery_soc_max,
      })
    }
  } catch (error) {
    console.error('[BatteryConfigPanel] load failed', error)
    showMessage('Failed to load battery config', 'error')
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

    await settingsStore.updateBatterySettings({
      capacity: form.battery_capacity_kwh,
      minSOC: Math.round(form.battery_soc_min * 100),
      maxChargeRate: Number((form.battery_capacity_kwh * form.battery_c_rate_charge).toFixed(2)),
      maxDischargeRate: Number((form.battery_capacity_kwh * form.battery_c_rate_discharge).toFixed(2)),
    })

    await batteryPhysicsStore.fetchBatteryData()
    showMessage('Battery settings saved', 'success')
  } catch (error) {
    console.error('[BatteryConfigPanel] save failed', error)
    showMessage('Failed to save battery settings', 'error')
  } finally {
    isSaving.value = false
  }
}

onMounted(loadConfig)
</script>

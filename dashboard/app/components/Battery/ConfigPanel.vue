<template>
  <div class="rounded-xl border border-slate-700 bg-slate-800/40 p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-white">Battery Configuration</h2>
        <p class="text-sm text-slate-400">Pick chemistry with visual presets, then tune physical limits.</p>
      </div>
      <button
        class="rounded-lg bg-slate-700 px-4 py-2 text-sm hover:bg-slate-600"
        @click="loadConfig"
        :disabled="isLoading"
      >
        {{ isLoading ? 'Loading...' : 'Reload' }}
      </button>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <button
        v-for="option in batteryOptions"
        :key="option.id"
        type="button"
        class="rounded-xl border p-4 text-left transition"
        :class="form.battery_type === option.id
          ? 'border-cyan-400 bg-cyan-500/10 shadow-[0_0_0_1px_rgba(34,211,238,0.25)]'
          : 'border-slate-700 bg-slate-900/50 hover:border-slate-500 hover:bg-slate-900'"
        @click="applyBatteryPreset(option.id)"
      >
        <div class="flex items-start justify-between">
          <div>
            <p class="text-2xl">{{ option.emoji }}</p>
            <p class="mt-2 text-base font-semibold text-white">{{ option.name }}</p>
            <p class="mt-1 text-xs text-slate-400">{{ option.tagline }}</p>
          </div>
          <span
            class="rounded-full px-2 py-1 text-[10px] uppercase tracking-wide"
            :class="form.battery_type === option.id ? 'bg-cyan-400/20 text-cyan-200' : 'bg-slate-700 text-slate-300'"
          >
            {{ option.bestFor }}
          </span>
        </div>

        <div class="mt-4 grid grid-cols-2 gap-2 text-xs">
          <div class="rounded-lg bg-slate-800/70 p-2">
            <p class="text-slate-400">Cycle life</p>
            <p class="font-semibold text-white">{{ option.cycles.toLocaleString() }}</p>
          </div>
          <div class="rounded-lg bg-slate-800/70 p-2">
            <p class="text-slate-400">Typical efficiency</p>
            <p class="font-semibold text-white">{{ option.efficiencyDefault }}%</p>
          </div>
        </div>
      </button>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
      <label class="block">
        <span class="text-sm text-slate-300">Capacity (kWh)</span>
        <input
          v-model.number="form.battery_capacity_kwh"
          type="number"
          min="1"
          max="1000"
          step="0.1"
          class="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
        />
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Round-trip efficiency (%)</span>
        <input
          v-model.number="efficiencyPercent"
          type="number"
          min="70"
          max="100"
          step="0.1"
          class="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
        />
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Charge C-rate</span>
        <input
          v-model.number="form.battery_c_rate_charge"
          type="number"
          min="0.1"
          max="2"
          step="0.1"
          class="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
        />
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Discharge C-rate</span>
        <input
          v-model.number="form.battery_c_rate_discharge"
          type="number"
          min="0.1"
          max="3"
          step="0.1"
          class="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
        />
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Min SOC reserve (%)</span>
        <input
          v-model.number="socMinPercent"
          type="number"
          min="5"
          max="50"
          step="1"
          class="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
        />
      </label>

      <label class="block">
        <span class="text-sm text-slate-300">Max SOC (%)</span>
        <input
          v-model.number="socMaxPercent"
          type="number"
          min="50"
          max="100"
          step="1"
          class="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
        />
      </label>
    </div>

    <div class="rounded-lg border border-slate-700 bg-slate-900/60 p-4">
      <p class="text-sm text-slate-300">Battery economics preview</p>
      <div class="mt-3 grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
        <div>
          <p class="text-slate-400">Usable window</p>
          <p class="font-semibold text-white">{{ usableCapacityKwh.toFixed(1) }} kWh</p>
        </div>
        <div>
          <p class="text-slate-400">Max discharge power</p>
          <p class="font-semibold text-white">{{ maxDischargeKw.toFixed(1) }} kW</p>
        </div>
        <div>
          <p class="text-slate-400">Capex estimate</p>
          <p class="font-semibold text-emerald-300">₴{{ capexEstimate.toLocaleString() }}</p>
        </div>
      </div>
    </div>

    <div class="flex items-center gap-3">
      <button
        class="rounded bg-energy-400 px-6 py-2 font-semibold text-slate-950 hover:bg-cyan-300"
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

type BatteryType = 'LFP' | 'Lead-Acid' | 'VRFB'

const tenantContext = useTenantContext()
const settingsStore = useSettingsStore()
const batteryPhysicsStore = useBatteryPhysicsStore()

const batteryOptions: Array<{
  id: BatteryType
  emoji: string
  name: string
  tagline: string
  bestFor: string
  cycles: number
  efficiencyDefault: number
  cRateCharge: number
  cRateDischarge: number
  socMin: number
  socMax: number
  capexPerKwh: number
}> = [
  {
    id: 'LFP',
    emoji: '🟢',
    name: 'LFP',
    tagline: 'Long cycle life with stable daily arbitrage behavior.',
    bestFor: 'Balanced',
    cycles: 8000,
    efficiencyDefault: 95,
    cRateCharge: 0.5,
    cRateDischarge: 1,
    socMin: 0.1,
    socMax: 1,
    capexPerKwh: 13000,
  },
  {
    id: 'Lead-Acid',
    emoji: '🟡',
    name: 'Lead-Acid',
    tagline: 'Lower upfront cost, better for conservative dispatch windows.',
    bestFor: 'Budget',
    cycles: 600,
    efficiencyDefault: 85,
    cRateCharge: 0.2,
    cRateDischarge: 0.3,
    socMin: 0.2,
    socMax: 0.8,
    capexPerKwh: 5500,
  },
  {
    id: 'VRFB',
    emoji: '🔵',
    name: 'VRFB',
    tagline: 'Ultra-high cycle endurance for heavy throughput operations.',
    bestFor: 'Heavy-duty',
    cycles: 20000,
    efficiencyDefault: 75,
    cRateCharge: 0.25,
    cRateDischarge: 0.25,
    socMin: 0.05,
    socMax: 1,
    capexPerKwh: 22000,
  },
]

const isLoading = ref(false)
const isSaving = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

const form = reactive({
  battery_type: 'LFP' as BatteryType,
  battery_capacity_kwh: 10,
  battery_efficiency: 0.95,
  battery_c_rate_charge: 0.5,
  battery_c_rate_discharge: 1,
  battery_soc_min: 0.1,
  battery_soc_max: 1,
})

const selectedBatteryMeta = computed(() => {
  const selected = batteryOptions.find((item) => item.id === form.battery_type)
  return selected ?? batteryOptions[0]!
})

const efficiencyPercent = computed({
  get: () => Number((form.battery_efficiency * 100).toFixed(1)),
  set: (value: number) => {
    form.battery_efficiency = Math.max(0.7, Math.min(1, Number(value) / 100))
  },
})

const socMinPercent = computed({
  get: () => Math.round(form.battery_soc_min * 100),
  set: (value: number) => {
    form.battery_soc_min = Math.max(0.05, Math.min(0.5, Number(value) / 100))
  },
})

const socMaxPercent = computed({
  get: () => Math.round(form.battery_soc_max * 100),
  set: (value: number) => {
    form.battery_soc_max = Math.max(0.5, Math.min(1, Number(value) / 100))
  },
})

const usableCapacityKwh = computed(() => {
  const window = Math.max(0, form.battery_soc_max - form.battery_soc_min)
  return form.battery_capacity_kwh * window
})

const maxDischargeKw = computed(() => form.battery_capacity_kwh * form.battery_c_rate_discharge)
const capexEstimate = computed(() => Math.round(form.battery_capacity_kwh * selectedBatteryMeta.value.capexPerKwh))

const messageClass = computed(() => (messageType.value === 'success' ? 'text-green-300' : 'text-red-300'))

const showMessage = (text: string, type: 'success' | 'error') => {
  message.value = text
  messageType.value = type
  setTimeout(() => {
    message.value = ''
  }, 4000)
}

const applyBatteryPreset = (batteryType: BatteryType) => {
  const preset = batteryOptions.find((item) => item.id === batteryType)
  if (!preset) return

  form.battery_type = batteryType
  form.battery_efficiency = Number((preset.efficiencyDefault / 100).toFixed(4))
  form.battery_c_rate_charge = preset.cRateCharge
  form.battery_c_rate_discharge = preset.cRateDischarge
  form.battery_soc_min = preset.socMin
  form.battery_soc_max = preset.socMax
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

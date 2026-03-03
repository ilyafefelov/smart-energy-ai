<template>
  <div class="rounded-xl border border-slate-700 bg-slate-800/40 p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-white">Scenario and Load Profile</h2>
        <p class="text-sm text-slate-400">Choose an operating profile, then tune demand behavior and seasonality.</p>
      </div>
      <button class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded text-sm" @click="loadConfig" :disabled="isLoading">
        {{ isLoading ? 'Loading...' : 'Reload' }}
      </button>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
      <button
        v-for="profile in profileOptions"
        :key="profile.id"
        type="button"
        class="rounded-xl border p-4 text-left transition"
        :class="form.load_profile_type === profile.id
          ? 'border-amber-400 bg-amber-500/10 shadow-[0_0_0_1px_rgba(251,191,36,0.25)]'
          : 'border-slate-700 bg-slate-900/50 hover:border-slate-500 hover:bg-slate-900'"
        @click="form.load_profile_type = profile.id"
      >
        <div class="flex items-start justify-between">
          <div>
            <p class="text-2xl">{{ profile.emoji }}</p>
            <p class="mt-2 text-base font-semibold text-white">{{ profile.name }}</p>
            <p class="mt-1 text-xs text-slate-400">{{ profile.description }}</p>
          </div>
          <span
            class="rounded-full px-2 py-1 text-[10px] uppercase tracking-wide"
            :class="form.load_profile_type === profile.id ? 'bg-amber-400/20 text-amber-200' : 'bg-slate-700 text-slate-300'"
          >
            {{ profile.arbitrage }}
          </span>
        </div>

        <div class="mt-4 grid grid-cols-2 gap-2 text-xs">
          <div class="rounded-lg bg-slate-800/70 p-2">
            <p class="text-slate-400">Peak window</p>
            <p class="font-semibold text-white">{{ profile.peakWindow }}</p>
          </div>
          <div class="rounded-lg bg-slate-800/70 p-2">
            <p class="text-slate-400">Typical shape</p>
            <p class="font-semibold text-white">{{ profile.shape }}</p>
          </div>
        </div>
      </button>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
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

      <label class="block md:col-span-2">
        <span class="text-sm text-slate-300">Seasonal Variation (0..0.5)</span>
        <input v-model.number="form.load_seasonal_variation" type="number" min="0" max="0.5" step="0.01" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
      </label>
    </div>

    <div class="rounded-lg border border-slate-700 bg-slate-900/60 p-4">
      <p class="text-sm text-slate-300">Load and arbitrage preview</p>
      <div class="mt-3 grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
        <div>
          <p class="text-slate-400">Estimated daily energy</p>
          <p class="font-semibold text-white">{{ estimatedDailyEnergy.toFixed(1) }} kWh/day</p>
        </div>
        <div>
          <p class="text-slate-400">Load factor</p>
          <p class="font-semibold text-white">{{ loadFactorPercent.toFixed(1) }}%</p>
        </div>
        <div>
          <p class="text-slate-400">Peak-base spread</p>
          <p class="font-semibold text-amber-300">{{ peakSpreadKw.toFixed(1) }} kW</p>
        </div>
      </div>
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

type LoadProfileType = 'standard' | 'multi-shift' | '24/7' | 'custom'

const profileOptions: Array<{
  id: LoadProfileType
  emoji: string
  name: string
  description: string
  peakWindow: string
  shape: string
  arbitrage: string
}> = [
  {
    id: 'standard',
    emoji: '🏢',
    name: 'Standard Business',
    description: 'Typical office and retail daytime demand with evening drop-off.',
    peakWindow: '09:00-18:00',
    shape: 'Single daily peak',
    arbitrage: 'High potential',
  },
  {
    id: 'multi-shift',
    emoji: '🏭',
    name: 'Multi-shift Plant',
    description: 'Two operating blocks and stronger overnight demand continuity.',
    peakWindow: '06:00-14:00 + 22:00-06:00',
    shape: 'Dual plateau',
    arbitrage: 'Medium potential',
  },
  {
    id: '24/7',
    emoji: '🌐',
    name: 'Continuous 24/7',
    description: 'Stable industrial baseline with minimal downtime windows.',
    peakWindow: 'Always active',
    shape: 'Flat baseline',
    arbitrage: 'Lower potential',
  },
  {
    id: 'custom',
    emoji: '🧩',
    name: 'Custom Profile',
    description: 'User-defined coefficients and business-specific demand behavior.',
    peakWindow: 'User-managed',
    shape: 'Flexible',
    arbitrage: 'Variable',
  },
]

const isLoading = ref(false)
const isSaving = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

const form = reactive({
  load_profile_type: 'standard' as LoadProfileType,
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

const peakSpreadKw = computed(() => Math.max(0, Number(form.load_peak_kw) - Number(form.load_base_kw)))

const loadFactorPercent = computed(() => {
  if (!form.load_peak_kw || form.load_peak_kw <= 0) return 0
  return (estimatedDailyEnergy.value / (form.load_peak_kw * 24)) * 100
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

<template>
  <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
    <h2 class="text-xl font-bold text-white mb-6">Solar and Wind Generation Config</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="bg-slate-900 rounded-lg p-4">
        <h3 class="font-semibold text-yellow-400 mb-3">Solar Panel</h3>
        <div class="space-y-3">
          <div>
            <label class="block text-xs text-slate-400 mb-1">Peak Power (kW)</label>
            <input v-model.number="solarCapacity" @change="saveSettings" type="number" min="0" class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-1 text-white text-sm focus:outline-none focus:border-energy-400" />
          </div>
          <div>
            <label class="block text-xs text-slate-400 mb-1">Efficiency (%)</label>
            <input v-model.number="solarEfficiency" @change="saveSettings" type="number" min="0" max="100" class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-1 text-white text-sm focus:outline-none focus:border-energy-400" />
          </div>
        </div>
      </div>
      <div class="bg-slate-900 rounded-lg p-4">
        <h3 class="font-semibold text-blue-400 mb-3">Wind Turbine</h3>
        <div class="space-y-3">
          <div>
            <label class="block text-xs text-slate-400 mb-1">Rated Power (kW)</label>
            <input v-model.number="windCapacity" @change="saveSettings" type="number" min="0" class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-1 text-white text-sm focus:outline-none focus:border-energy-400" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useSettingsStore } from '~/stores/settingsStore'

const settingsStore = useSettingsStore()

const solarCapacity = ref(50)
const solarEfficiency = ref(18)
const windCapacity = ref(10)

onMounted(() => {
  solarCapacity.value = settingsStore.settings.generation?.solarCapacity || 50
  windCapacity.value = settingsStore.settings.generation?.windCapacity || 10
})

const saveSettings = () => {
  settingsStore.updateGenerationSettings({
    solarCapacity: solarCapacity.value,
    windCapacity: windCapacity.value
  })
}
</script>

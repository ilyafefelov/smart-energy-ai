<template>
  <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
    <h2 class="text-xl font-bold text-white mb-6">🔋 Battery Configuration</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div>
        <label class="block text-sm font-semibold text-slate-300 mb-2">Battery Type</label>
        <select v-model="batteryType" @change="saveSettings" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-energy-400">
          <option value="LFP">LFP (Lithium Iron Phosphate)</option>
          <option value="Lead-Acid">Lead-Acid</option>
          <option value="VRFB">VRFB (Vanadium Redox Flow)</option>
        </select>
      </div>
      <div>
        <label class="block text-sm font-semibold text-slate-300 mb-2">Capacity (kWh)</label>
        <input v-model.number="capacity" @change="saveSettings" type="number" min="1" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-energy-400" />
      </div>
      <div>
        <label class="block text-sm font-semibold text-slate-300 mb-2">Charge C-Rate</label>
        <input v-model.number="maxChargeRate" @change="saveSettings" type="number" min="0.1" max="3" step="0.1" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-energy-400" />
      </div>
      <div>
        <label class="block text-sm font-semibold text-slate-300 mb-2">Discharge C-Rate</label>
        <input v-model.number="maxDischargeRate" @change="saveSettings" type="number" min="0.1" max="3" step="0.1" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-energy-400" />
      </div>
      <div>
        <label class="block text-sm font-semibold text-slate-300 mb-2">Min SOC (%)</label>
        <input v-model.number="minSOC" @change="saveSettings" type="number" min="0" max="50" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-energy-400" />
      </div>
      <div>
        <label class="block text-sm font-semibold text-slate-300 mb-2">Max SOC (%)</label>
        <input v-model.number="maxSOC" @change="saveSettings" type="number" min="50" max="100" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-energy-400" />
      </div>
    </div>
    <div class="mt-6 p-3 bg-slate-900 rounded-lg">
      <p class="text-xs text-slate-400">💡 Changes are saved automatically and used for savings calculations.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useSettingsStore } from '~/stores/settingsStore'
import { useBatteryPhysicsStore } from '~/stores/batteryPhysicsStore'

const settingsStore = useSettingsStore()
const batteryPhysicsStore = useBatteryPhysicsStore()

// Local state synced with settings
const capacity = ref(150)
const batteryType = ref('LFP')
const maxChargeRate = ref(50)
const maxDischargeRate = ref(50)
const minSOC = ref(15)
const maxSOC = ref(95)

// Load from settings on mount
onMounted(() => {
  capacity.value = settingsStore.batterySettings.capacity
  maxChargeRate.value = settingsStore.batterySettings.maxChargeRate
  maxDischargeRate.value = settingsStore.batterySettings.maxDischargeRate
  minSOC.value = settingsStore.batterySettings.minSOC
  maxSOC.value = settingsStore.batterySettings.maxSOC
  
  // Also sync with physics store
  batteryPhysicsStore.updateConfig({
    capacity: capacity.value,
    cRateCharge: maxChargeRate.value / capacity.value,
    cRateDischarge: maxDischargeRate.value / capacity.value,
    socMin: minSOC.value / 100,
    socMax: maxSOC.value / 100
  })
})

const saveSettings = () => {
  // Save to settings (persisted to localStorage)
  settingsStore.updateBatterySettings({
    capacity: capacity.value,
    maxChargeRate: maxChargeRate.value,
    maxDischargeRate: maxDischargeRate.value,
    minSOC: minSOC.value,
    maxSOC: maxSOC.value
  })
  
  // Also sync with physics store for simulation
  batteryPhysicsStore.updateConfig({
    capacity: capacity.value,
    cRateCharge: maxChargeRate.value / capacity.value,
    cRateDischarge: maxDischargeRate.value / capacity.value,
    socMin: minSOC.value / 100,
    socMax: maxSOC.value / 100
  })
}
</script>

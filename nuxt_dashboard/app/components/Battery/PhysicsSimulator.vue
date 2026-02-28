<template>
  <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
    <h2 class="text-xl font-bold text-white mb-6">⚡ Battery Physics Simulator</h2>

    <!-- Status Grid -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <div class="bg-slate-900 rounded-lg p-3 text-center">
        <div class="text-2xl font-bold mb-1" :class="batteryPhysicsStore.socColor">{{ batteryPhysicsStore.state.socPercentage.toFixed(1) }}%</div>
        <div class="text-xs text-slate-400">SOC</div>
      </div>
      <div class="bg-slate-900 rounded-lg p-3 text-center">
        <div class="text-2xl font-bold mb-1 text-cyan-400">{{ batteryPhysicsStore.state.power.toFixed(1) }} kW</div>
        <div class="text-xs text-slate-400">Power</div>
      </div>
      <div class="bg-slate-900 rounded-lg p-3 text-center">
        <div class="text-2xl font-bold mb-1" :class="batteryPhysicsStore.healthStatus.color">{{ (batteryPhysicsStore.state.health * 100).toFixed(1) }}%</div>
        <div class="text-xs text-slate-400">Health</div>
      </div>
      <div class="bg-slate-900 rounded-lg p-3 text-center">
        <div class="text-2xl font-bold mb-1 text-orange-400">{{ batteryPhysicsStore.state.temperature.toFixed(1) }}°C</div>
        <div class="text-xs text-slate-400">Temperature</div>
      </div>
    </div>

    <!-- Power Control -->
    <div class="mb-6">
      <label class="block text-sm font-semibold text-slate-300 mb-2">Power Command (kW) — positive = charge, negative = discharge</label>
      <div class="flex gap-3 items-center">
        <input v-model.number="powerCommand" type="range" :min="-batteryPhysicsStore.state.maxDischargePower" :max="batteryPhysicsStore.state.maxChargePower" step="1" class="flex-1" />
        <span class="text-white font-bold w-20 text-right">{{ powerCommand.toFixed(1) }} kW</span>
      </div>
    </div>

    <!-- Control Buttons -->
    <div class="flex flex-wrap gap-3">
      <button @click="runSimulation" class="px-4 py-2 bg-energy-400 hover:bg-cyan-300 text-slate-950 font-semibold rounded-lg transition">▶ Simulate Step</button>
      <button @click="batteryPhysicsStore.charge(batteryPhysicsStore.state.maxChargePower * 0.8)" :disabled="!batteryPhysicsStore.canCharge" class="px-4 py-2 bg-green-600 hover:bg-green-500 text-white font-semibold rounded-lg transition disabled:opacity-50">⚡ Full Charge</button>
      <button @click="batteryPhysicsStore.discharge(batteryPhysicsStore.state.maxDischargePower * 0.8)" :disabled="!batteryPhysicsStore.canDischarge" class="px-4 py-2 bg-orange-600 hover:bg-orange-500 text-white font-semibold rounded-lg transition disabled:opacity-50">🔋 Full Discharge</button>
      <button @click="batteryPhysicsStore.idle()" class="px-4 py-2 bg-slate-600 hover:bg-slate-500 text-white font-semibold rounded-lg transition">⏸ Idle</button>
      <button @click="batteryPhysicsStore.reset()" class="px-4 py-2 bg-red-700 hover:bg-red-600 text-white font-semibold rounded-lg transition">↺ Reset</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useBatteryPhysicsStore } from '~/stores/batteryPhysicsStore'

const batteryPhysicsStore = useBatteryPhysicsStore()
const powerCommand = ref(0)

const runSimulation = () => {
  if (powerCommand.value >= 0) {
    batteryPhysicsStore.charge(powerCommand.value)
  } else {
    batteryPhysicsStore.discharge(Math.abs(powerCommand.value))
  }
}
</script>

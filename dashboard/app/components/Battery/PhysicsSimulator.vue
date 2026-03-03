<template>
  <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-white">Battery Control</h2>
        <p class="text-sm text-slate-400">Manual and automatic execution mode control. Strategy selection is managed in the Optimization tab.</p>
      </div>
      <div class="text-sm" :class="batteryPhysicsStore.powerStatus.color">
        {{ batteryPhysicsStore.powerStatus.icon }} {{ batteryPhysicsStore.powerStatus.text }}
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-slate-900 bg-opacity-50 rounded p-4">
        <p class="text-xs text-slate-400">SOC</p>
        <p class="text-2xl font-bold" :class="batteryPhysicsStore.socColor">{{ batteryPhysicsStore.state.socPercentage.toFixed(1) }}%</p>
      </div>
      <div class="bg-slate-900 bg-opacity-50 rounded p-4">
        <p class="text-xs text-slate-400">Power</p>
        <p class="text-2xl font-bold" :class="powerColor">{{ batteryPhysicsStore.state.power.toFixed(2) }} kW</p>
      </div>
      <div class="bg-slate-900 bg-opacity-50 rounded p-4">
        <p class="text-xs text-slate-400">Temperature</p>
        <p class="text-2xl font-bold">{{ batteryPhysicsStore.state.temperature.toFixed(1) }}C</p>
      </div>
      <div class="bg-slate-900 bg-opacity-50 rounded p-4">
        <p class="text-xs text-slate-400">Health</p>
        <p class="text-2xl font-bold" :class="batteryPhysicsStore.healthStatus.color">{{ batteryPhysicsStore.state.health }}%</p>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <button class="px-4 py-2 rounded font-semibold" :class="batteryPhysicsStore.state.manualMode ? 'bg-red-600 hover:bg-red-500 text-white' : 'bg-slate-700 text-slate-300'" @click="setManualMode(true)">
        Manual Mode
      </button>
      <button class="px-4 py-2 rounded font-semibold" :class="batteryPhysicsStore.state.autoOptimization ? 'bg-green-600 hover:bg-green-500 text-white' : 'bg-slate-700 text-slate-300'" @click="setManualMode(false)">
        Auto Mode
      </button>
    </div>

    <div>
      <div class="flex justify-between text-sm text-slate-300 mb-2">
        <span>Power Command</span>
        <span>{{ powerCommand.toFixed(1) }} kW</span>
      </div>
      <input
        v-model.number="powerCommand"
        type="range"
        :min="-batteryPhysicsStore.state.maxDischargePower"
        :max="batteryPhysicsStore.state.maxChargePower"
        step="0.1"
        :disabled="!batteryPhysicsStore.state.manualMode"
        class="w-full"
      />
    </div>

    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <button class="px-4 py-2 bg-green-600 hover:bg-green-500 rounded" :disabled="!batteryPhysicsStore.state.manualMode" @click="applyPower">Apply</button>
      <button class="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded" @click="quickCharge" :disabled="!batteryPhysicsStore.canCharge">Quick Charge</button>
      <button class="px-4 py-2 bg-orange-600 hover:bg-orange-500 rounded" @click="quickDischarge" :disabled="!batteryPhysicsStore.canDischarge">Quick Discharge</button>
      <button class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded" @click="stopPower">Stop</button>
    </div>

    <p v-if="message" class="text-sm" :class="messageClass">{{ message }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useBatteryPhysicsStore } from '~/stores/batteryPhysicsStore'

const batteryPhysicsStore = useBatteryPhysicsStore()

const powerCommand = ref(0)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

const messageClass = computed(() => (messageType.value === 'success' ? 'text-green-300' : 'text-red-300'))
const powerColor = computed(() => {
  if (batteryPhysicsStore.state.power > 0) return 'text-green-400'
  if (batteryPhysicsStore.state.power < 0) return 'text-orange-400'
  return 'text-slate-300'
})

const showMessage = (text: string, type: 'success' | 'error') => {
  message.value = text
  messageType.value = type
  setTimeout(() => {
    message.value = ''
  }, 3500)
}

const setManualMode = async (manual: boolean) => {
  await batteryPhysicsStore.setAutoMode(!manual)
  showMessage(manual ? 'Manual mode enabled' : 'Auto mode enabled', 'success')
}

const applyPower = async () => {
  try {
    await batteryPhysicsStore.setPowerCommand(powerCommand.value)
    showMessage('Power command applied', 'success')
  } catch {
    showMessage('Failed to apply power command', 'error')
  }
}

const quickCharge = async () => {
  try {
    await batteryPhysicsStore.charge(batteryPhysicsStore.state.maxChargePower * 0.8)
    showMessage('Quick charge started', 'success')
  } catch {
    showMessage('Quick charge failed', 'error')
  }
}

const quickDischarge = async () => {
  try {
    await batteryPhysicsStore.discharge(batteryPhysicsStore.state.maxDischargePower * 0.8)
    showMessage('Quick discharge started', 'success')
  } catch {
    showMessage('Quick discharge failed', 'error')
  }
}

const stopPower = async () => {
  try {
    await batteryPhysicsStore.idle()
    powerCommand.value = 0
    showMessage('Power command reset to idle', 'success')
  } catch {
    showMessage('Failed to stop power command', 'error')
  }
}

onMounted(async () => {
  await batteryPhysicsStore.fetchBatteryData()
  powerCommand.value = batteryPhysicsStore.state.powerCommand
})
</script>

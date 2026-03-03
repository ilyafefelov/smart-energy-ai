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

    <BatteryInteractiveIllustration
      title="Control Room Illustration"
      subtitle="Unified battery control widget reused in settings and dashboard"
    />

    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div class="rounded-lg bg-slate-900/70 px-3 py-2 text-center">
        <p class="text-xs text-slate-400">Voltage</p>
        <p class="text-sm font-semibold text-slate-100">{{ batteryPhysicsStore.state.voltage.toFixed(1) }} V</p>
      </div>
      <div class="rounded-lg bg-slate-900/70 px-3 py-2 text-center">
        <p class="text-xs text-slate-400">Current</p>
        <p class="text-sm font-semibold text-slate-100">{{ batteryPhysicsStore.state.current.toFixed(1) }} A</p>
      </div>
      <div class="rounded-lg bg-slate-900/70 px-3 py-2 text-center">
        <p class="text-xs text-slate-400">Cycle Count</p>
        <p class="text-sm font-semibold text-slate-100">{{ batteryPhysicsStore.state.cycleCount }}</p>
      </div>
      <div class="rounded-lg bg-slate-900/70 px-3 py-2 text-center">
        <p class="text-xs text-slate-400">Limits</p>
        <p class="text-sm font-semibold text-slate-100">{{ batteryPhysicsStore.state.socMin }}-{{ batteryPhysicsStore.state.socMax }}%</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useBatteryPhysicsStore } from '~/stores/batteryPhysicsStore'
import BatteryInteractiveIllustration from '~/components/Battery/InteractiveIllustration.vue'

const batteryPhysicsStore = useBatteryPhysicsStore()

onMounted(async () => {
  await batteryPhysicsStore.fetchBatteryData()
})
</script>

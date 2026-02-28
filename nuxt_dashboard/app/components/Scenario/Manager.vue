<template>
  <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
    <h2 class="text-xl font-bold text-white mb-6">Scenario Manager</h2>
    <p class="text-slate-400 mb-4">Save and load battery configuration scenarios.</p>
    <div class="space-y-3">
      <div v-for="(scenario, idx) in scenarios" :key="idx" class="flex items-center justify-between bg-slate-900 rounded-lg p-3">
        <div>
          <p class="font-semibold text-white">{{ scenario.name }}</p>
          <p class="text-xs text-slate-400">{{ scenario.description }}</p>
        </div>
        <button @click="loadScenario(scenario)" class="px-3 py-1 text-xs bg-cyan-400 text-slate-950 font-semibold rounded">Load</button>
      </div>
    </div>
    <div class="mt-4 flex gap-3">
      <input v-model="newScenarioName" type="text" placeholder="Scenario name..." class="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm" />
      <button @click="saveScenario" class="px-4 py-2 bg-green-600 text-white font-semibold rounded-lg text-sm">Save</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue"
interface Scenario { name: string; description: string }
const scenarios = ref<Scenario[]>([
  { name: "Conservative", description: "Low C-rate, protect battery health" },
  { name: "Aggressive", description: "High C-rate, maximize arbitrage" },
  { name: "Balanced", description: "Balance between savings and longevity" }
])
const newScenarioName = ref("")
const loadScenario = (scenario: Scenario) => { console.log("Loading:", scenario.name) }
const saveScenario = () => {
  if (!newScenarioName.value.trim()) return
  scenarios.value.push({ name: newScenarioName.value, description: "Custom scenario" })
  newScenarioName.value = ""
}
</script>